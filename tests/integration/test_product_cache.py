"""Real Redis scripts/expiry and real guarded MySQL reads; exact test keys only."""

import asyncio
import os
import socket
from unittest.mock import patch

import httpx
import pytest
import pytest_asyncio
from redis.asyncio import Redis

from concurrency_lab.cache.products import ProductCache, product_keys
from concurrency_lab.core.config import Settings
from concurrency_lab.main import create_app
from concurrency_lab.observability.recording import RequestObservation
from concurrency_lab.schemas.business import ProductDTO
from concurrency_lab.services.business_service import BusinessService

pytestmark = pytest.mark.skipif(
    os.getenv("CACHE_INTEGRATION") != "1",
    reason="Explicit owned cache/MySQL integration environment",
)
DATABASE = "concurrency_lab_business_test"
PATH = "/api/v1/business/cache/products/1"


@pytest_asyncio.fixture
async def lab():
    settings = Settings().model_copy(
        update={
            "business_enabled": True,
            "business_database": DATABASE,
            "db_pool_size": 5,
            "db_max_overflow": 0,
            "redis_max_connections": 32,  # Isolate fill coordination from client pool exhaustion.
        }
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        redis = app.state.resources.redis
        keys = [
            key
            for identifier in (1, 999)
            for key in vars(product_keys(DATABASE, identifier)).values()
        ]
        await redis.delete(*keys)
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url="http://lab"
            ) as api:
                yield app, api, redis
        finally:
            await redis.delete(*keys)


def sql_count(response):
    return sum(span["kind"] == "sql_execute_fetch" for span in response.json()["trace"]["spans"])


async def test_bypass_miss_hit_expiry_invalidation_and_inspection(lab):
    _, api, redis = lab
    bypass = await api.get(PATH + "?mode=bypass")
    assert bypass.status_code == 200 and sql_count(bypass) == 2
    assert not any(s["kind"] == "redis_command" for s in bypass.json()["trace"]["spans"])
    cold = await api.get(PATH + "?ttl_seconds=1")
    assert cold.json()["cache"]["initial_lookup"] == "miss"
    assert cold.json()["cache"]["fill_published"] is True and sql_count(cold) == 2
    hit = await api.get(PATH)
    assert hit.json()["cache"]["initial_lookup"] == "hit" and sql_count(hit) == 0
    assert bypass.json()["data"] == cold.json()["data"] == hit.json()["data"]
    state = (await api.get(PATH + "/state")).json()["cache"]
    assert 0 < state["ttl_ms"] <= 1100 and state["memory_bytes"] > 0
    await asyncio.sleep(state["ttl_ms"] / 1000 + 0.1)
    assert await redis.pttl(product_keys(DATABASE, 1).value) == -2
    assert (await api.get(PATH)).json()["cache"]["initial_lookup"] == "miss"
    invalidated = await api.delete(PATH)
    assert invalidated.json()["cache"]["outcome"] == "invalidated"
    assert await redis.pttl(product_keys(DATABASE, 1).value) == -2
    assert (await api.get(PATH)).json()["cache"]["fill_published"] is True


async def test_corrupt_and_missing_products_never_return_invented_data(lab):
    _, api, redis = lab
    await redis.set(product_keys(DATABASE, 1).value, "invalid-json", px=5000)
    response = await api.get(PATH)
    assert response.status_code == 200 and response.json()["data"]["price"] == "1.17"
    assert response.json()["cache"]["reason"] == "invalid_entry"
    for _ in range(2):
        response = await api.get(PATH.replace("/1", "/999"))
        assert response.status_code == 404 and sql_count(response) == 2
    assert await redis.exists(product_keys(DATABASE, 999).value) == 0
    await redis.set(product_keys(DATABASE, 1).generation, "invalid-generation")
    response = await api.get(PATH)
    assert response.json()["data"]["price"] == "1.17" and sql_count(response) == 2
    assert response.json()["cache"]["reason"] == "invalid_generation"
    assert (
        response.json()["cache"]["redis_available"] is True
    )  # Corruption is not connectivity loss.
    state = (await api.get(PATH + "/state")).json()["cache"]
    assert state["outcome"] == "degraded" and state["ttl_ms"] is None


async def test_real_generation_and_lease_fences(lab):
    _, _, redis = lab
    cache = ProductCache(redis, RequestObservation(DATABASE), 1)
    product = ProductDTO(id=1, sku="test", name="test", price="1.17")
    generation = await cache.acquire("old", lease_ms=80)
    assert generation is not None
    await asyncio.sleep(0.12)
    current_generation = await cache.acquire("new")
    assert current_generation is not None
    await cache.release("old")
    assert await redis.get(cache.keys.lease) == "new"
    assert not await cache.publish(product, generation, "old", 1000)
    assert await cache.publish(product, current_generation, "new", 1000)
    await cache.release("new")
    generation = await cache.acquire("before-invalidate")
    assert generation is not None
    await cache.invalidate()
    assert not await cache.publish(product, generation, "before-invalidate", 1000)
    assert await redis.get(cache.keys.value) is None


async def test_concurrent_cold_reads_coalesce_and_bound_wait(lab):
    _, api, _ = lab
    original = BusinessService.execute_read

    async def held_read(service, *args):
        result = await original(service, *args)
        await asyncio.sleep(0.1)
        return result

    with patch.object(BusinessService, "execute_read", held_read):
        responses = await asyncio.wait_for(asyncio.gather(*(api.get(PATH) for _ in range(12))), 5)
    assert all(r.status_code == 200 and r.json()["data"]["price"] == "1.17" for r in responses)
    assert any(r.json()["cache"]["outcome"] == "coalesced" for r in responses)
    assert sum(sql_count(r) for r in responses) == 2
    await api.delete(PATH)

    async def slow_read(service, *args):
        result = await original(service, *args)
        await asyncio.sleep(0.4)
        return result

    with patch.object(BusinessService, "execute_read", slow_read):
        responses = await asyncio.wait_for(asyncio.gather(*(api.get(PATH) for _ in range(6))), 5)
    assert all(r.status_code == 200 for r in responses)
    assert any(r.json()["cache"]["reason"] == "coordination_deadline" for r in responses)
    assert sum(sql_count(r) for r in responses) > 2


async def test_real_unreachable_redis_falls_back_and_recovers(lab):
    app, api, redis = lab
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    unavailable = Redis(
        host="127.0.0.1",
        port=port,
        socket_connect_timeout=0.05,
        socket_timeout=0.05,
        decode_responses=True,
    )
    try:
        app.state.resources.redis = unavailable
        response = await api.get(PATH)
        assert response.status_code == 200 and response.json()["data"]["price"] == "1.17"
        assert response.json()["cache"]["outcome"] == "degraded" and sql_count(response) == 2
        assert str(port) not in response.text
    finally:
        app.state.resources.redis = redis
        await unavailable.aclose()
    assert (await api.get(PATH)).json()["cache"]["fill_published"] is True
    assert (await api.get(PATH)).json()["cache"]["initial_lookup"] == "hit"


async def test_real_client_pool_exhaustion_falls_back_and_recovers(lab):
    from concurrency_lab.cache.client import create_redis

    app, api, original_client = lab
    limited = create_redis(Settings().model_copy(update={"redis_max_connections": 1}))
    connection = await limited.connection_pool.get_connection()
    try:
        app.state.resources.redis = limited
        response = await api.get(PATH)
        assert response.status_code == 200 and sql_count(response) == 2
        assert response.json()["cache"]["outcome"] == "degraded"
        await limited.connection_pool.release(connection)
        assert (await api.get(PATH)).json()["cache"]["fill_published"] is True
    finally:
        app.state.resources.redis = original_client
        await limited.aclose()


async def test_active_invalidation_rejects_a_real_inflight_fill(lab):
    _, api, redis = lab
    sql_done, resume = asyncio.Event(), asyncio.Event()
    original = BusinessService.execute_read

    async def held_after_sql(service, *args):
        product = await original(service, *args)
        sql_done.set()
        await resume.wait()
        return product

    with patch.object(BusinessService, "execute_read", held_after_sql):
        task = asyncio.create_task(api.get(PATH))
        try:
            await asyncio.wait_for(sql_done.wait(), 3)
            assert (await api.delete(PATH)).json()["cache"]["outcome"] == "invalidated"
        finally:
            resume.set()
        response = await asyncio.wait_for(task, 3)
    assert response.json()["data"]["price"] == "1.17"
    assert response.json()["cache"]["fill_published"] is False
    assert response.json()["cache"]["reason"] == "generation_or_lease_changed"
    assert await redis.get(product_keys(DATABASE, 1).value) is None


async def test_cancelled_owner_releases_or_expires_and_recovers(lab):
    _, api, redis = lab
    entered = asyncio.Event()
    original = BusinessService.execute_read

    async def paused_read(service, *args):
        result = await original(service, *args)
        entered.set()
        await asyncio.Event().wait()
        return result

    with patch.object(BusinessService, "execute_read", paused_read):
        task = asyncio.create_task(api.get(PATH))
        await asyncio.wait_for(entered.wait(), 3)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    await asyncio.sleep(1.05)
    assert not await redis.exists(product_keys(DATABASE, 1).lease)
    assert (await api.get(PATH)).status_code == 200
