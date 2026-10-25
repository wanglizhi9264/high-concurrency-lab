import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from concurrency_lab.core.config import Settings
from concurrency_lab.db.business import validate_business_database
from concurrency_lab.main import create_app
from concurrency_lab.observability.recording import RequestObservation
from concurrency_lab.schemas.business import PageParameters


def test_business_database_isolation():
    for name in ("mysql", "concurrency_lab", "concurrency_lab_exp_002_1000000", "x;DROP"):
        with pytest.raises(ValueError):
            validate_business_database(name)
    assert validate_business_database("concurrency_lab_business") == "concurrency_lab_business"
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            mysql_password="secret",
            redis_password="secret",
            business_database="mysql",
        )


def test_reference_rows_preserve_existing_catalog():
    from concurrency_lab.experiments.dataset import reference_rows

    users, products = reference_rows()
    assert len(users) == 1000 and len(products) == 100
    assert users[499]["email"] == "user0500@example.invalid"
    assert products[0]["sku"] == "SKU0001"
    assert str(products[0]["price"]) == "1.17"


def test_paired_cursor_and_limits():
    for parameters in (
        {"limit": 101},
        {"offset": -1},
        {"before_id": 2},
        {"before_time": "2025-01-01T00:00:00"},
    ):
        with pytest.raises(ValidationError):
            PageParameters(**parameters)
    page = PageParameters(before_id=2, before_time="2025-01-01T00:00:00Z")
    assert page.before_time.tzinfo is None
    with pytest.raises(ValidationError):
        PageParameters(offset=3, before_id=2, before_time="2025-01-01T00:00:00")


def test_nested_measured_spans_and_error_redaction():
    observation = RequestObservation("concurrency_lab_business")
    with observation.span("service", "service", "src/concurrency_lab/services/business_service.py"):
        with observation.span("SQL", "sql_execute_fetch", "src/concurrency_lab/db/business.py"):
            pass
    assert len(observation.spans) == 2
    assert observation.spans[1].parent_id == observation.spans[0].id
    assert all(span.duration_ms >= 0 for span in observation.spans)
    with pytest.raises(RuntimeError), observation.span("failure", "sql_execute_fetch", "safe.py"):
        raise RuntimeError("private-secret")
    assert observation.spans[-1].state == "error"
    assert "private-secret" not in observation.snapshot().model_dump_json()


def test_disabled_business_mode_preserves_health_and_correlation(monkeypatch):
    monkeypatch.setenv("BUSINESS_ENABLED", "true")
    config = Settings(
        _env_file=None, mysql_password="test", redis_password="test", business_enabled=False
    )
    assert config.business_enabled is False
    with TestClient(create_app(config)) as api:
        response = api.get("/api/v1/business/products/1")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "business_disabled"
        assert response.headers["x-request-id"] == response.json()["trace"]["request_id"]
        assert float(response.headers["x-process-time-ms"]) >= 0
        assert api.get("/health/live").status_code == 200
        invalid = api.get("/api/v1/business/products/0")
        assert invalid.status_code == 422
        assert invalid.headers["x-request-id"]
        assert invalid.json()["error"]["code"] == "invalid_input"
        assert invalid.json()["trace"]["request_id"] == invalid.headers["x-request-id"]
        assert all(span["sql"] is None for span in invalid.json()["trace"]["spans"])
