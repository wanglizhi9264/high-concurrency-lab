"""Explicit per-request monotonic spans; no request data in global mutable state."""

import asyncio
import platform
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from importlib.metadata import version
from uuid import uuid4

from concurrency_lab.schemas.business import BusinessTrace, MeasuredSpan


class RequestObservation:
    def __init__(self, database: str) -> None:
        self.request_id = uuid4().hex
        self.database = database
        self.observed_at = datetime.now(UTC).isoformat()
        self.started = time.perf_counter()
        self.spans: list[MeasuredSpan] = []
        self._parents: list[str] = []
        self.pool_before: dict[str, int] = {}
        self.pool_after: dict[str, int] = {}
        self.pool_before_offset_ms: float | None = None
        self.pool_after_offset_ms: float | None = None

    def elapsed(self) -> float:
        return (time.perf_counter() - self.started) * 1000

    @contextmanager
    def span(self, name: str, kind: str, source: str) -> Iterator[MeasuredSpan]:
        start = self.elapsed()
        span = MeasuredSpan(
            id=f"span-{len(self.spans)}",
            parent_id=self._parents[-1] if self._parents else None,
            name=name,
            kind=kind,
            source=source,
            start_ms=start,
        )
        self.spans.append(span)
        self._parents.append(span.id)
        try:
            yield span
        except asyncio.CancelledError:
            span.state = "cancelled"
            raise
        except TimeoutError:
            span.state = "timeout"
            raise
        except Exception:
            span.state = "error"
            raise
        finally:
            span.duration_ms = self.elapsed() - start
            self._parents.pop()

    def snapshot(self) -> BusinessTrace:
        return BusinessTrace(
            request_id=self.request_id,
            observed_at=self.observed_at,
            environment={
                "python": platform.python_version(),
                "sqlalchemy": version("sqlalchemy"),
                "scope": "single application process; configured business database",
            },
            service_elapsed_ms=self.elapsed(),
            database=self.database,
            spans=self.spans,
            pool_before=self.pool_before,
            pool_after=self.pool_after,
            pool_before_offset_ms=self.pool_before_offset_ms,
            pool_after_offset_ms=self.pool_after_offset_ms,
            definitions={
                "service_elapsed_ms": "Request start to snapshot before serialization; ms.",
                "acquire": "Queue/connect/pre-ping/session setup; not pure queue time; ms.",
                "sql_execute_fetch": "Client execute/fetch includes driver/network/server; ms.",
                "pool": "Instantaneous per-process gauges; no queue-length measurement.",
                "nested": "Parent spans include children; do not sum overlapping intervals.",
                "http_header": "Through response-start preparation; excludes delivery/network; ms.",
                "clock": "Server monotonic clock; browser RTT uses a separate clock.",
                "redis_command": "Client Redis command/script round trip, including network; ms.",
                "cache_coordination": "Bounded polling and command time, not pure queueing; ms.",
                "cache_fence": "Observed atomic generation/token publication decision.",
                "sql_execute_change": "Client fixed DML interval; result_count is affected rows.",
                "transaction": (
                    "Explicit transaction including exit/commit/rollback cost. "
                    "Error/timeout alone does not establish commit outcome."
                ),
            },
        )
