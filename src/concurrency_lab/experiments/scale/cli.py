"""Guarded phase protocol; all009schema changes use its independent Alembic context."""

import argparse
import asyncio
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import event, text
from sqlalchemy.exc import SQLAlchemyError

from concurrency_lab.experiments.runner import save_result
from concurrency_lab.experiments.scale.dataset import dataset_identity, seed_database
from concurrency_lab.experiments.scale.identity import ROOT, source_identity
from concurrency_lab.experiments.scale.measurement import PHASES, measure_phase
from concurrency_lab.experiments.scale.safety import (
    DATABASES,
    REVISIONS,
    assert_owned,
    can_initialize,
    engine_for,
    experiment_lock,
    validate_batch_budget,
    validate_target,
)
from concurrency_lab.experiments.scale.writes import measure_writes


async def _migrate(database: str, revision: str) -> dict[str, Any]:
    validate_target(database)
    if revision not in REVISIONS:
        raise ValueError("Unsupported009revision")
    engine, ddl = engine_for(database), []
    started = time.perf_counter()

    def before(
        connection: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        if (
            statement.lstrip()
            .upper()
            .startswith(("CREATE TABLE", "CREATE INDEX", "DROP INDEX", "ALTER TABLE"))
        ):
            context.scale_started = time.perf_counter()

    def after(
        connection: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        if hasattr(context, "scale_started"):
            ddl.append(
                {
                    "sql": statement,
                    "client_execute_ms": (time.perf_counter() - context.scale_started) * 1000,
                }
            )

    event.listen(engine.sync_engine, "before_cursor_execute", before)
    event.listen(engine.sync_engine, "after_cursor_execute", after)
    try:
        async with engine.begin() as connection:
            if await connection.scalar(text("SELECT DATABASE()")) != database:
                raise ValueError("Migration target mismatch")
            await connection.execute(text("SET SESSION lock_wait_timeout=5"))

            def apply(sync_connection: Any) -> None:
                configuration = Config()
                configuration.set_main_option("script_location", str(ROOT / "migrations/scale"))
                configuration.attributes["connection"] = sync_connection
                command.upgrade(configuration, revision)

            await connection.run_sync(apply)
        return {
            "revision": revision,
            "guarded_alembic_wall_ms": (time.perf_counter() - started) * 1000,
            "ddl": ddl,
            "semantics": "DDL DBAPI execute wall includes server index build/implicit DDL "
            "commit and network; not pure server time",
        }
    finally:
        await engine.dispose()


async def initialize_database(database: str) -> dict[str, Any] | None:
    if not await can_initialize(database):
        return None  # Existing owned schema retained, never reset/downgrade.
    return await _migrate(database, "scale001")


async def advance(database: str, target: str, directory: Path) -> dict[str, Any]:
    if target not in REVISIONS[1:]:
        raise ValueError("Only next009index revision supported")
    position = REVISIONS.index(target)
    previous = json.loads((directory / f"{PHASES[position - 1]}.json").read_text(encoding="utf-8"))
    engine = engine_for(database)
    try:
        async with engine.connect() as connection:
            if await assert_owned(connection, database) != REVISIONS[position - 1]:
                raise ValueError("Index advance requires exact preceding revision")
            if previous["phase"] != PHASES[position - 1] or previous[
                "dataset"
            ] != await dataset_identity(connection):
                raise ValueError("Saved preceding phase does not match actual dataset")
            if previous["source"] != source_identity():
                raise ValueError("Sources changed since preceding phase; refusing DDL")
    finally:
        await engine.dispose()
    return await _migrate(database, target)


async def run_pipeline(
    database: str,
    count: int,
    seed: int,
    batch_size: int,
    repeats: int,
    directory: Path,
    probe_rows: int = 50000,
    allow_ten_million: bool = False,
) -> dict[str, Any]:
    validate_target(database, count, allow_ten_million)
    validate_batch_budget(count, batch_size)
    validate_batch_budget(probe_rows, batch_size)
    if not re.fullmatch(r"scale-[0-9]{8}T[0-9]{6}-[0-9a-f]{8}", directory.name):
        raise ValueError("Exclusive009run ID required")
    if not 3 <= repeats <= 30:
        raise ValueError("Repeats must be3..30")
    await asyncio.to_thread(directory.mkdir, parents=True, exist_ok=True)
    if any(
        (directory / f"{name}.json").exists()
        for name in ("seed", *PHASES, "writes", "database-result", "result")
    ):
        raise FileExistsError("Run evidence already exists; no overwrite/resume")
    source = source_identity()
    started, clock = datetime.now(UTC).isoformat(), time.perf_counter()
    try:
        async with experiment_lock(database):
            initialization = await initialize_database(database)
            generation = await seed_database(database, count, seed, batch_size, allow_ten_million)
            save_result(directory / "seed.json", generation)
            phases: list[dict[str, Any]] = []
            migrations = [initialization] if initialization else []
            for position, phase in enumerate(PHASES):
                if position:
                    migrations.append(await advance(database, REVISIONS[position], directory))
                phases.append(
                    await measure_phase(
                        database, phase, repeats, directory, phases[0] if phases else None
                    )
                )
            writes = await measure_writes(database, probe_rows, seed, batch_size)
            save_result(directory / "writes.json", writes)
            engine = engine_for(database)
            try:
                async with engine.connect() as connection:
                    if await dataset_identity(connection) != phases[0]["dataset"]:
                        raise ValueError("Write probes changed immutable query data")
            finally:
                await engine.dispose()
            if source_identity() != source:
                raise ValueError("Source changed during009run")
            result = {
                "schema_version": 1,
                "evidence": "recorded",
                "complete": True,
                "manifest": {
                    "id": directory.name,
                    "database": database,
                    "source": source,
                    "started_at": started,
                    "finished_at": datetime.now(UTC).isoformat(),
                    "duration_seconds": time.perf_counter() - clock,
                    "order_count": count,
                    "seed": seed,
                    "batch_size": batch_size,
                    "repeats": repeats,
                },
                "generation": generation,
                "migrations": migrations,
                "phases": phases,
                "writes": writes,
                "resources": [],
                "definitions": {
                    "client_ms": (
                        "SELECT execute/fetch wall, one client, warmup1; "
                        "not server-only or concurrent HTTP RPS"
                    ),
                    "access_operator_rows": (
                        "sum(actual access iterator output rows*loops), "
                        "not physical I/O; nested iterator times not summed"
                    ),
                    "coverage": "Actual EXPLAIN JSON using_index, not using_index_condition",
                    "partitions": "Optimizer-selected partitions from EXPLAIN JSON; null means "
                    "unpartitioned/not reported, not empty",
                    "space": "InnoDB allocation/page/cardinality estimates, not file bytes",
                    "write": writes["semantics"],
                },
                "limitations": [
                    "Small warm repeated samples; P95/P99 interpolation not production "
                    "tail estimates",
                    "Fixed sequential baseline/composite/covering phases have cache/order "
                    "confounding",
                    "Analytical snapshot: matching compositePK(id,created_at), no business "
                    "foreign keys or DB id-only unique constraint",
                    "Partitioning affects only matching predicates; no universal speedup "
                    "or automatic sharding conclusion",
                    "Failed runs retained incomplete and excluded from complete catalogue; "
                    "zero query failures applies only to these completed samples",
                ],
            }
            save_result(directory / "database-result.json", result)
            return result
    except (ValueError, OSError, SQLAlchemyError) as failure:
        if not (directory / "incomplete.json").exists():
            save_result(
                directory / "incomplete.json",
                {
                    "complete": False,
                    "error_type": type(failure).__name__,
                    "observed_at": datetime.now(UTC).isoformat(),
                },
            )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", choices=sorted(DATABASES), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--orders", type=int, required=True)
    parser.add_argument("--seed", type=int, default=20261025)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--probe-rows", type=int, default=50000)
    parser.add_argument("--allow-ten-million", action="store_true")
    arguments = parser.parse_args()
    try:
        result = asyncio.run(
            run_pipeline(
                arguments.database,
                arguments.orders,
                arguments.seed,
                arguments.batch_size,
                arguments.repeats,
                arguments.output_dir,
                arguments.probe_rows,
                arguments.allow_ten_million,
            )
        )
        print(json.dumps({"id": result["manifest"]["id"], "complete": True}), flush=True)
    except (ValueError, OSError):
        parser.exit(2, "009guard refused operation; retained state/evidence, no reset.\n")
    except SQLAlchemyError:
        parser.exit(1, "009database operation failed; details redacted, preserve partial state.\n")
