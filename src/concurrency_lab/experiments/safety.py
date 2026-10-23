"""Safety boundary shared by every experimental write/DDL command."""

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

DATABASES = frozenset(
    f"concurrency_lab_exp_002_{size}" for size in ("10000", "100000", "1000000", "test")
)
PURPOSE = "index-baseline-v1"


class ExperimentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EXP_MYSQL_",
        env_file=".env",
        extra="ignore",
        hide_input_in_errors=True,
        populate_by_name=True,
    )
    host: str = "127.0.0.1"
    port: int = Field(default=13306, ge=1, le=65535)
    user: str = "lab_exp"
    password: SecretStr = Field(
        validation_alias=AliasChoices("EXP_MYSQL_PASSWORD", "MYSQL_PASSWORD", "password"),
        min_length=1,
    )

    def url(self, database: str) -> URL:
        return URL.create(
            "mysql+asyncmy",
            username=self.user,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            database=validate_database(database),
            query={"charset": "utf8mb4"},
        )


def validate_database(database: str) -> str:
    if database not in DATABASES:
        raise ValueError("Refusing non-allowlisted experiment database")
    return database


def engine_for(database: str) -> AsyncEngine:
    return create_async_engine(
        ExperimentSettings().url(database),
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )


async def assert_owned(connection: AsyncConnection, database: str) -> None:
    validate_database(database)
    actual = await connection.scalar(text("SELECT DATABASE()"))
    if actual != database:
        raise ValueError("Connected database does not match explicit experiment target")
    purpose = await connection.scalar(text("SELECT purpose FROM experiment_ownership WHERE id=1"))
    if purpose != PURPOSE:
        raise ValueError("Missing or incorrect experiment ownership marker")


async def revision(connection: AsyncConnection) -> str:
    return str(await connection.scalar(text("SELECT version_num FROM alembic_version")))


async def can_initialize(database: str) -> None:
    engine = engine_for(database)
    try:
        async with engine.connect() as connection:
            if await connection.scalar(text("SELECT DATABASE()")) != database:
                raise ValueError("Connected database does not match explicit experiment target")
            tables = await connection.scalar(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE()")
            )
            if tables:
                await assert_owned(connection, database)
                if await revision(connection) != "0002":
                    raise ValueError("Init only accepts empty database or owned baseline revision")
    finally:
        await engine.dispose()
