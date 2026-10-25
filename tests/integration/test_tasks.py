"""Real scoped MySQL/Redis worker protocol. No resets or broad key deletion."""

import asyncio
import os
import sys
from contextlib import suppress
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

import httpx
import pytest
import pytest_asyncio
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import func, select, text

from concurrency_lab.cache.task_stream import TaskStream
from concurrency_lab.core.config import Settings
from concurrency_lab.domain.tasks import WorkerPolicy
from concurrency_lab.main import create_app
from concurrency_lab.models.tasks import OrderReceipt
from concurrency_lab.repositories.task_repository import TaskRepository
from concurrency_lab.workers.runtime import WorkerRuntime

pytestmark = pytest.mark.skipif(
    os.getenv("TASK_INTEGRATION") != "1", reason="Explicit owned0005 task lab required"
)
ROOT = Path(__file__).resolve().parents[2]
TASKS = "/api/v1/business/tasks"


@pytest_asyncio.fixture
async def lab():
    settings = Settings().model_copy(
        update={
            "business_enabled": True,
            "business_writes_enabled": True,
            "business_database": "concurrency_lab_business_test",
            "db_pool_size": 10,
            "business_request_timeout": 6,
        }
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://lab"
        ) as api:
            yield app, api


async def paid_order(api, paid=True):
    scope = uuid4()
    result = await api.post(
        "/api/v1/business/inventory/scenarios",
        json={"scenario_id": str(scope), "product_id": 1, "initial": 5},
    )
    assert result.status_code == 201, result.text
    result = await api.post(
        "/api/v1/business/purchases/orders",
        json={"scenario_id": str(scope), "user_id": 1, "quantity": 1},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert result.status_code == 201, result.text
    order = result.json()["data"]["order"]
    if paid:
        result = await api.post(
            f"/api/v1/business/purchases/orders/{order['id']}/state", json={"target": "paid"}
        )
        assert result.status_code == 200, result.text
    return scope, order["id"]


async def create_task(api, order_id, **options):
    intent = {"task_id": str(uuid4()), "order_id": order_id, **options}
    result = await api.post(TASKS, json=intent)
    assert result.status_code == 201, result.text
    return UUID(intent["task_id"]), intent


async def detail(api, task_id):
    result = await api.get(f"{TASKS}/{task_id}")
    assert result.status_code == 200, result.text
    return result.json()["data"]


async def test_atomic_acceptance_idempotency_unpaid_and_no_broker_dependency(lab):
    app, api = lab
    scope, identifier = await paid_order(api)
    # Creation never needs Redis; use an actually unavailable loopback broker.
    old = app.state.resources.redis
    from redis.asyncio import Redis

    unavailable = Redis(host="127.0.0.1", port=1, socket_connect_timeout=0.1, decode_responses=True)
    app.state.resources.redis = unavailable
    try:
        task_id, intent = await create_task(api, identifier)
        replay = await api.post(TASKS, json=intent)
        assert replay.status_code == 200 and replay.json()["data"]["replayed"]
        assert (await api.post(TASKS, json={**intent, "max_attempts": 1})).status_code == 409
        data = await detail(api, task_id)
        assert data["task"]["state"] == "queued" and data["outbox"]["publish_count"] == 0
        assert data["task"]["created_at"].endswith("Z")
        assert "lease_token" not in data["task"]
        snapshot = (await api.get(f"/api/v1/business/task-queues/{scope}")).json()["data"]
        assert snapshot["redis_available"] is False and snapshot["pending"] is None
    finally:
        app.state.resources.redis = old
        await unavailable.aclose()
    worker = runtime(app, scope)
    try:
        assert (await until_terminal(worker, api, task_id))["task"]["state"] == "succeeded"
    finally:
        await old.delete(worker.stream.key)
    _, unpaid = await paid_order(api, False)
    assert (
        await api.post(TASKS, json={"task_id": str(uuid4()), "order_id": unpaid})
    ).status_code == 409


async def test_real_success_duplicates_and_retry_history(lab):
    from concurrency_lab.cache.task_stream import TaskStream
    from concurrency_lab.domain.tasks import WorkerPolicy
    from concurrency_lab.workers.runtime import WorkerRuntime

    app, api = lab
    scope, identifier = await paid_order(api)
    task_id, _ = await create_task(api, identifier, fault_plan={"fail_first_attempts": 1})
    stream = TaskStream(
        app.state.resources.redis, app.state.resources.settings.business_database, scope
    )
    worker = WorkerRuntime(app.state.resources.business, stream, WorkerPolicy(0.2, 1))
    try:
        for _ in range(40):
            await worker.cycle()
            data = await detail(api, task_id)
            if data["task"]["state"] == "succeeded":
                break
            await asyncio.sleep(0.05)
        assert data["task"]["state"] == "succeeded"
        assert [a["status"] for a in data["attempts"]] == ["failed", "succeeded"]
        assert data["receipt"]["total"] == "1.17"
        receipt = data["receipt"]["id"]
        await stream.publish(task_id.hex)
        await worker.cycle()
        assert (await detail(api, task_id))["receipt"]["id"] == receipt
    finally:
        await app.state.resources.redis.delete(stream.key)


def runtime(app, scope):
    stream = TaskStream(
        app.state.resources.redis, app.state.resources.settings.business_database, scope
    )
    return WorkerRuntime(app.state.resources.business, stream, WorkerPolicy(0.2, 1))


async def until_terminal(worker, api, task_id, cycles=60):
    for _ in range(cycles):
        await worker.cycle()
        data = await detail(api, task_id)
        if data["task"]["state"] in ("failed", "succeeded"):
            return data
        await asyncio.sleep(0.05)
    pytest.fail("Actual task did not reach terminal state within bounded cycles")


async def receipt_count(app, order_id):
    async with app.state.resources.business.engine.connect() as connection:
        return await connection.scalar(
            select(func.count()).select_from(OrderReceipt).where(OrderReceipt.order_id == order_id)
        )


async def test_publish_unknown_commit_and_ack_failure_do_not_duplicate_effect(lab):
    app, api = lab
    scope, order_id = await paid_order(api)
    identifier, _ = await create_task(api, order_id)
    worker = runtime(app, scope)
    original = TaskRepository.change_outbox

    async def crash_before_confirmation(repository, task_id, values):
        if "last_message_id" in values:
            raise RuntimeError("Controlled failure after real XADD before database confirmation")
        return await original(repository, task_id, values)

    try:
        with patch.object(TaskRepository, "change_outbox", crash_before_confirmation):
            with pytest.raises(RuntimeError):
                await worker.dispatcher.publish_due()
        assert await app.state.resources.redis.xlen(worker.stream.key) == 1
        assert (await detail(api, identifier))["outbox"]["publish_count"] == 0
        # Durable intent publishes again: transport has two actual entries.
        assert await worker.dispatcher.publish_due() == 1
        assert await app.state.resources.redis.xlen(worker.stream.key) == 2
        with patch.object(
            worker.stream, "acknowledge", side_effect=RedisConnectionError("controlled ACK outage")
        ):
            await worker.consume()
        data = await detail(api, identifier)
        assert data["task"]["state"] == "succeeded"
        assert any(e["details"].get("outcome") == "unconfirmed" for e in data["events"])
        assert await receipt_count(app, order_id) == 1
        await worker.consume()  # Second duplicate terminal delivery.
        await asyncio.sleep(1.05)  # Real Redis PEL idle threshold, then actual XAUTOCLAIM.
        await worker.consume()
        assert await receipt_count(app, order_id) == 1
        pending = await app.state.resources.redis.xpending(worker.stream.key, worker.stream.group)
        assert pending["pending"] == 0
    finally:
        await app.state.resources.redis.delete(worker.stream.key)


async def test_deadline_exhaustion_and_linked_successor_preserve_failed_history(lab):
    app, api = lab
    scope, order_id = await paid_order(api)
    identifier, _ = await create_task(api, order_id, max_attempts=2, fault_plan={"delay_ms": 400})
    worker = runtime(app, scope)
    try:
        data = await until_terminal(worker, api, identifier)
        assert data["task"]["state"] == "failed"
        assert [a["status"] for a in data["attempts"]] == ["timeout", "timeout"]
        assert all(a["handler_ms"] >= 190 for a in data["attempts"])
        assert data["receipt"] is None
        successor = {"task_id": str(uuid4()), "disable_faults": True}
        response = await api.post(f"{TASKS}/{identifier}/retry", json=successor)
        assert response.status_code == 201, response.text
        assert (await api.post(f"{TASKS}/{identifier}/retry", json=successor)).status_code == 200
        assert (
            await api.post(
                f"{TASKS}/{identifier}/retry", json={**successor, "disable_faults": False}
            )
        ).status_code == 409
        recovered = await until_terminal(worker, api, UUID(successor["task_id"]))
        assert recovered["task"]["state"] == "succeeded"
        assert recovered["task"]["retry_of"] == str(identifier)
        assert (await detail(api, identifier))["attempts"] == data["attempts"]
        assert await receipt_count(app, order_id) == 1
    finally:
        await app.state.resources.redis.delete(worker.stream.key)


async def test_two_tasks_one_order_and_stale_success_failure_are_fenced(lab):
    app, api = lab
    scope, order_id = await paid_order(api)
    first, _ = await create_task(api, order_id)
    second, _ = await create_task(api, order_id)
    worker, other = runtime(app, scope), runtime(app, scope)
    a = (await worker.execution.claim(first.hex)).claim
    b = (await other.execution.claim(second.hex)).claim
    assert a and b
    assert (await other.execution.claim(first.hex)).disposition == "busy"
    assert not await other.execution.finalize(
        replace(a, token=uuid4().hex), None, "controlled_failure", 1
    )
    assert all(await asyncio.gather(worker.execution.execute(a), other.execution.execute(b)))
    assert await receipt_count(app, order_id) == 1
    assert (await detail(api, first))["receipt"]["id"] == (await detail(api, second))["receipt"][
        "id"
    ]
    assert not await worker.execution.finalize(a, {}, None, 1)
    assert not await worker.execution.finalize(a, None, "handler_timeout", 1)


async def test_expiry_during_final_receipt_mutation_rolls_back_insert(lab):
    app, api = lab
    scope, order_id = await paid_order(api)
    identifier, _ = await create_task(api, order_id)
    worker = runtime(app, scope)
    claim = (await worker.execution.claim(identifier.hex)).claim
    assert claim
    original = TaskRepository.materialize_receipt

    async def slow_receipt(repository, order, snapshot):
        result = await original(repository, order, snapshot)
        await asyncio.sleep(1.05)  # Lease expires after real INSERT, before fenced UPDATE.
        return result

    with patch.object(TaskRepository, "materialize_receipt", slow_receipt):
        assert not await worker.execution.execute(claim)
    assert await receipt_count(app, order_id) == 0
    replacement = (await worker.execution.claim(identifier.hex)).claim
    assert replacement and replacement.number == 2 and replacement.token != claim.token
    assert not await worker.execution.finalize(claim, None, "controlled_failure", 1)
    assert await worker.execution.execute(replacement)
    data = await detail(api, identifier)
    assert data["attempts"][0]["status"] == "abandoned"
    assert data["attempts"][0]["finished_at"] is None and data["attempts"][0]["handler_ms"] is None
    assert data["attempts"][0]["abandoned_at"] is not None


@pytest.mark.parametrize("max_attempts", [1, 3])
async def test_actual_child_crash_after_claim_and_recovery(lab, max_attempts):
    app, api = lab
    scope, order_id = await paid_order(api)
    identifier, _ = await create_task(api, order_id, max_attempts=max_attempts)
    worker = runtime(app, scope)
    env = {**os.environ, "BUSINESS_WRITES_ENABLED": "true", "PYTHONUTF8": "1"}
    child = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "concurrency_lab.workers.receipts",
        "--database",
        worker.stream.database,
        "--scenario",
        str(scope),
        "--timeout-seconds",
        ".2",
        "--lease-seconds",
        "1",
        "--crash-after-claim",
        "--max-cycles",
        "10",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=ROOT,
        env=env,
    )
    try:
        stdout, stderr = await asyncio.wait_for(child.communicate(), 20)
        assert child.returncode == 70, stderr.decode()
        assert "crash_after_committed_claim" in stdout.decode()
        data = await detail(api, identifier)
        assert data["task"]["state"] == "running" and data["attempts"][0]["status"] == "running"
        assert data["attempts"][0]["finished_at"] is None
        data = await until_terminal(worker, api, identifier)
        expected = "failed" if max_attempts == 1 else "succeeded"
        assert data["task"]["state"] == expected
        assert data["attempts"][0]["status"] == "abandoned"
        assert data["attempts"][0]["handler_ms"] is None
        assert data["attempts"][0]["finished_at"] is None
        assert await receipt_count(app, order_id) == (0 if max_attempts == 1 else 1)
    finally:
        if child.returncode is None:
            child.kill()
            with suppress(Exception):
                await child.wait()
        await app.state.resources.redis.delete(worker.stream.key)


async def test_broker_transport_loss_repaired_and_foreign_messages_do_not_mutate(lab):
    app, api = lab
    scope, order_id = await paid_order(api)
    identifier, _ = await create_task(api, order_id)
    foreign_scope, foreign_order = await paid_order(api)
    foreign, _ = await create_task(api, foreign_order)
    worker = runtime(app, scope)
    try:
        await worker.dispatcher.publish_due()
        await app.state.resources.redis.delete(
            worker.stream.key
        )  # Exact fresh-test transport only.
        # DB cooldown is real; exercise reconciliation after actual eligibility.
        async with app.state.resources.business.engine.connect() as connection:
            for _ in range(150):
                ready = await connection.scalar(
                    text(
                        "SELECT next_publish_at <= UTC_TIMESTAMP(6) "
                        "FROM task_outbox WHERE task_id=:id"
                    ),
                    {"id": identifier.hex},
                )
                if ready:
                    break
                await asyncio.sleep(0.05)
            assert ready
        assert (await until_terminal(worker, api, identifier))["task"]["state"] == "succeeded"
        await worker.stream.publish(foreign.hex)
        await app.state.resources.redis.xadd(worker.stream.key, {"task_id": "malformed"})
        assert await worker.consume() == "invalid"
        assert await worker.consume() == "invalid_message"
        assert (await detail(api, foreign))["task"]["state"] == "queued"
        assert await receipt_count(app, foreign_order) == 0
        assert foreign_scope != scope
    finally:
        await app.state.resources.redis.delete(worker.stream.key)


async def test_cancel_after_committed_claim_preserves_lease_and_pending_for_recovery(lab):
    app, api = lab
    scope, order_id = await paid_order(api)
    identifier, _ = await create_task(api, order_id)
    worker = runtime(app, scope)
    entered, release = asyncio.Event(), asyncio.Event()
    original = worker.execution.handler

    async def interrupted_handler(claim):
        entered.set()  # consume reached handler only after claim TX committed.
        await release.wait()
        return await original(claim)

    operation = None
    try:
        await worker.dispatcher.publish_due()
        with patch.object(worker.execution, "handler", interrupted_handler):
            operation = asyncio.create_task(worker.consume())
            await asyncio.wait_for(entered.wait(), 3)
            running = await detail(api, identifier)
            assert running["task"]["state"] == "running"
            operation.cancel()
            with pytest.raises(asyncio.CancelledError):
                await operation
        assert await receipt_count(app, order_id) == 0
        pending = await app.state.resources.redis.xpending(worker.stream.key, worker.stream.group)
        assert pending["pending"] == 1  # No ACK or fabricated completion on cancellation.
        recovered = await until_terminal(runtime(app, scope), api, identifier)
        assert recovered["task"]["state"] == "succeeded"
        assert [a["status"] for a in recovered["attempts"]] == ["abandoned", "succeeded"]
        assert recovered["attempts"][0]["handler_ms"] is None
    finally:
        release.set()
        if operation is not None and not operation.done():
            operation.cancel()
            with suppress(asyncio.CancelledError):
                await operation
        await app.state.resources.redis.delete(worker.stream.key)


async def test_creation_failure_after_task_and_outbox_insert_rolls_back_all(lab):
    app, api = lab
    _, order_id = await paid_order(api)
    identifier = uuid4()
    original = TaskRepository.event

    async def fail_created(repository, task_id, kind, source, details):
        if kind == "created":
            raise RuntimeError("Controlled failure after actual Task and Outbox INSERT")
        return await original(repository, task_id, kind, source, details)

    with patch.object(TaskRepository, "event", fail_created):
        with pytest.raises(RuntimeError):
            await api.post(TASKS, json={"task_id": str(identifier), "order_id": order_id})
    assert (await api.get(f"{TASKS}/{identifier}")).status_code == 404
    async with app.state.resources.business.engine.connect() as connection:
        assert (
            await connection.scalar(
                text("SELECT COUNT(*) FROM task_outbox WHERE task_id=:id"), {"id": identifier.hex}
            )
            == 0
        )
    # Same intent is safe after known rollback, and normal creation still works.
    assert (
        await api.post(TASKS, json={"task_id": str(identifier), "order_id": order_id})
    ).status_code == 201
