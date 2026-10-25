"""Separate009allowlist and owned connections;002and business validators stay unchanged."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from concurrency_lab.experiments.safety import ExperimentSettings

SCALES = (10000, 100000, 1000000, 10000000)
TEST_DATABASES = frozenset(
    f"concurrency_lab_exp_009_{name}" for name in ("test", "test_partial", "test_gate")
)
DATABASES = TEST_DATABASES | frozenset(f"concurrency_lab_exp_009_{n}" for n in SCALES)
PURPOSE = "scale-lab-v1"
REVISIONS = ("scale001", "scale002", "scale003")


def validate_batch_budget(count: int, batch_size: int) -> None:
    if count < 1 or not 1 <= batch_size <= 10000 or (count + batch_size - 1) // batch_size > 10000:
        raise ValueError(
            "Use batch1..10000 and at most10000retained batches; choose a larger batch"
        )


def validate_target(
    database: str, count: int | None = None, allow_ten_million: bool = False
) -> str:
    if database not in DATABASES:
        raise ValueError("Refusing non-009 experiment database")
    if count is not None:
        if database in TEST_DATABASES:
            if not 1 <= count <= 10000:
                raise ValueError("Test dataset must be1..10000rows")
        elif count not in SCALES or database != f"concurrency_lab_exp_009_{count}":
            raise ValueError("Scale must match the literal database suffix")
        if count == 10000000 and not allow_ten_million:
            raise ValueError("Ten-million extension requires explicit opt-in")
    return database


def database_url(database: str) -> URL:
    settings = ExperimentSettings()
    return URL.create(
        "mysql+asyncmy",
        username=settings.user,
        password=settings.password.get_secret_value(),
        host=settings.host,
        port=settings.port,
        database=validate_target(database),
        query={"charset": "utf8mb4"},
    )


def engine_for(database: str) -> AsyncEngine:
    return create_async_engine(
        database_url(database),
        pool_size=2,
        max_overflow=0,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )


async def assert_owned(connection: AsyncConnection, database: str) -> str:
    validate_target(database)
    if await connection.scalar(text("SELECT DATABASE()")) != database:
        raise ValueError("Connected experiment target mismatch")
    if await connection.scalar(text("SELECT purpose FROM scale_ownership WHERE id=1")) != PURPOSE:
        raise ValueError("Wrong or absent009ownership")
    revision = await connection.scalar(text("SELECT version_num FROM scale_alembic_version"))
    if revision not in REVISIONS:
        raise ValueError("Unexpected009migration revision retained")
    return cast(str, revision)


async def can_initialize(database: str) -> bool:
    engine = engine_for(database)
    try:
        async with engine.connect() as connection:
            if await connection.scalar(text("SELECT DATABASE()")) != database:
                raise ValueError("Connected experiment target mismatch")
            count = await connection.scalar(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE()")
            )
            if count:
                await assert_owned(connection, database)
                return False
            return True
    finally:
        await engine.dispose()


@asynccontextmanager
async def experiment_lock(database: str) -> AsyncIterator[None]:
    engine = engine_for(database)
    name = "hcl:009:" + validate_target(database)
    try:
        async with engine.connect() as connection:
            if await connection.scalar(text("SELECT GET_LOCK(:name,0)"), {"name": name}) != 1:
                raise ValueError(
                    "Another009experiment owns this database; no concurrent transition"
                )
            try:
                yield
            finally:
                await connection.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": name})
    finally:
        await engine.dispose()
