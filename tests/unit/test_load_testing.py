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
