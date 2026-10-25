"""Business DB isolation and one measured execute/fetch boundary."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy import CursorResult, Executable, RowMapping, event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.sql import ClauseElement

from concurrency_lab.core.exceptions import BusinessFailure, FailureCode
from concurrency_lab.observability.recording import RequestObservation
from concurrency_lab.schemas.business import MeasuredSpan

BUSINESS_DATABASES = frozenset({"concurrency_lab_business", "concurrency_lab_business_test"})
BUSINESS_PURPOSE = "business-lab-v1"


def validate_business_database(database: str) -> str:
    if database not in BUSINESS_DATABASES:
        raise ValueError("Refusing non-allowlisted business database")
    return database


@dataclass(frozen=True)
class BusinessResources:
    engine: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]


def configure_business_lock_timeout(engine: AsyncEngine, seconds: int) -> None:
    """Uniform business-pool session configuration, part of lazy connection acquisition."""
    if not 1 <= seconds <= 10:
        raise ValueError("Business lock timeout outside bounded seconds")

    @event.listens_for(engine.sync_engine, "connect")
    def configure(connection: Any, record: Any) -> None:
        cursor = connection.cursor()
        try:
            cursor.execute(f"SET SESSION innodb_lock_wait_timeout={seconds}")
        finally:
            cursor.close()


@dataclass(frozen=True)
class ChangeResult:
    affected_rows: int
    inserted_id: int | None


def pool_gauges(engine: AsyncEngine) -> dict[str, int]:
    pool = cast(QueuePool, engine.sync_engine.pool)
    return {
        "configured_size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": max(0, pool.overflow()),
    }


class ObservedDatabase:
    def __init__(self, session: AsyncSession, observation: RequestObservation) -> None:
        self.session = session
        self.observation = observation

    @contextmanager
    def _statement_span(
        self, statement: Executable, source: str, kind: str
    ) -> Iterator[MeasuredSpan]:
        compiled = cast(ClauseElement, statement).compile(dialect=self.session.get_bind().dialect)
        with self.observation.span("Execute fixed SQL", kind, source) as span:
            span.sql = str(compiled)
            span.parameters = {
                key: value if isinstance(value, (int, float, bool)) or value is None else str(value)
                for key, value in (compiled.params or {}).items()
            }
            yield span

    async def fetch_rows(self, statement: Executable, source: str) -> list[RowMapping]:
        with self._statement_span(statement, source, "sql_execute_fetch") as span:
            result = await self.session.execute(statement)
            rows = list(result.mappings().all())
            span.result_count = len(rows)
        return rows

    async def execute_change(self, statement: Executable, source: str) -> ChangeResult:
        with self._statement_span(statement, source, "sql_execute_change") as span:
            result = cast(CursorResult[Any], await self.session.execute(statement))
            span.result_count = result.rowcount
            return ChangeResult(
                result.rowcount, int(result.lastrowid) if result.lastrowid else None
            )

    async def verify_ownership(self, database: str) -> None:
        rows = await self.fetch_rows(
            text(
                "SELECT DATABASE() AS database_name, purpose, "
                "(SELECT status FROM experiment_dataset WHERE id=1) AS dataset_status "
                "FROM experiment_ownership WHERE id=1"
            ),
            "src/concurrency_lab/db/business.py",
        )
        if (
            len(rows) != 1
            or rows[0]["database_name"] != database
            or rows[0]["purpose"] != BUSINESS_PURPOSE
            or rows[0]["dataset_status"] != "ready"
        ):
            raise BusinessFailure(FailureCode.OWNERSHIP)
