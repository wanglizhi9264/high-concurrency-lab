"""Canonical year-distributed rows and streaming database identity, bounded client memory."""

import hashlib
import json
import random
import time
from collections import Counter
from collections.abc import Iterator
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from concurrency_lab.experiments.scale.safety import (
    assert_owned,
    engine_for,
    validate_batch_budget,
    validate_target,
)
from concurrency_lab.models.scale import QUERY_TABLES, dataset, tables

GENERATOR_VERSION = 1


def canonical_row(row: dict[str, Any]) -> bytes:
    return (json.dumps(row, sort_keys=True, default=str, separators=(",", ":")) + "\n").encode()


def row_batches(count: int, seed: int, batch_size: int) -> Iterator[list[dict[str, Any]]]:
    if count < 1 or not 1 <= batch_size <= 10000 or not 0 <= seed <= 2147483647:
        raise ValueError("Positive count, seed0..2^31-1 and batch1..10000 required")
    rng, epoch = random.Random(seed), datetime(2025, 1, 1)
    for start in range(1, count + 1, batch_size):
        rows = []
        for identifier in range(start, min(count + 1, start + batch_size)):
            rows.append(
                dict(
                    id=identifier,
                    created_at=epoch
                    + timedelta(days=rng.randrange(365), minutes=rng.randrange(96) * 15),
                    user_id=rng.randint(1, 1000),
                    total=(Decimal(rng.randint(1, 100000)) / 100).quantize(Decimal("0.01")),
                    status=rng.choice(("created", "paid", "cancelled")),
                    payload=f"order:{identifier}." + "x" * 120,
                )
            )
        yield rows


async def table_identity(connection: AsyncConnection, table: str) -> dict[str, Any]:
    if table not in tables:
        raise ValueError("Unknown009table")
    hasher, count, previous = hashlib.sha256(), 0, 0
    months: Counter[str] = Counter()
    statement = select(tables[table]).order_by(tables[table].c.id, tables[table].c.created_at)
    async with connection.stream(statement) as cursor:
        async for batch in cursor.mappings().partitions(1000):
            for mapping in batch:
                row = dict(mapping)
                if row["id"] <= previous:
                    raise ValueError("Generated id-only uniqueness/order invariant failed")
                previous = row["id"]
                hasher.update(canonical_row(row))
                count += 1
                months[row["created_at"].strftime("%Y-%m")] += 1
    return {
        "count": count,
        "digest": hasher.hexdigest(),
        "monthly_counts": dict(sorted(months.items())),
        "id_unique": True,
    }


async def dataset_identity(connection: AsyncConnection) -> dict[str, Any]:
    manifest = (await connection.execute(select(dataset))).mappings().one()
    if manifest["status"] != "ready":
        raise ValueError("Incomplete009dataset retained; no implicit resume")
    identities = {name: await table_identity(connection, name) for name in QUERY_TABLES}
    if any(
        v["count"] != manifest["order_count"] or v["digest"] != manifest["digest"]
        for v in identities.values()
    ):
        raise ValueError("Actual DB content differs from ready generation manifest")
    return {
        "seed": manifest["seed"],
        "order_count": manifest["order_count"],
        "generator_version": manifest["generator_version"],
        "digest": manifest["digest"],
        "tables": identities,
    }


async def seed_database(
    database: str, count: int, seed: int, batch_size: int, allow_ten_million: bool = False
) -> dict[str, Any]:
    validate_target(database, count, allow_ten_million)
    validate_batch_budget(count, batch_size)
    started = time.perf_counter()
    iterator = row_batches(count, seed, batch_size)
    first = next(iterator)  # Validate before persisting the loading marker.
    engine, hasher = engine_for(database), hashlib.sha256()
    sql_ms, samples = 0.0, []
    try:
        async with engine.begin() as connection:
            if await assert_owned(connection, database) != "scale001":
                raise ValueError("Seed requires baseline schema")
            if await connection.scalar(select(dataset.c.id)) is not None:
                raise ValueError("Dataset already present; no reset/resume")
            for name in QUERY_TABLES:
                if await connection.scalar(select(tables[name].c.id).limit(1)) is not None:
                    raise ValueError("Refusing nonempty query table")
            await connection.execute(
                insert(dataset).values(
                    id=1,
                    seed=seed,
                    order_count=count,
                    batch_size=batch_size,
                    generator_version=GENERATOR_VERSION,
                    digest="",
                    status="loading",
                    created_at=func.utc_timestamp(6),
                )
            )
        from itertools import chain

        for batch in chain([first], iterator):
            for row in batch:
                hasher.update(canonical_row(row))
            before = time.perf_counter()
            async with engine.begin() as connection:
                await assert_owned(connection, database)
                for name in QUERY_TABLES:
                    await connection.execute(insert(tables[name]), batch)
            elapsed = (time.perf_counter() - before) * 1000
            samples.append({"rows_per_twin": len(batch), "execute_commit_ms": elapsed})
            sql_ms += elapsed
        async with engine.begin() as connection:
            await connection.execute(
                update(dataset)
                .where(dataset.c.id == 1)
                .values(digest=hasher.hexdigest(), status="ready")
            )
        async with engine.connect() as connection:
            identity = await dataset_identity(connection)
        return {
            "dataset": identity,
            "batch_size": batch_size,
            "generation_insert_validation_wall_seconds": time.perf_counter() - started,
            "sql_transaction_ms": sql_ms,
            "batches": samples,
            "semantics": "Per batch ownership checks + two INSERTs + COMMIT; "
            "generation/hash/readback validation excluded from sql_transaction_ms",
        }
    finally:
        await engine.dispose()
