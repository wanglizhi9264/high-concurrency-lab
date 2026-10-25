"""Policy and contract tests; real Redis semantics are covered independently."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError

from concurrency_lab.cache.products import ProductCache, product_keys
from concurrency_lab.core.config import Settings
from concurrency_lab.main import create_app
from concurrency_lab.observability.recording import RequestObservation


def test_key_scope_and_bounds():
    assert product_keys("concurrency_lab_business_test", 1).value.endswith(":product:1:value")
    for database, identifier in [
        ("concurrency_lab", 1),
        ("concurrency_lab_business", 0),
        ("concurrency_lab_business", 1001),
    ]:
        with pytest.raises(ValueError):
            product_keys(database, identifier)


@pytest.mark.parametrize(
    "raw",
    [
        '{"schema_version":99}',
        '{"database":"concurrency_lab_business","generation":0,"product":{"id":1,"sku":"s","name":"n","price":"1.17"}}',
        '{"database":"concurrency_lab_business_test","generation":0,"product":{"id":2,"sku":"s","name":"n","price":"1.17"}}',
    ],
)
async def test_invalid_cached_product_is_not_returned(raw):
    redis = AsyncMock()
    redis.mget.return_value = ["0", raw]
    observation = RequestObservation("concurrency_lab_business_test")
    lookup = await ProductCache(redis, observation, 1).lookup()
    assert lookup.product is None and lookup.invalid
    assert any(
        span.kind == "cache_validation" and span.state == "error" for span in observation.spans
    )


async def test_redis_failure_is_safe_and_measured():
    from concurrency_lab.cache.products import CacheUnavailable

    redis = AsyncMock()
    redis.mget.side_effect = RedisConnectionError("private address and secret")
    observation = RequestObservation("concurrency_lab_business_test")
    with pytest.raises(CacheUnavailable, match="redis_unavailable"):
        await ProductCache(redis, observation, 1).lookup()
    span = observation.spans[0]
    assert span.kind == "redis_command" and span.state == "error"
    assert "secret" not in span.model_dump_json()


def test_cache_api_disabled_and_invalid_input_preserve_envelope():
    settings = Settings(
        _env_file=None, mysql_password="test", redis_password="test", business_enabled=False
    )
    with TestClient(create_app(settings)) as api:
        disabled = api.get("/api/v1/business/cache/products/1")
        assert disabled.status_code == 503
        assert disabled.json()["error"]["code"] == "business_disabled"
        invalid = api.get("/api/v1/business/cache/products/1001")
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "invalid_input"
        assert invalid.json()["trace"]["spans"][-1]["kind"] == "validation"


async def test_failed_publication_does_not_repeat_mysql_read():
    from types import SimpleNamespace

    from concurrency_lab.schemas.business import ProductDTO
    from concurrency_lab.services.product_cache import ProductCacheService

    observation = RequestObservation("concurrency_lab_business_test")
    business = SimpleNamespace(
        observation=observation,
        budget=5,
        execute_read=AsyncMock(return_value=ProductDTO(id=1, sku="s", name="n", price="1.17")),
    )
    redis = AsyncMock()
    redis.mget.return_value = ["0", None]
    redis.eval.side_effect = ["0", RedisConnectionError("private"), 1]
    service = ProductCacheService(business, redis, 1)
    product = await service.read(False, 5)
    assert product.price == ProductDTO(id=1, sku="s", name="n", price="1.17").price
    business.execute_read.assert_awaited_once()
    assert service.metadata.outcome == "degraded" and service.metadata.served_from == "mysql"


@pytest.mark.parametrize(
    "url, concurrency",
    [
        ("https://example.com", 6),
        ("http://127.0.0.1:18002/other", 6),
        ("http://user:password@127.0.0.1:18002", 6),
        ("http://127.0.0.1:18002", 21),
    ],
)
def test_recording_script_rejects_unsafe_target_before_output(tmp_path, url, concurrency):
    import asyncio
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "cache_acceptance_runner",
        Path(__file__).resolve().parents[2] / "scripts/verify_cache_lab.py",
    )
    assert spec and spec.loader
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    with pytest.raises(ValueError, match="loopback"):
        asyncio.run(runner.record_experiment(url, tmp_path, concurrency))
    assert list(tmp_path.iterdir()) == []
