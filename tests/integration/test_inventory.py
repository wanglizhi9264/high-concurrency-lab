"""Real MySQL transactions/constraints with fresh scenarios, never a database reset."""

import asyncio
import os
from contextlib import suppress
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select, text, update
from sqlalchemy.exc import OperationalError

from concurrency_lab.core.config import Settings
from concurrency_lab.main import create_app
from concurrency_lab.models.inventory import InventoryScenario, PurchaseOrder
from concurrency_lab.repositories.inventory_repository import InventoryRepository
from concurrency_lab.services.inventory_service import mysql_error_code

pytestmark = pytest.mark.skipif(
    os.getenv("INVENTORY_INTEGRATION") != "1",
    reason="Explicit owned inventory database migrated to0004 required",
)
SCENARIOS = "/api/v1/business/inventory/scenarios"
ORDERS = "/api/v1/business/purchases/orders"


@pytest_asyncio.fixture
async def lab():
    settings = Settings().model_copy(
        update={
            "business_enabled": True,
            "business_writes_enabled": True,
            "business_database": "concurrency_lab_business_test",
            "db_pool_size": 10,
            "db_max_overflow": 0,
            "db_pool_timeout": 3,
            "business_request_timeout": 6,
            "business_lock_wait_timeout": 1,
        }
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://lab"
        ) as api:
            yield app, api


async def scenario(api, initial=5):
    intent = {"scenario_id": str(uuid4()), "product_id": 1, "initial": initial}
    response = await api.post(SCENARIOS, json=intent)
    assert response.status_code == 201, response.text
    return response.json()["data"]["scenario"], intent


async def order(api, stock, key=None, quantity=1, user=1):
    return await api.post(
        ORDERS,
        json={"scenario_id": stock["id"], "user_id": user, "quantity": quantity},
        headers={"Idempotency-Key": str(key or uuid4())},
    )


async def audit(api, stock):
    response = await api.get(f"{SCENARIOS}/{stock['id']}/audit")
    assert response.status_code == 200, response.text
    assert response.json()["data"]["all_pass"], response.text
    return response.json()["data"]


async def test_exact_price_replay_soldout_cancel_and_audit(lab):
    _, api = lab
    stock, intent = await scenario(api, 1)
    assert (await api.post(SCENARIOS, json=intent)).json()["data"]["replayed"]
    key = uuid4()
    first = await order(api, stock, key)
    assert first.status_code == 201, first.text
    item = first.json()["data"]["order"]
    assert item["unit_price"] == item["total"] == "1.17"
    duplicate = await order(api, stock, key)
    assert duplicate.status_code == 200 and duplicate.json()["data"]["replayed"]
    assert duplicate.json()["data"]["order"]["id"] == item["id"]
    insufficient = await order(api, stock)
    assert (
        insufficient.status_code == 409
        and insufficient.json()["error"]["code"] == "insufficient_stock"
    )
    assert (await api.get(f"{ORDERS}/by-key/{key}")).json()["data"]["order"]["id"] == item["id"]
    for _ in range(2):
        response = await api.post(f"{ORDERS}/{item['id']}/state", json={"target": "cancelled"})
        assert response.status_code == 200
    assert (await audit(api, stock))["scenario"]["available"] == 1
    assert (await order(api, stock, key)).json()["data"]["order"]["status"] == "cancelled"
    # Cancelled historical units do not count against current available stock.
    another = await order(api, stock)
    assert another.status_code == 201
    report = await audit(api, stock)
    assert report["order_units"] == {"reserved": 1, "paid": 0, "cancelled": 1}


async def test_real_constraints_and_failed_transactions_leave_no_order(lab):
    app, api = lab
    stock, _ = await scenario(api, 2)
    key = uuid4()
    response = await order(api, stock, key, user=999999)
    assert response.status_code == 422
    assert (await api.get(f"{ORDERS}/by-key/{key}")).status_code == 404
    assert (await audit(api, stock))["scenario"]["available"] == 2
    identifier = stock["id"].replace("-", "")
    engine = app.state.resources.business.engine
    for values in ({"available": -1, "reserved": 3}, {"available": 3}):
        with pytest.raises(OperationalError) as failure:
            async with engine.begin() as connection:
                await connection.execute(
                    update(InventoryScenario)
                    .where(InventoryScenario.id == identifier)
                    .values(**values)
                )
        assert mysql_error_code(failure.value) == 3819
    created = (await order(api, stock)).json()["data"]["order"]
    with pytest.raises(OperationalError) as failure:
        async with engine.begin() as connection:
            await connection.execute(
                update(PurchaseOrder)
                .where(PurchaseOrder.id == created["id"])
                .values(total=PurchaseOrder.total + 1)
            )
    assert mysql_error_code(failure.value) == 3819
    await audit(api, stock)
    async with engine.connect() as connection:
        assert await connection.scalar(text("SELECT COUNT(*) FROM lab_order")) == 10000
        assert await connection.scalar(text("SELECT @@SESSION.innodb_lock_wait_timeout")) == 1


async def test_distinct_concurrent_orders_never_oversell(lab):
    _, api = lab
    stock, _ = await scenario(api, 5)
    responses = await asyncio.wait_for(asyncio.gather(*(order(api, stock) for _ in range(20))), 10)
    assert sum(r.status_code == 201 for r in responses) == 5
    assert all(r.status_code in (201, 409) for r in responses)
    assert all(
        r.status_code == 201 or r.json()["error"]["code"] == "insufficient_stock" for r in responses
    )
    report = await audit(api, stock)
    assert report["scenario"]["available"] == 0 and report["order_counts"]["reserved"] == 5


async def test_concurrent_same_key_old_snapshot_replays_even_when_sold_out(lab):
    _, api = lab
    stock, _ = await scenario(api, 1)
    key = uuid4()
    original = InventoryRepository.order_by_key
    both_read = asyncio.Event()
    misses = 0

    async def before_stock_lock(repository, value):
        nonlocal misses
        row = await original(repository, value)
        if row is None and misses < 2:
            misses += 1
            if misses == 2:
                both_read.set()
            await both_read.wait()
        return row

    with patch.object(InventoryRepository, "order_by_key", before_stock_lock):
        responses = await asyncio.wait_for(
            asyncio.gather(order(api, stock, key), order(api, stock, key)), 5
        )
    assert sorted(r.status_code for r in responses) == [200, 201]
    assert len({r.json()["data"]["order"]["id"] for r in responses}) == 1
    report = await audit(api, stock)
    assert report["scenario"]["reserved"] == 1 and report["order_counts"]["reserved"] == 1
    assert any(s["state"] == "error" for r in responses for s in r.json()["trace"]["spans"])


async def test_mismatched_key_and_terminal_race_preserve_stock(lab):
    _, api = lab
    stock, _ = await scenario(api, 10)
    key = uuid4()
    responses = await asyncio.gather(
        order(api, stock, key, quantity=2), order(api, stock, key, quantity=3)
    )
    assert sorted(r.status_code for r in responses) == [201, 409]
    assert (
        next(r for r in responses if r.status_code == 409).json()["error"]["code"]
        == "idempotency_conflict"
    )
    created = next(r for r in responses if r.status_code == 201).json()["data"]["order"]
    responses = await asyncio.wait_for(
        asyncio.gather(
            *(
                api.post(f"{ORDERS}/{created['id']}/state", json={"target": state})
                for state in ["paid", "cancelled"] * 5
            )
        ),
        8,
    )
    assert sum(r.status_code == 200 and r.json()["data"]["applied"] for r in responses) == 1
    assert any(r.status_code == 409 for r in responses)
    report = await audit(api, stock)
    assert report["scenario"]["reserved"] == 0


async def test_actual_lock_wait_timeout_rolls_back_and_retry_recovers(lab):
    app, api = lab
    stock, _ = await scenario(api, 2)
    key = uuid4()
    async with app.state.resources.business.engine.connect() as blocker:
        transaction = await blocker.begin()
        try:
            await blocker.execute(
                select(InventoryScenario.id)
                .where(InventoryScenario.id == stock["id"].replace("-", ""))
                .with_for_update()
            )
            response = await asyncio.wait_for(order(api, stock, key), 4)
            assert (
                response.status_code == 409
                and response.json()["error"]["code"] == "transaction_conflict"
            )
            assert response.headers["retry-after"] == "1"
        finally:
            await transaction.rollback()
    assert (await api.get(f"{ORDERS}/by-key/{key}")).status_code == 404
    assert (await order(api, stock, key)).status_code == 201
    await audit(api, stock)


async def test_cancel_before_commit_rolls_back_reservation_and_order(lab):
    _, api = lab
    stock, _ = await scenario(api, 2)
    key, reserved = uuid4(), asyncio.Event()
    original = InventoryRepository.reserve

    async def pause_after_reserve(repository, *args):
        result = await original(repository, *args)
        reserved.set()
        await asyncio.Event().wait()
        return result

    with patch.object(InventoryRepository, "reserve", pause_after_reserve):
        task = asyncio.create_task(order(api, stock, key))
        await asyncio.wait_for(reserved.wait(), 3)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert (await api.get(f"{ORDERS}/by-key/{key}")).status_code == 404
    assert (await audit(api, stock))["scenario"]["available"] == 2


async def test_actual_external_deadlock_records_victim_and_recovers(lab, record_property):
    app, api = lab
    stock, _ = await scenario(api, 5)
    created = (await order(api, stock)).json()["data"]["order"]
    padding = [await scenario(api, 2) for _ in range(6)]
    identifier = stock["id"].replace("-", "")
    locked = asyncio.Event()
    original = InventoryRepository.scenario

    async def signal_real_lock(repository, value, locked=False):
        row = await original(repository, value, locked)
        if locked and value == identifier:
            scenario_locked.set()
        return row

    scenario_locked = locked
    task = None
    external_victim = False
    try:
        async with app.state.resources.business.engine.connect() as blocker:
            transaction = await blocker.begin()
            try:
                await blocker.execute(text("SET SESSION innodb_lock_wait_timeout=5"))
                # Test-only uncommitted changes bias victim choice; every change is rolled back.
                for extra, _ in padding:
                    await blocker.execute(
                        update(InventoryScenario)
                        .where(InventoryScenario.id == extra["id"].replace("-", ""))
                        .values(
                            available=InventoryScenario.available - 1,
                            reserved=InventoryScenario.reserved + 1,
                        )
                    )
                await blocker.execute(
                    select(PurchaseOrder.id)
                    .where(PurchaseOrder.id == created["id"])
                    .with_for_update()
                )
                with patch.object(InventoryRepository, "scenario", signal_real_lock):
                    task = asyncio.create_task(
                        api.post(f"{ORDERS}/{created['id']}/state", json={"target": "paid"})
                    )
                    await asyncio.wait_for(scenario_locked.wait(), 3)
                    try:
                        # Only this external test transaction deliberately inverts lock order.
                        await asyncio.wait_for(
                            blocker.execute(
                                select(InventoryScenario.id)
                                .where(InventoryScenario.id == identifier)
                                .with_for_update()
                            ),
                            4,
                        )
                    except OperationalError as error:
                        assert mysql_error_code(error) == 1213
                        external_victim = True
            finally:
                await transaction.rollback()
                await blocker.execute(text("SET SESSION innodb_lock_wait_timeout=1"))
        response = await asyncio.wait_for(task, 4)
        if external_victim:
            assert response.status_code == 200, response.text
        else:
            assert response.status_code == 409, response.text
            assert response.json()["error"]["code"] == "transaction_conflict"
            assert (await audit(api, stock))["scenario"]["reserved"] == 1
            assert (
                await api.post(f"{ORDERS}/{created['id']}/state", json={"target": "paid"})
            ).status_code == 200
        victim = "external" if external_victim else "api"
        record_property("actual_deadlock_victim", victim)
        print("Actual MySQL1213 deadlock victim:", victim)
        report = await audit(api, stock)
        assert report["scenario"]["sold"] == 1 and report["scenario"]["reserved"] == 0
        for extra, _ in padding:
            assert (await audit(api, extra))["scenario"]["available"] == 2
    finally:
        if task is not None and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
