"""Pure invariants and API boundary contracts; database behavior is tested separately."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import DBAPIError

from concurrency_lab.core.config import Settings
from concurrency_lab.domain.inventory import (
    InvalidTransition,
    OrderState,
    audit_checks,
    order_fingerprint,
    transition_changes_state,
)
from concurrency_lab.main import create_app
from concurrency_lab.schemas.inventory import OrderInput, ScenarioInput
from concurrency_lab.services.inventory_service import mysql_error_code


def test_canonical_intent_fingerprint_excludes_server_price():
    identifier = uuid4()
    assert order_fingerprint(identifier, 1, 2) == order_fingerprint(UUID(identifier.hex), 1, 2)
    assert order_fingerprint(identifier, 1, 2) != order_fingerprint(identifier, 1, 3)
    assert order_fingerprint(identifier, 1, 2) != order_fingerprint(identifier, 2, 2)


def test_terminal_transition_is_idempotent_and_cross_terminal_is_invalid():
    assert transition_changes_state(OrderState.RESERVED, OrderState.PAID)
    assert transition_changes_state(OrderState.RESERVED, OrderState.CANCELLED)
    assert not transition_changes_state(OrderState.CANCELLED, OrderState.CANCELLED)
    with pytest.raises(InvalidTransition):
        transition_changes_state(OrderState.PAID, OrderState.CANCELLED)


def test_audit_uses_current_occupancy_not_cancelled_history():
    assert all(audit_checks(10, 5, 3, 2, 3, 2).values())
    assert not all(audit_checks(10, 5, 3, 2, 4, 2).values())
    assert not all(audit_checks(10, -1, 9, 2, 9, 2).values())


def test_input_bounds_and_exact_positive_quantities():
    with pytest.raises(ValidationError):
        OrderInput(scenario_id=uuid4(), user_id=1, quantity=0)
    with pytest.raises(ValidationError):
        ScenarioInput(scenario_id=uuid4(), product_id=1, initial=10001)


@pytest.mark.parametrize("code", [1062, 1205, 1213, 1452, 3819])
def test_driver_error_code_does_not_parse_or_publish_raw_message(code):
    assert mysql_error_code(DBAPIError("statement", {}, Exception(code, "private"))) == code
    assert mysql_error_code(DBAPIError("statement", {}, Exception("private"))) is None


def test_write_gate_before_any_database_access():
    settings = Settings(
        _env_file=None,
        mysql_password="test",
        redis_password="test",
        business_enabled=True,
        business_writes_enabled=False,
    )
    with TestClient(create_app(settings)) as api:
        response = api.post(
            "/api/v1/business/inventory/scenarios",
            json={"scenario_id": str(uuid4()), "product_id": 1, "initial": 5},
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "write_lab_disabled"
        assert not any(s["sql"] for s in response.json()["trace"]["spans"])


def test_inventory_migration_refuses_index_and_foundation_databases():
    import asyncio

    from concurrency_lab.experiments.business_schema import check_upgrade_target

    for database in ("concurrency_lab", "concurrency_lab_exp_002_1000000"):
        with pytest.raises(ValueError, match="allowlisted"):
            asyncio.run(check_upgrade_target(database))


@pytest.mark.parametrize("url", ["https://example.com", "http://127.0.0.1:18002/other"])
def test_inventory_recorder_rejects_unsafe_targets_before_output(tmp_path, url):
    import asyncio
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "inventory_acceptance_runner",
        Path(__file__).resolve().parents[2] / "scripts/verify_inventory_lab.py",
    )
    assert spec and spec.loader
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    with pytest.raises(ValueError, match="loopback"):
        asyncio.run(runner.record_inventory(url, tmp_path))
    assert list(tmp_path.iterdir()) == []
