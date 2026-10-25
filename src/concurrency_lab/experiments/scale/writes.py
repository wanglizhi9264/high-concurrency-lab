"""Committed fresh-table bulk probes, separate from immutable query fixtures."""

import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import insert, select, text

from concurrency_lab.experiments.queries import percentile
from concurrency_lab.experiments.scale.dataset import row_batches, table_identity
from concurrency_lab.experiments.scale.measurement import schema_statistics
from concurrency_lab.experiments.scale.safety import assert_owned, engine_for, validate_batch_budget
from concurrency_lab.models.scale import PROBE_TABLES, tables


async def measure_writes(database: str, count: int, seed: int, batch_size: int) -> dict[str, Any]:
    if not 1 <= count <= 50000:
        raise ValueError("Write probe bounded to1..50000fresh rows")
    validate_batch_budget(count, batch_size)
    engine = engine_for(database)
    started, clock = datetime.now(UTC).isoformat(), time.perf_counter()
    samples: dict[str, list[dict[str, Any]]] = {layout: [] for layout in PROBE_TABLES}
    ordering = []
    try:
        async with engine.connect() as connection:
            if await assert_owned(connection, database) != "scale003":
                raise ValueError("Write comparison requires final predefined layouts")
            for name in PROBE_TABLES.values():
                if await connection.scalar(select(tables[name].c.id).limit(1)) is not None:
                    raise ValueError("Write probe not empty; refuse overwrite or repeat")
        layouts = list(PROBE_TABLES)
        for number, batch in enumerate(row_batches(count, seed, batch_size)):
            order = layouts[number % 3 :] + layouts[: number % 3]
            ordering.append(order)
            for layout in order:
                before = time.perf_counter()
                async with engine.begin() as connection:
                    await connection.execute(insert(tables[PROBE_TABLES[layout]]), batch)
                samples[layout].append(
                    {"rows": len(batch), "execute_commit_ms": (time.perf_counter() - before) * 1000}
                )
        probes = {}
        async with engine.connect() as connection:
            for layout, name in PROBE_TABLES.items():
                identity = await table_identity(connection, name)
                if identity["count"] != count:
                    raise ValueError("Committed probe count differs from requested count")
                timings = [sample["execute_commit_ms"] for sample in samples[layout]]
                await connection.execute(text(f"ANALYZE TABLE {name}"))
                probes[layout] = {
                    "table": name,
                    "identity": identity,
                    "batches": samples[layout],
                    "total_execute_commit_ms": sum(timings),
                    "rows_per_sql_second": count * 1000 / sum(timings),
                    "p50_batch_ms": percentile(timings, 0.5),
                    "p95_batch_ms": percentile(timings, 0.95),
                    "p99_batch_ms": percentile(timings, 0.99),
                    "failures": 0,
                }
            if len({probe["identity"]["digest"] for probe in probes.values()}) != 1:
                raise ValueError("Write probes received different actual data")
            statistics = await schema_statistics(connection)
        return {
            "started_at": started,
            "finished_at": datetime.now(UTC).isoformat(),
            "wall_seconds": time.perf_counter() - clock,
            "rows_per_probe": count,
            "batch_size": batch_size,
            "layout_order_per_batch": ordering,
            "probes": probes,
            "statistics": statistics,
            "semantics": "Initially empty tables, same prepared rows, rotating layout order. "
            "Batch execute+COMMIT only, generation/hash/readback excluded. Not "
            "million-existing-row write amplification; shared cache/order remain "
            "confounders.",
        }
    finally:
        await engine.dispose()
