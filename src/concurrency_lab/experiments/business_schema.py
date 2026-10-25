"""Explicit owned-business schema upgrade. Never resets data or targets index experiment DBs."""

import argparse
import asyncio

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from concurrency_lab.core.config import Settings
from concurrency_lab.db.business import (
    BUSINESS_DATABASES,
    BUSINESS_PURPOSE,
    validate_business_database,
)
from concurrency_lab.experiments.business_dataset import business_engine


async def check_upgrade_target(database: str) -> str:
    engine = business_engine(validate_business_database(database))
    try:
        async with engine.connect() as connection:
            if await connection.scalar(text("SELECT DATABASE()")) != database:
                raise ValueError("Connected database mismatch")
            if (
                await connection.scalar(text("SELECT purpose FROM experiment_ownership WHERE id=1"))
                != BUSINESS_PURPOSE
            ):
                raise ValueError("Owned business purpose required before migration")
            if (
                await connection.scalar(text("SELECT status FROM experiment_dataset WHERE id=1"))
                != "ready"
            ):
                raise ValueError("Ready business dataset required before migration")
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            if revision not in (
                "0003",
                "0004",
                "0005",
            ):
                raise ValueError("Unexpected business schema revision retained")
            return str(revision)
    finally:
        await engine.dispose()


def upgrade_business_schema(database: str, revision: str = "0004") -> None:
    if revision not in ("0004", "0005"):
        raise ValueError("Unsupported business revision")
    current = asyncio.run(check_upgrade_target(database))
    if current >= revision:
        return
    configuration = Config("alembic.ini")
    configuration.attributes["database_url"] = (
        Settings()
        .model_copy(update={"mysql_database": validate_business_database(database)})
        .database_url
    )
    command.upgrade(configuration, revision)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", choices=sorted(BUSINESS_DATABASES), required=True)
    parser.add_argument("--revision", choices=["0004", "0005"], default="0004")
    arguments = parser.parse_args()
    try:
        upgrade_business_schema(arguments.database, arguments.revision)
    except ValueError as failure:
        parser.exit(2, str(failure) + "\n")
    except SQLAlchemyError:
        parser.exit(
            1, "Migration failed; preserve the scene and inspect locally. No automatic reset.\n"
        )


if __name__ == "__main__":
    main()
