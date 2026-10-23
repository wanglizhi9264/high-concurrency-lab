import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from concurrency_lab.core.config import Settings
from concurrency_lab.main import create_app
from concurrency_lab.services.health import bounded_check


def settings():
    return Settings(_env_file=None, mysql_password="test", redis_password="test")


@pytest.mark.parametrize(
    "mysql,redis,code",
    [(True, True, 200), (False, True, 503), (True, False, 503), (False, False, 503)],
)
def test_health(mysql, redis, code):
    with (
        patch("concurrency_lab.services.health.mysql_ping", AsyncMock(return_value=mysql)),
        patch("concurrency_lab.services.health.redis_ping", AsyncMock(return_value=redis)),
    ):
        app = create_app(settings())
        with TestClient(app) as client:
            assert client.get("/health/live").json() == {"status": "alive"}
            response = client.get("/health/ready")
            assert response.status_code == code
            assert response.json()["checks"] == {
                "mysql": "ok" if mysql else "unavailable",
                "redis": "ok" if redis else "unavailable",
            }


async def test_timeout_and_error_redaction():
    async def hanging():
        await asyncio.sleep(10)
        return True

    async def failing():
        raise RuntimeError("private-password")

    assert await asyncio.wait_for(bounded_check(hanging, 0.01), 0.5) is False
    assert await bounded_check(failing, 0.1) is False


def test_cleanup():
    with (
        patch("concurrency_lab.main.create_engine") as engine_factory,
        patch("concurrency_lab.main.create_redis") as redis_factory,
    ):
        engine_factory.return_value.dispose = AsyncMock()
        redis_factory.return_value.aclose = AsyncMock()
        with TestClient(create_app(settings())) as client:
            assert client.get("/health/live").status_code == 200
        engine_factory.return_value.dispose.assert_awaited_once()
        redis_factory.return_value.aclose.assert_awaited_once()


def test_partial_initialization_cleanup():
    with (
        patch("concurrency_lab.main.create_engine") as factory,
        patch("concurrency_lab.main.create_redis", side_effect=RuntimeError("init failure")),
    ):
        factory.return_value.dispose = AsyncMock()
        with pytest.raises(RuntimeError, match="init failure"), TestClient(create_app(settings())):
            pass
        factory.return_value.dispose.assert_awaited_once()


async def test_session_dependency_closes_when_generator_closed():
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from concurrency_lab.db.session import get_session

    session = AsyncMock()
    context = AsyncMock()
    context.__aenter__.return_value = session
    factory = MagicMock(return_value=context)
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(resources=SimpleNamespace(sessions=factory)))
    )
    dependency = get_session(request)
    assert await anext(dependency) is session
    await dependency.aclose()
    context.__aexit__.assert_awaited_once()


def test_api_timeout_keeps_live_available():
    async def hanging(*args):
        await asyncio.sleep(10)
        return True

    config = settings()
    config.readiness_timeout = 0.01
    with patch("concurrency_lab.services.health.mysql_ping", hanging):
        with TestClient(create_app(config)) as client:
            response = client.get("/health/ready")
            assert response.status_code == 503
            assert response.json()["checks"]["mysql"] == "unavailable"
            assert client.get("/health/live").status_code == 200
