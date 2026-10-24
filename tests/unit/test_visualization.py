from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from concurrency_lab.core.config import Settings
from concurrency_lab.main import create_app
from concurrency_lab.services.visualization import DataUnavailable, load_result, parse_plan_tree


def client(**overrides):
    return TestClient(
        create_app(
            Settings(_env_file=None, mysql_password="test", redis_password="test", **overrides)
        )
    )


def test_probe_guide_projects_current_target_and_budgets_without_credentials():
    with client(mysql_database="custom_lab", readiness_timeout=0.5, io_timeout=0.25) as api:
        response = api.get("/api/v1/observability/probe-guide")
        assert response.status_code == 200
        assert response.json() == {
            "mysql_database": "custom_lab",
            "redis_database": 0,
            "readiness_timeout_seconds": 0.5,
            "io_timeout_seconds": 0.25,
            "pool_timeout_seconds": 1.0,
        }
        assert all(word not in response.text for word in ("password", "127.0.0.1", "mysql+asyncmy"))


@pytest.mark.parametrize("failed", ["mysql", "redis"])
def test_single_dependency_failure_matches_ready_and_trace_without_exception_details(failed):
    with (
        patch(
            "concurrency_lab.services.health.mysql_ping", AsyncMock(return_value=failed != "mysql")
        ),
        patch(
            "concurrency_lab.services.health.redis_ping", AsyncMock(return_value=failed != "redis")
        ),
        client() as api,
    ):
        for path in ("/health/ready", "/api/v1/observability/health-trace"):
            response = api.get(path)
            assert response.status_code == 503
            assert response.json()["checks"] == {
                "mysql": "unavailable" if failed == "mysql" else "ok",
                "redis": "unavailable" if failed == "redis" else "ok",
            }
        assert api.get("/health/live").json() == {"status": "alive"}


def test_architecture_and_experiment_exact_source():
    with client() as api:
        data = api.get("/api/v1/architecture").json()
        assert any(
            node["id"] == "session" and node["status"] == "teaching" for node in data["nodes"]
        )
        assert api.get("/api/v1/experiments").status_code == 200
        result = api.get("/api/v1/experiments/002-mysql-index-baseline/results?scale=1000000")
        assert result.status_code == 200
        assert result.json()["baseline"]["queries"]["offset"]["p50_ms"] == 414.6824999770615
        assert api.get("/api/v1/experiments/invalid/results").status_code == 404
        assert (
            api.get("/api/v1/experiments/002-mysql-index-baseline/results?scale=12").status_code
            == 422
        )


def test_plan_tree_and_schema_guard():
    result = load_result(1000000, "baseline")
    nodes = parse_plan_tree(result.queries["offset"])
    assert nodes[0].children[0].children[0].metrics.actual_rows_per_loop == 1000000
    with patch("pathlib.Path.read_bytes", return_value=b'{"schema_version":99}'):
        with pytest.raises(DataUnavailable):
            load_result(10000, "baseline")


def test_safe_data_error():
    with (
        client() as api,
        patch("concurrency_lab.services.visualization.load_result", side_effect=DataUnavailable()),
    ):
        response = api.get("/api/v1/experiments/002-mysql-index-baseline/results")
        assert response.status_code == 503
        assert "Traceback" not in response.text and "C:" not in response.text


@pytest.mark.parametrize("ok,code", [(True, 200), (False, 503)])
def test_real_trace_records_events_without_secrets(ok, code):
    with (
        patch("concurrency_lab.services.health.mysql_ping", AsyncMock(return_value=ok)),
        patch("concurrency_lab.services.health.redis_ping", AsyncMock(return_value=ok)),
        client() as api,
    ):
        response = api.get("/api/v1/observability/health-trace")
        assert response.status_code == code
        data = response.json()
        assert data["mode"] == "live" and data["http_status"] == code
        assert all(e["evidence"] == "measured" for e in data["events"])
        assert all(e["offset_ms"] >= 0 for e in data["events"])
        assert "password" not in response.text.lower() and "127.0.0.1" not in response.text
        assert api.get("/api/v1/observability/pool").json()["waiting"] is None


@pytest.mark.parametrize("scale", [10000, 100000, 1000000])
def test_all_recorded_scales_are_validated(scale):
    from concurrency_lab.services.visualization import result_pair

    pair = result_pair(scale)
    assert pair.baseline.dataset == pair.optimized.dataset
    assert len(pair.baseline.queries) == 6
    assert pair.optimized.sizes.tables


def test_result_symlink_escape_is_rejected():
    from pathlib import Path

    from concurrency_lab.services.visualization import RESULT_ROOT

    root = RESULT_ROOT.absolute()
    with patch.object(Path, "resolve", side_effect=[root, root.parent / "outside.json"]):
        with pytest.raises(DataUnavailable):
            load_result(10000, "baseline")


async def test_trace_timeout_is_recorded_as_failure():
    import asyncio

    from concurrency_lab.services.health import readiness
    from concurrency_lab.services.tracing import TraceRecorder

    async def hang(*args):
        await asyncio.sleep(10)
        return True

    recorder = TraceRecorder()
    with (
        patch("concurrency_lab.services.health.mysql_ping", hang),
        patch("concurrency_lab.services.health.redis_ping", AsyncMock(return_value=True)),
    ):
        result = await readiness(AsyncMock(), AsyncMock(), 0.01, on_event=recorder.probe)
    assert result["mysql"] == "unavailable"
    assert any(e.component == "mysql" and e.state == "failure" for e in recorder.events)


async def test_api_budget_timeout_preserves_other_probe_success():
    import asyncio

    async def hang(*args):
        await asyncio.sleep(1)
        return True

    with (
        patch("concurrency_lab.services.health.mysql_ping", hang),
        patch("concurrency_lab.services.health.redis_ping", AsyncMock(return_value=True)),
        client(readiness_timeout=0.01) as api,
    ):
        response = api.get("/api/v1/observability/health-trace")
        assert response.status_code == 503
        assert response.json()["checks"] == {"mysql": "unavailable", "redis": "ok"}
        assert any(
            e["component"] == "mysql" and e["state"] == "failure" for e in response.json()["events"]
        )


def test_exception_reason_is_not_exposed_in_trace():
    with (
        patch(
            "concurrency_lab.services.health.mysql_ping",
            AsyncMock(side_effect=RuntimeError("private-secret-at-host")),
        ),
        patch("concurrency_lab.services.health.redis_ping", AsyncMock(return_value=True)),
        client() as api,
    ):
        response = api.get("/api/v1/observability/health-trace")
        assert response.status_code == 503
        assert "private-secret" not in response.text
        assert "具体原因" in response.text
