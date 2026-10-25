"""Synthetic fixtures validate evidence contracts, never published as measurements."""

import copy
import hashlib
import json

import pytest
from pydantic import ValidationError

from concurrency_lab.schemas.scale_experiments import ScaleRun
from concurrency_lab.services.scale_results import load_run


def fixture_record():
    source = {"revision": "a" * 40, "sha256": "b" * 64, "sources_dirty": False, "files": 1}
    identity = {"count": 1, "digest": "c" * 64, "monthly_counts": {"2025-01": 1}, "id_unique": True}
    dataset = {
        "seed": 20261025,
        "order_count": 1,
        "generator_version": 1,
        "digest": "c" * 64,
        "tables": {name: identity for name in ("scale_order", "scale_order_partitioned")},
    }
    query = {
        "sql": "SELECT id FROM fixture_only",
        "parameters": {},
        "warmups": 1,
        "repeats": 3,
        "client_ms_samples": [1.0, 2.0, 3.0],
        "p50_ms": 2.0,
        "p95_ms": 2.9,
        "p99_ms": 2.98,
        "serial_selects_per_second": 500.0,
        "attempts": 3,
        "failures": 0,
        "error_rate": 0.0,
        "result_count": 0,
        "result_rows": [],
        "result_sha256": hashlib.sha256(b"[]").hexdigest(),
        "tree": "-> Table scan on fixture (actual time=0.1..0.2 rows=0 loops=1)",
        "json_plan": {"query_block": {"table": {"using_index": False}}},
        "iterators": [
            {
                "operator": "-> Table scan on fixture",
                "first_row_ms": 0.1,
                "iterator_ms_per_loop": 0.2,
                "actual_rows_per_loop": 0.0,
                "loops": 1.0,
                "access_rows": 0.0,
            }
        ],
        "access_operator_rows": 0.0,
        "selected_partitions": None,
        "covering_observed": False,
    }
    cases = (
        "primary_key",
        "by_user",
        "user_projection",
        "offset",
        "keyset",
        "time_range",
        "id_without_time",
    )
    table = {
        "cursor_lookup_ms": 1.0,
        "cursor": {"created_at": "2025-01-01 00:00:00", "id": 1},
        "offset": 0,
        "page_ids": {"offset": [], "keyset": []},
        "queries": {case: copy.deepcopy(query) for case in cases},
    }
    phases = [
        {
            "phase": phase,
            "revision": revision,
            "started_at": "2026-10-25T00:00:01+00:00",
            "finished_at": "2026-10-25T00:00:02+00:00",
            "source": source,
            "dataset": dataset,
            "repeats": 3,
            "tables": {
                name: copy.deepcopy(table) for name in ("scale_order", "scale_order_partitioned")
            },
            "statistics": {},
            "mysql_before": {},
            "mysql_after": {},
            "environment": {},
        }
        for phase, revision in zip(
            ("baseline", "composite", "covering"), ("scale001", "scale002", "scale003"), strict=True
        )
    ]
    for index, item in enumerate(phases):
        item["started_at"] = f"2026-10-25T00:00:0{1 + index * 2}+00:00"
        item["finished_at"] = f"2026-10-25T00:00:0{2 + index * 2}+00:00"
    probe = {
        "table": "fixture_probe",
        "identity": identity,
        "batches": [{"rows": 1, "execute_commit_ms": 2.0}],
        "total_execute_commit_ms": 2.0,
        "rows_per_sql_second": 500.0,
        "p50_batch_ms": 2.0,
        "p95_batch_ms": 2.0,
        "p99_batch_ms": 2.0,
        "failures": 0,
    }
    return {
        "schema_version": 1,
        "evidence": "recorded",
        "complete": True,
        "manifest": {
            "id": "scale-20261025T000000-1234abcd",
            "database": "concurrency_lab_exp_009_test",
            "source": source,
            "started_at": "2026-10-25T00:00:00+00:00",
            "finished_at": "2026-10-25T00:00:10+00:00",
            "duration_seconds": 10.0,
            "order_count": 1,
            "seed": 20261025,
            "batch_size": 1,
            "repeats": 3,
        },
        "generation": {},
        "migrations": [],
        "phases": phases,
        "writes": {
            "started_at": "2026-10-25T00:00:07+00:00",
            "finished_at": "2026-10-25T00:00:08+00:00",
            "wall_seconds": 1.0,
            "rows_per_probe": 1,
            "batch_size": 1,
            "layout_order_per_batch": [["single", "composite", "covering"]],
            "probes": {name: copy.deepcopy(probe) for name in ("single", "composite", "covering")},
            "statistics": {},
            "semantics": "Synthetic fixture only",
        },
        "resources": [],
        "definitions": {"fixture": "Synthetic schema test, never measured evidence"},
        "limitations": ["Synthetic test fixture only"],
    }


def test_rejects_tampered_samples_plan_identity_and_page():
    ScaleRun.model_validate(fixture_record())
    for mutate in (
        lambda r: r["phases"][0]["tables"]["scale_order"]["queries"]["by_user"].update(p95_ms=999),
        lambda r: r["phases"][0]["tables"]["scale_order"]["queries"]["by_user"].update(
            covering_observed=True
        ),
        lambda r: r["phases"][1]["dataset"].update(digest="d" * 64),
        lambda r: r["phases"][0]["tables"]["scale_order"]["page_ids"].update(keyset=[99]),
    ):
        record = copy.deepcopy(fixture_record())
        mutate(record)
        with pytest.raises(ValidationError):
            ScaleRun.model_validate(record)


def test_record_path_identity_size_and_corruption_guards(tmp_path):
    record = fixture_record()
    identifier = record["manifest"]["id"]
    folder = tmp_path / identifier
    folder.mkdir()
    path = folder / "result.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    assert load_run(identifier, tmp_path).manifest.id == identifier
    for invalid in ("../result", "scale-invalid", "../../.env"):
        with pytest.raises(ValueError):
            load_run(invalid, tmp_path)
    record["manifest"]["id"] = "scale-20261025T000000-abcdef12"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError):
        load_run(identifier, tmp_path)
    path.write_text(" " * 8_000_001, encoding="utf-8")
    with pytest.raises(ValueError):
        load_run(identifier, tmp_path)


def test_manifest_utc_and_monotonic_boundary_must_agree():
    record = fixture_record()
    record["manifest"]["duration_seconds"] = 1.0
    with pytest.raises(ValidationError):
        ScaleRun.model_validate(record)


def test_readonly_api_unknown_corrupt_and_no_execution_endpoint(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from concurrency_lab.core.config import Settings
    from concurrency_lab.main import create_app
    from concurrency_lab.services import scale_results

    monkeypatch.setattr(scale_results, "RESULT_ROOT", tmp_path)
    config = Settings(_env_file=None, mysql_password="fixture", redis_password="fixture")
    with TestClient(create_app(config)) as api:
        assert api.get("/api/v1/scale-experiments").json() == []
        record = fixture_record()
        identifier = record["manifest"]["id"]
        folder = tmp_path / identifier
        folder.mkdir()
        path = folder / "result.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        assert api.get("/api/v1/scale-experiments").status_code == 200
        assert api.get(f"/api/v1/scale-experiments/{identifier}").status_code == 200
        assert api.post("/api/v1/scale-experiments", json={"sql": "SELECT 1"}).status_code == 405
        assert (
            api.get("/api/v1/scale-experiments/scale-20261025T000000-abcdef12").status_code == 404
        )
        path.write_text("{broken", encoding="utf-8")
        assert api.get(f"/api/v1/scale-experiments/{identifier}").status_code == 503
        assert api.get("/api/v1/scale-experiments").status_code == 503


def test_record_symlink_cannot_escape_trusted_root(tmp_path):
    import os

    identifier = fixture_record()["manifest"]["id"]
    folder = tmp_path / identifier
    folder.mkdir()
    external = tmp_path / "external.json"
    external.write_text(json.dumps(fixture_record()), encoding="utf-8")
    try:
        os.symlink(external, folder / "result.json")
    except OSError:
        pytest.skip("OS does not permit creating a symlink in this test environment")
    with pytest.raises(ValueError):
        load_run(identifier, tmp_path)
