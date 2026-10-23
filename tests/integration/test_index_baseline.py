"""Opt-in tests against the isolated experiment instance; no table clearing."""

import asyncio
import os

import pytest
from sqlalchemy import insert, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from concurrency_lab.experiments.dataset import seed_database
from concurrency_lab.experiments.index_baseline import can_optimize, migrate
from concurrency_lab.experiments.runner import measure
from concurrency_lab.experiments.safety import assert_owned, can_initialize, engine_for, revision
from concurrency_lab.models.commerce import LabOrderItem, LabProduct

pytestmark = pytest.mark.skipif(
    os.getenv("EXPERIMENT_INTEGRATION") != "1",
    reason="Opt-in isolated MySQL experiment tests: set EXPERIMENT_INTEGRATION=1",
)
DATABASE = "concurrency_lab_exp_002_test"


@pytest.fixture(scope="module")
def prepared():
    async def prepare():
        engine = engine_for(DATABASE)
        try:
            async with engine.connect() as connection:
                count = await connection.scalar(
                    text(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_schema=DATABASE()"
                    )
                )
                if not count:
                    return "empty"
                await assert_owned(connection, DATABASE)
                return await revision(connection)
        finally:
            await engine.dispose()

    state = asyncio.run(prepare())
    if state == "empty":
        asyncio.run(can_initialize(DATABASE))
        migrate(DATABASE, "0002")
        state = "0002"
    if state == "0002":
        engine = engine_for(DATABASE)

        async def empty():
            try:
                async with engine.connect() as conn:
                    return not await conn.scalar(text("SELECT COUNT(*) FROM experiment_dataset"))
            finally:
                await engine.dispose()

        if asyncio.run(empty()):
            asyncio.run(seed_database(DATABASE, 100, 42, 17))
    return state


async def test_nonempty_seed_refused(prepared):
    with pytest.raises(ValueError):
        await seed_database(DATABASE, 100, 42, 10)


async def test_foreign_key_and_check_constraints(prepared):
    engine = engine_for(DATABASE)
    try:
        with pytest.raises(IntegrityError):
            async with engine.begin() as conn:
                await conn.execute(
                    insert(LabOrderItem),
                    [
                        {
                            "id": 999999,
                            "order_id": 999999,
                            "product_id": 1,
                            "quantity": 1,
                            "unit_price": 1,
                        }
                    ],
                )
        with pytest.raises(DBAPIError):
            async with engine.begin() as conn:
                await conn.execute(
                    insert(LabProduct),
                    [{"id": 999999, "sku": "NEGATIVE", "name": "bad", "price": -1}],
                )
    finally:
        await engine.dispose()


async def test_duplicate_timestamps_keyset_walk(prepared):
    engine = engine_for(DATABASE)
    try:
        async with engine.connect() as conn:
            # Force tied sort keys inside a rollback-only transaction.
            await conn.execute(text("UPDATE lab_order SET created_at='2025-01-01' WHERE id<=30"))
            expected = (
                (
                    await conn.execute(
                        text("SELECT id FROM lab_order ORDER BY created_at DESC,id DESC")
                    )
                )
                .scalars()
                .all()
            )
            first = (
                await conn.execute(
                    text(
                        "SELECT id,created_at FROM lab_order "
                        "ORDER BY created_at DESC,id DESC LIMIT 7"
                    )
                )
            ).all()
            found = [r[0] for r in first]
            page = first
            while page:
                last = page[-1]
                page = (
                    await conn.execute(
                        text(
                            "SELECT id,created_at FROM lab_order WHERE created_at < :t "
                            "OR (created_at=:t AND id<:id) "
                            "ORDER BY created_at DESC,id DESC LIMIT 7"
                        ),
                        {"t": last[1], "id": last[0]},
                    )
                ).all()
                found.extend(r[0] for r in page)
            assert found == list(expected)
            assert len(set(found)) == 100
    finally:
        await engine.dispose()


def test_small_real_pipeline(prepared, tmp_path):
    if prepared == "0003":
        # Existing optimized test data is intentionally retained; never downgrade/clear it.
        pytest.skip("Optimized test data retained; full pipeline already executed on first run")
    asyncio.run(measure(DATABASE, "baseline", 3, tmp_path))
    with pytest.raises(ValueError):
        asyncio.run(measure(DATABASE, "baseline", 3, tmp_path))
    asyncio.run(can_optimize(DATABASE, tmp_path))
    migrate(DATABASE, "0003")
    result = asyncio.run(measure(DATABASE, "optimized", 3, tmp_path))
    assert result["page_ids"]["offset"] == result["page_ids"]["keyset"]
    assert all(q["iterators"] for q in result["queries"].values())
