from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from concurrency_lab.core.config import Settings
from concurrency_lab.domain.tasks import WorkerPolicy, task_fingerprint
from concurrency_lab.main import create_app
from concurrency_lab.schemas.tasks import ControlledFaultPlan, TaskInput


def test_intent_is_stable_and_all_effect_inputs_matter():
    identifier = uuid4()
    intent = TaskInput(task_id=identifier, order_id=1)
    assert task_fingerprint(intent) == task_fingerprint(intent.model_copy())
    for changed in (
        intent.model_copy(update={"order_id": 2}),
        intent.model_copy(update={"max_attempts": 1}),
        intent.model_copy(update={"fault_plan": ControlledFaultPlan(delay_ms=1)}),
    ):
        assert task_fingerprint(intent) != task_fingerprint(changed)
    assert task_fingerprint(intent, uuid4()) != task_fingerprint(intent)


def test_bounded_fault_configuration_and_ownership_budget():
    for value in (0, 6):
        with pytest.raises(ValidationError):
            TaskInput(task_id=uuid4(), order_id=1, max_attempts=value)
    with pytest.raises(ValidationError):
        ControlledFaultPlan(delay_ms=5001)
    with pytest.raises(ValidationError):
        ControlledFaultPlan(fail_first_attempts=6)
    for timeout, lease in ((1, 1), (0, 5), (11, 20), (1, 61)):
        with pytest.raises(ValueError):
            WorkerPolicy(timeout, lease)
    assert WorkerPolicy(0.2, 1).lease_seconds == 1


def test_task_writes_are_opt_in_before_any_sql_or_broker_command():
    settings = Settings(
        _env_file=None,
        mysql_password="fixture",
        redis_password="fixture",
        business_enabled=True,
        business_writes_enabled=False,
    )
    with TestClient(create_app(settings)) as client:
        result = client.post(
            "/api/v1/business/tasks", json={"task_id": str(uuid4()), "order_id": 1}
        )
        assert result.status_code == 503
        body = result.json()
        assert body["error"]["code"] == "write_lab_disabled"
        assert all(span["kind"] == "validation" for span in body["trace"]["spans"])
