"""Actual isolated business DB behavior. No cleanup/reset of seeded data."""

import asyncio
import os
from unittest.mock import patch

import httpx
import pytest
from sqlalchemy import text

from concurrency_lab.core.config import Settings
from concurrency_lab.core.exceptions import BusinessFailure, FailureCode
from concurrency_lab.db.business import ObservedDatabase
from concurrency_lab.experiments.business_dataset import seed_business_database
from concurrency_lab.main import create_app
from concurrency_lab.observability.recording import RequestObservation
from concurrency_lab.repositories.product_repository import ProductRepository

pytestmark = pytest.mark.skipif(
    os.getenv("BUSINESS_INTEGRATION") != "1",
    reason="Requires explicitly provisioned owned business test database",
)


def configuration(**changes):
    return Settings().model_copy(
        update={
            "business_enabled": True,
            "business_database": "concurrency_lab_business_test",
            "db_pool_size": 1,
            "db_max_overflow": 0,
            "db_pool_timeout": 0.5,
            **changes,
        }
    )


async def test_real_reads_fixed_sql_count_and_safe_errors():
    app = create_app(configuration())
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://lab"
        ) as api:
            product = await api.get("/api/v1/business/products/1")
            assert product.status_code == 200
            result = product.json()
            assert result["data"]["price"] == "1.17"
            assert product.headers["x-request-id"] == result["trace"]["request_id"]
            assert result["trace"]["database"] == "concurrency_lab_business_test"
            trace = result["trace"]
            assert 0 <= trace["pool_before_offset_ms"] <= trace["pool_after_offset_ms"]
            assert trace["pool_after_offset_ms"] <= trace["service_elapsed_ms"]
            sql = [span for span in result["trace"]["spans"] if span["kind"] == "sql_execute_fetch"]
            assert len(sql) == 2  # ownership SQL plus primary-key business SQL
            assert any(span["kind"] == "acquire" for span in result["trace"]["spans"])
            detail = await api.get("/api/v1/business/orders/1")
            assert detail.status_code == 200
            assert len(detail.json()["data"]["items"]) == 2
            assert len([s for s in detail.json()["trace"]["spans"] if s["sql"]]) == 3
            missing = await api.get("/api/v1/business/products/999999")
            assert missing.status_code == 404
            assert missing.json()["error"]["code"] == "not_found"
            empty = await api.get("/api/v1/business/users/999999/orders")
            assert empty.json()["data"]["items"] == []
            invalid = await api.get("/api/v1/business/users/500/order-page?before_id=3")
            assert invalid.status_code == 422
            assert "x-request-id" in invalid.headers
            assert invalid.json()["error"]["code"] == "invalid_input"
            assert app.state.resources.business.engine.pool.checkedout() == 0


async def test_stable_cursor_walk_matches_real_ordering_and_no_duplicates():
    app = create_app(configuration())
    async with app.router.lifespan_context(app):
        engine = app.state.resources.business.engine
        async with engine.connect() as connection:
            expected = list(
                (
                    await connection.execute(
                        text(
                            "SELECT id FROM lab_order WHERE user_id=500 "
                            "ORDER BY created_at DESC,id DESC"
                        )
                    )
                ).scalars()
            )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://lab"
        ) as api:
            parameters = {"limit": 3}
            found = []
            while True:
                response = await api.get("/api/v1/business/users/500/order-page", params=parameters)
                assert response.status_code == 200
                data = response.json()["data"]
                found.extend(item["id"] for item in data["items"])
                if data["next_cursor"] is None:
                    break
                parameters = {"limit": 3, **data["next_cursor"]}
            assert found == expected
            assert len(set(found)) == len(found)


async def test_actual_pool_exhaustion_and_concurrent_recovery():
    app = create_app(configuration())
    async with app.router.lifespan_context(app):
        engine = app.state.resources.business.engine
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://lab"
        ) as api:
            async with engine.connect():
                blocked = await api.get("/api/v1/business/products/1")
                assert blocked.status_code == 503
                assert blocked.json()["error"]["code"] == "pool_timeout"
            responses = await asyncio.gather(
                *[api.get("/api/v1/business/products/1") for _ in range(8)]
            )
            assert all(response.status_code == 200 for response in responses)
            assert len({r.json()["trace"]["request_id"] for r in responses}) == 8
            assert engine.pool.checkedout() == 0


async def test_budget_cancellation_releases_real_connection_and_recovers():
    app = create_app(configuration(business_request_timeout=0.3))

    async def slow_query(self, product_id):
        # Server-side sleep is a controlled read-only integration fault, never HTTP input.
        return await self.database.fetch_rows(
            text("SELECT SLEEP(1) AS controlled_test_delay"),
            "tests/integration/test_business.py",
        )

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://lab"
        ) as api:
            with patch.object(ProductRepository, "get_product_by_id", slow_query):
                response = await api.get("/api/v1/business/products/1")
            assert response.status_code == 504
            assert response.json()["error"]["code"] == "request_timeout"
            assert any(span["state"] == "timeout" for span in response.json()["trace"]["spans"])
            assert app.state.resources.business.engine.pool.checkedout() == 0
            assert (await api.get("/api/v1/business/products/1")).status_code == 200


async def test_real_connection_failure_is_sanitized():
    app = create_app(configuration(mysql_port=1))
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://lab"
        ) as api:
            response = await api.get("/api/v1/business/products/1")
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "database_unavailable"
            assert "127.0.0.1" not in response.text and "password" not in response.text


async def test_real_ownership_guard_and_reseed_refusal_preserve_data():
    app = create_app(configuration())
    async with app.router.lifespan_context(app):
        resources = app.state.resources.business
        async with resources.sessions() as session, session.begin():
            database = ObservedDatabase(
                session, RequestObservation("concurrency_lab_business_test")
            )
            with pytest.raises(BusinessFailure) as failure:
                await database.verify_ownership("concurrency_lab_business")
            assert failure.value.code == FailureCode.OWNERSHIP
        with pytest.raises(ValueError, match="size differs"):
            await seed_business_database("concurrency_lab_business_test", count=1)
        async with resources.engine.connect() as connection:
            assert await connection.scalar(text("SELECT COUNT(*) FROM lab_order")) == 10000
            assert await connection.scalar(text("SELECT status FROM experiment_dataset")) == "ready"
