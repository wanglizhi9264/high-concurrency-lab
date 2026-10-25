"""Opt-in actual009schema/data/plan/partition/write protocol, no reset."""

import asyncio
import os
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import insert, text
from sqlalchemy.exc import OperationalError

from concurrency_lab.db.errors import mysql_error_code
from concurrency_lab.experiments.scale import dataset as generation
from concurrency_lab.experiments.scale.cli import advance, initialize_database, run_pipeline
from concurrency_lab.experiments.scale.dataset import dataset_identity, seed_database
from concurrency_lab.experiments.scale.measurement import measure_phase, measure_query
from concurrency_lab.experiments.scale.safety import assert_owned, engine_for
from concurrency_lab.models.scale import QUERY_TABLES, tables

pytestmark = pytest.mark.skipif(
    os.getenv("SCALE_INTEGRATION") != "1", reason="Explicit owned009test database required"
)
DATABASE = "concurrency_lab_exp_009_test"


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    output = tmp_path_factory.mktemp("scale-record") / (
        "scale-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8]
    )

    async def prepare():
        await initialize_database(DATABASE)
        engine = engine_for(DATABASE)
        try:
            async with engine.connect() as connection:
                revision = await assert_owned(connection, DATABASE)
                if revision != "scale001":
                    return None  # Keep retained advanced dataset, never reset just for a rerun.
                count = await connection.scalar(text("SELECT COUNT(*) FROM scale_dataset"))
                if count:
                    raise ValueError("Partial prior009test retained; inspect before running")
        finally:
            await engine.dispose()
        return await run_pipeline(DATABASE, 1000, 20261025, 127, 3, output, probe_rows=1000)

    return asyncio.run(prepare())


async def test_actual_phase_protocol_coverage_pruning_equivalence_and_writes(prepared):
    if prepared is None:
        pytest.skip("Existing completed009test pipeline retained; no remeasurement/reset")
    assert prepared["complete"]
    phases = prepared["phases"]
    assert [p["phase"] for p in phases] == ["baseline", "composite", "covering"]
    assert len({p["dataset"]["digest"] for p in phases}) == 1
    for phase in phases:
        ordinary, partitioned = (
            phase["tables"]["scale_order"],
            phase["tables"]["scale_order_partitioned"],
        )
        assert ordinary["page_ids"]["offset"] == ordinary["page_ids"]["keyset"]
        assert partitioned["page_ids"] == ordinary["page_ids"]
        for case in ordinary["queries"]:
            assert (
                ordinary["queries"][case]["result_sha256"]
                == partitioned["queries"][case]["result_sha256"]
            )
        assert partitioned["queries"]["time_range"]["selected_partitions"] == ["p3"]
        assert len(partitioned["queries"]["id_without_time"]["selected_partitions"]) == 5
    assert phases[-1]["tables"]["scale_order"]["queries"]["user_projection"]["covering_observed"]
    assert all(
        probe["identity"]["count"] == 1000 for probe in prepared["writes"]["probes"].values()
    )
    assert (
        len({probe["identity"]["digest"] for probe in prepared["writes"]["probes"].values()}) == 1
    )


async def test_retained_dataset_refuses_reseed_and_actual_twin_identity(prepared):
    with pytest.raises(ValueError):
        await seed_database(DATABASE, 1000, 20261025, 100)
    engine = engine_for(DATABASE)
    try:
        async with engine.connect() as connection:
            identity = await dataset_identity(connection)
            assert (
                identity["tables"]["scale_order"] == identity["tables"]["scale_order_partitioned"]
            )
            assert identity["order_count"] == 1000
            assert (
                await connection.scalar(
                    text("SELECT COUNT(*)=COUNT(DISTINCT id) FROM scale_order_partitioned")
                )
                == 1
            )
    finally:
        await engine.dispose()


async def test_partial_batch_failure_is_retained_and_cannot_be_reseeded():
    database = "concurrency_lab_exp_009_test_partial"
    await initialize_database(database)
    engine = engine_for(database)
    try:
        async with engine.connect() as connection:
            existing = await connection.scalar(text("SELECT COUNT(*) FROM scale_dataset"))
        if not existing:
            original = generation.row_batches

            def interrupted(count, seed, batch_size):
                for number, batch in enumerate(original(count, seed, batch_size)):
                    if number == 1:
                        raise RuntimeError("Controlled failure after first committed twin batch")
                    yield batch

            with patch.object(generation, "row_batches", interrupted):
                with pytest.raises(RuntimeError):
                    await seed_database(database, 1000, 20261025, 127)
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT status FROM scale_dataset")) == "loading"
            assert await connection.scalar(text("SELECT COUNT(*) FROM scale_order")) == 127
            assert (
                await connection.scalar(text("SELECT COUNT(*) FROM scale_order_partitioned")) == 127
            )
            with pytest.raises(ValueError):
                await dataset_identity(connection)
        with pytest.raises(ValueError):
            await seed_database(database, 1000, 20261025, 127)
    finally:
        await engine.dispose()


async def test_source_dataset_and_missing_proof_block_ddl_advance(tmp_path):
    import json

    database = "concurrency_lab_exp_009_test_gate"
    await initialize_database(database)
    engine = engine_for(database)
    try:
        async with engine.connect() as connection:
            existing = await connection.scalar(text("SELECT COUNT(*) FROM scale_dataset"))
        if not existing:
            await seed_database(database, 500, 20261025, 127)
        with pytest.raises(FileNotFoundError):
            await advance(database, "scale002", tmp_path)
        baseline = await measure_phase(database, "baseline", 3, tmp_path, None)
        for field in ("source", "dataset"):
            modified = json.loads(json.dumps(baseline, default=str))
            modified[field]["sha256" if field == "source" else "digest"] = "0" * 64
            (tmp_path / "baseline.json").write_text(json.dumps(modified), encoding="utf-8")
            with pytest.raises(ValueError):
                await advance(database, "scale002", tmp_path)
            async with engine.connect() as connection:
                assert await assert_owned(connection, database) == "scale001"
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                await connection.execute(
                    text("UPDATE scale_ownership SET purpose='wrong-owner' WHERE id=1")
                )
                with pytest.raises(ValueError):
                    await assert_owned(connection, database)
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


async def test_real_analytical_check_constraints_rollback_invalid_money(prepared):
    engine = engine_for(DATABASE)
    try:
        for name in QUERY_TABLES:
            async with engine.connect() as connection:
                transaction = await connection.begin()
                try:
                    with pytest.raises(OperationalError) as failure:
                        await connection.execute(
                            insert(tables[name]).values(
                                id=1000000001,
                                created_at=datetime(2025, 1, 1),
                                user_id=1,
                                total=-1,
                                status="paid",
                                payload="invalid-negative-money",
                            )
                        )
                    assert mysql_error_code(failure.value) == 3819
                finally:
                    await (
                        transaction.rollback()
                    )  # Never commit the invalid row even if a constraint regresses.
                assert await connection.scalar(text(f"SELECT COUNT(*) FROM {name}")) == 1000
    finally:
        await engine.dispose()


async def test_actual_query_error_retains_stage_and_unknown_completion(prepared):
    engine = engine_for(DATABASE)
    partial = {}
    try:
        async with engine.connect() as connection:
            await assert_owned(connection, DATABASE)
            with pytest.raises(OperationalError) as failure:
                await measure_query(
                    connection, "SELECT controlled_missing_column FROM scale_order", {}, 3, partial
                )
            assert mysql_error_code(failure.value) == 1054
        assert partial["failed_stage"] == "warmup"
        assert partial["error_type"] == "OperationalError"
        assert partial["warmup_completed"] is False
        assert partial["completed_client_ms_samples"] == []
        assert partial["failed_stage_client_ms"] > 0
    finally:
        await engine.dispose()
