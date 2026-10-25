import csv
from pathlib import Path

import pytest

from concurrency_lab.experiments.load_recording import aggregate_requests, validate_load_parameters
from concurrency_lab.services.benchmarks import load_benchmark, validate_run_id


def test_load_bounds_and_run_id_safety():
    for parameters in ((501, 15, 1, 5), (10, 301, 1, 5), (10, 15, 0, 5), (10, 15, 1, 0)):
        with pytest.raises(ValueError):
            validate_load_parameters(*parameters)
    with pytest.raises(ValueError):
        validate_run_id("../../.env")
    assert validate_run_id("load-20261025T000000-1234abcd")


def test_actual_request_aggregation_and_unknown_sql(tmp_path: Path):
    path = tmp_path / "requests.csv"
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "completed_epoch",
                "response_ms",
                "status",
                "failed",
                "sql_attempts",
                "error_code",
                "error_type",
                "request_id",
                "name",
            ],
        )
        writer.writeheader()
        for row in [
            [101, 10, 200, 0, 2, "", "", "a", "hot"],
            [102, 20, 503, 1, 1, "pool_timeout", "", "b", "hot"],
            [103, 30, 0, 1, "", "", "ReadTimeout", "", "hot"],
        ]:
            writer.writerow(dict(zip(writer.fieldnames, row, strict=True)))
    summary, history = aggregate_requests(path, 100, 104, 4)
    assert summary.requests == 3 and summary.failures == 2
    assert summary.completed_rps == 0.75 and summary.p50_ms == 20
    assert summary.observed_sql_attempts_per_s == 0.75
    assert summary.unknown_sql_responses == 1 and summary.pool_timeouts == 1
    assert summary.transport_timeouts == 1
    assert sum(point.completed for point in history) == 3


def test_invalid_record_is_not_published(tmp_path: Path):
    with pytest.raises(ValueError):
        load_benchmark("load-20261025T000000-1234abcd", tmp_path)


def test_record_api_schema_identity_and_safe_errors(tmp_path: Path):
    import json
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    from concurrency_lab.core.config import Settings
    from concurrency_lab.main import create_app
    from concurrency_lab.services import benchmarks

    source = next(benchmarks.LOAD_ROOT.glob("*/result.json"))
    record = json.loads(source.read_text(encoding="utf-8"))
    identifier = record["manifest"]["id"]
    folder = tmp_path / identifier
    folder.mkdir()
    target = folder / "result.json"
    target.write_text(json.dumps(record), encoding="utf-8")
    with (
        patch.object(benchmarks, "LOAD_ROOT", tmp_path),
        TestClient(
            create_app(
                Settings(
                    _env_file=None,
                    mysql_password="test",
                    redis_password="test",
                    business_enabled=False,
                )
            )
        ) as api,
    ):
        assert api.get("/api/v1/benchmarks").json()[0]["manifest"]["id"] == identifier
        from concurrency_lab.schemas.benchmarks import LoadSummary

        assert api.get(f"/api/v1/benchmarks/{identifier}").json()["summary"] == (
            LoadSummary.model_validate(record["summary"]).model_dump()
        )
        assert api.get("/api/v1/benchmarks/unknown").status_code == 404
        record["manifest"]["id"] = "load-20261025T000000-1234abcd"
        target.write_text(json.dumps(record), encoding="utf-8")
        response = api.get(f"/api/v1/benchmarks/{identifier}")
        assert response.status_code == 503
        assert str(tmp_path) not in response.text and "Traceback" not in response.text
        record["summary"]["completed_rps"] = float("nan")
        target.write_text(json.dumps(record), encoding="utf-8")
        with pytest.raises(ValueError):
            load_benchmark(identifier, tmp_path)


def test_client_starts_include_unfinished_calls(tmp_path: Path):
    from concurrency_lab.experiments.load_recording import REQUEST_FIELDS

    requests = tmp_path / "requests.csv"
    with requests.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=REQUEST_FIELDS)
        writer.writeheader()
        writer.writerow(
            dict(
                completed_epoch=102,
                response_ms=100,
                status=200,
                failed=0,
                sql_attempts=2,
                error_code="",
                error_type="",
                request_id="a",
                name="hot",
                started_epoch=101,
                call_id=1,
            )
        )
    starts = tmp_path / "starts.csv"
    starts.write_text("call_id,started_epoch,name\n1,101,hot\n2,103,hot\n", encoding="utf-8")
    summary, history = aggregate_requests(requests, 100, 104, 4, starts)
    assert summary.client_started == 2 and summary.requests == 1
    assert summary.uncompleted_client_calls == 1
    assert sum(point.client_started or 0 for point in history) == 2
    starts.write_text("call_id,started_epoch,name\n2,103,hot\n", encoding="utf-8")
    with pytest.raises(ValueError, match="identity"):
        aggregate_requests(requests, 100, 104, 4, starts)


@pytest.mark.parametrize("window", [(100, 104, 3), (100, 99, 1), (100, float("nan"), 4)])
def test_clock_discontinuities_reject_publication(tmp_path: Path, window):
    with pytest.raises(ValueError):
        aggregate_requests(tmp_path / "absent.csv", *window)


def test_process_cpu_is_unknown_until_all_members_have_a_baseline():
    import importlib.util
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    spec = importlib.util.spec_from_file_location(
        "lab_load_runner", Path(__file__).resolve().parents[2] / "scripts/run_load_test.py"
    )
    assert spec and spec.loader
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)

    root, child = MagicMock(), MagicMock()
    root.pid, child.pid = 101, 102
    root.children.side_effect = [[], [child], [child]]
    root.cpu_percent.return_value = 1
    child.cpu_percent.return_value = 5
    root.memory_info.return_value.rss = 100
    child.memory_info.return_value.rss = 50
    with patch.object(runner.psutil, "Process", return_value=root):
        sampler = runner.ProcessSampler()
        process = SimpleNamespace(pid=101)
        assert sampler.collect(process, "api").cpu_percent is None
        assert sampler.collect(process, "api").cpu_percent is None
        last = sampler.collect(process, "api")
        assert last.cpu_percent == 6 and last.memory_bytes == 150
