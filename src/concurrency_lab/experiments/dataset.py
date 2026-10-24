"""Deterministic streaming data, fixed IDs and bounded per-batch transactions."""

import hashlib
import json
import random
import time
from collections.abc import Iterator
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import insert, text, update

from concurrency_lab.experiments.safety import assert_owned, engine_for, revision
from concurrency_lab.models.commerce import (
    ExperimentDataset,
    LabOrder,
    LabOrderItem,
    LabProduct,
    LabUser,
)

USER_COUNT = 1000
PRODUCT_COUNT = 100
GENERATOR_VERSION = 1


def price(product_id: int) -> Decimal:
    return Decimal(100 + product_id * 17) / 100


def reference_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Bounded deterministic catalog shared with the isolated business dataset."""
    users = [
        {
            "id": i,
            "username": f"user{i:04}",
            "email": f"user{i:04}@example.invalid",
            "created_at": datetime(2025, 1, 1),
        }
        for i in range(1, USER_COUNT + 1)
    ]
    products = [
        {"id": i, "sku": f"SKU{i:04}", "name": f"Product {i}", "price": price(i)}
        for i in range(1, PRODUCT_COUNT + 1)
    ]
    return users, products


def order_batches(
    count: int, seed: int, batch_size: int
) -> Iterator[tuple[list[dict[str, Any]], list[dict[str, Any]]]]:
    if count < 1 or not 1 <= batch_size <= 10000:
        raise ValueError("Positive count and batch size in [1,10000] required")
    rng = random.Random(seed)
    epoch = datetime(2025, 1, 1)
    for start in range(1, count + 1, batch_size):
        orders, items = [], []
        for order_id in range(start, min(start + batch_size, count + 1)):
            first = rng.randint(1, PRODUCT_COUNT)
            second = first % PRODUCT_COUNT + 1
            quantity = rng.randint(1, 5)
            orders.append(
                {
                    "id": order_id,
                    "user_id": rng.randint(1, USER_COUNT),
                    "created_at": epoch + timedelta(minutes=rng.randrange(1440)),
                    "total": price(first) * quantity + price(second),
                    "status": rng.choice(("created", "paid", "cancelled")),
                }
            )
            items.extend(
                [
                    {
                        "id": order_id * 2 - 1,
                        "order_id": order_id,
                        "product_id": first,
                        "quantity": quantity,
                        "unit_price": price(first),
                    },
                    {
                        "id": order_id * 2,
                        "order_id": order_id,
                        "product_id": second,
                        "quantity": 1,
                        "unit_price": price(second),
                    },
                ]
            )
        yield orders, items


def digest_batch(hasher: Any, orders: list[dict[str, Any]], items: list[dict[str, Any]]) -> None:
    # Interleave by order, so changing transaction batch size never changes data identity.
    for position, order in enumerate(orders):
        for row in (order, *items[position * 2 : position * 2 + 2]):
            hasher.update(
                (
                    json.dumps(row, sort_keys=True, default=str, separators=(",", ":")) + "\n"
                ).encode()
            )


async def seed_database(database: str, count: int, seed: int, batch_size: int) -> dict[str, Any]:
    if (
        database != "concurrency_lab_exp_002_test"
        and database != f"concurrency_lab_exp_002_{count}"
    ):
        raise ValueError("Scale must match the database suffix")
    if count < 1 or not 1 <= batch_size <= 10000:
        raise ValueError("Invalid count/batch size")
    engine = engine_for(database)
    started = time.perf_counter()
    hasher = hashlib.sha256()
    try:
        async with engine.begin() as connection:
            await assert_owned(connection, database)
            if await revision(connection) != "0002":
                raise ValueError("Generate only on baseline revision0002")
            for table in (
                "lab_order_item",
                "lab_order",
                "lab_user",
                "lab_product",
                "experiment_dataset",
            ):
                if await connection.scalar(text(f"SELECT COUNT(*) FROM {table}")):
                    raise ValueError("Refusing nonempty data; no automatic reset or resume")
            await connection.execute(
                insert(ExperimentDataset),
                [{"id": 1, "seed": seed, "order_count": count, "digest": "", "status": "loading"}],
            )
            users, products = reference_rows()
            await connection.execute(insert(LabUser), users)
            await connection.execute(insert(LabProduct), products)
        for orders, items in order_batches(count, seed, batch_size):
            async with engine.begin() as connection:
                await connection.execute(insert(LabOrder), orders)
                await connection.execute(insert(LabOrderItem), items)
            digest_batch(hasher, orders, items)
        async with engine.begin() as connection:
            await connection.execute(
                update(ExperimentDataset)
                .where(ExperimentDataset.id == 1)
                .values(digest=hasher.hexdigest(), status="ready")
            )
        elapsed = time.perf_counter() - started
        return {
            "orders": count,
            "items": count * 2,
            "seed": seed,
            "batch_size": batch_size,
            "digest": hasher.hexdigest(),
            "generator_version": GENERATOR_VERSION,
            "duration_seconds": elapsed,
            "orders_per_second": count / elapsed,
        }
    finally:
        await engine.dispose()
