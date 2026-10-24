"""Explicit owned business initialization; no destructive reset or automatic resume."""

import argparse
import asyncio
import hashlib

from alembic import command
from alembic.config import Config
from sqlalchemy import insert, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from concurrency_lab.core.config import Settings
from concurrency_lab.db.business import (
    BUSINESS_DATABASES,
    BUSINESS_PURPOSE,
    validate_business_database,
)
from concurrency_lab.db.session import create_engine
from concurrency_lab.experiments.dataset import digest_batch, order_batches, reference_rows
from concurrency_lab.models.commerce import (
    ExperimentDataset,
    ExperimentOwnership,
    LabOrder,
    LabOrderItem,
    LabProduct,
    LabUser,
)

SEED = 20261023
TABLES = ("lab_user", "lab_product", "lab_order", "lab_order_item", "experiment_dataset")


def business_engine(database: str) -> AsyncEngine:
    validate_business_database(database)
    return create_engine(Settings().model_copy(update={"mysql_database": database}))


async def check_initialization_target(database: str) -> bool:
    engine = business_engine(database)
    try:
        async with engine.connect() as connection:
            if await connection.scalar(text("SELECT DATABASE()")) != database:
                raise ValueError("Connected business database mismatch")
            count = await connection.scalar(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE()")
            )
            if not count:
                return True
            purpose = await connection.scalar(
                text("SELECT purpose FROM experiment_ownership WHERE id=1")
            )
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            if purpose == BUSINESS_PURPOSE:
                if (
                    await connection.scalar(
                        text("SELECT status FROM experiment_dataset WHERE id=1")
                    )
                    != "ready"
                ):
                    raise ValueError("Incomplete owned dataset retained; no reset/resume")
                return False
            if purpose != "index-baseline-v1" or revision != "0003":
                raise ValueError("Refusing non-owned/nonempty initialization target")
            if any(
                [await connection.scalar(text(f"SELECT COUNT(*) FROM {table}")) for table in TABLES]
            ):
                raise ValueError("Refusing to claim a nonempty database")
            return False
    finally:
        await engine.dispose()


def initialize_business_database(database: str) -> None:
    if not asyncio.run(check_initialization_target(database)):
        print("Existing initialized target retained.")
        return
    config = Config("alembic.ini")
    config.attributes["database_url"] = (
        Settings()
        .model_copy(update={"mysql_database": validate_business_database(database)})
        .database_url
    )
    # Freeze004 schema version: later features have their own explicit migration step.
    command.upgrade(config, "0003")


async def seed_business_database(database: str, count: int = 10000, batch_size: int = 1000) -> None:
    if not 1 <= count <= 100000 or not 1 <= batch_size <= 10000:
        raise ValueError("Business seed count/batch outside bounded limits")
    await check_initialization_target(database)
    engine = business_engine(database)
    hasher = hashlib.sha256()
    try:
        async with engine.begin() as connection:
            purpose = await connection.scalar(
                text("SELECT purpose FROM experiment_ownership WHERE id=1 FOR UPDATE")
            )
            if purpose == BUSINESS_PURPOSE:
                status = await connection.scalar(
                    text("SELECT status FROM experiment_dataset WHERE id=1")
                )
                if status != "ready":
                    raise ValueError("Incomplete dataset retained; refusing automatic resume")
                existing_count = await connection.scalar(
                    text("SELECT order_count FROM experiment_dataset WHERE id=1")
                )
                if existing_count != count:
                    raise ValueError("Existing dataset size differs; retained without reseeding")
                print("Owned ready dataset retained; no data overwritten.")
                return
            if purpose != "index-baseline-v1":
                raise ValueError("Refusing unexpected ownership")
            for table in TABLES:
                if await connection.scalar(text(f"SELECT COUNT(*) FROM {table}")):
                    raise ValueError("Refusing nonempty business seed target")
            await connection.execute(
                update(ExperimentOwnership)
                .where(ExperimentOwnership.id == 1)
                .values(purpose=BUSINESS_PURPOSE)
            )
            await connection.execute(
                insert(ExperimentDataset),
                [
                    {
                        "id": 1,
                        "seed": SEED,
                        "order_count": count,
                        "digest": "",
                        "status": "loading",
                    }
                ],
            )
            users, products = reference_rows()
            await connection.execute(insert(LabUser), users)
            await connection.execute(insert(LabProduct), products)
        for orders, items in order_batches(count, SEED, batch_size):
            async with engine.begin() as connection:
                await connection.execute(insert(LabOrder), orders)
                await connection.execute(insert(LabOrderItem), items)
            digest_batch(hasher, orders, items)
        async with engine.begin() as connection:
            await connection.execute(
                update(ExperimentDataset)
                .where(ExperimentDataset.id == 1)
                .values(status="ready", digest=hasher.hexdigest())
            )
        print(f"Business dataset ready: {count} orders; SHA256 {hasher.hexdigest()}")
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", choices=sorted(BUSINESS_DATABASES), required=True)
    subcommands = parser.add_subparsers(dest="action", required=True)
    subcommands.add_parser("init")
    seed = subcommands.add_parser("seed")
    seed.add_argument("--orders", type=int, default=10000)
    seed.add_argument("--batch-size", type=int, default=1000)
    arguments = parser.parse_args()
    try:
        if arguments.action == "init":
            initialize_business_database(arguments.database)
        else:
            asyncio.run(
                seed_business_database(arguments.database, arguments.orders, arguments.batch_size)
            )
    except ValueError as error:
        parser.exit(2, str(error) + "\n")
    except SQLAlchemyError:
        parser.exit(
            1,
            "Business initialization failed; check permissions/schema. Details redacted.\n",
        )


if __name__ == "__main__":
    main()
