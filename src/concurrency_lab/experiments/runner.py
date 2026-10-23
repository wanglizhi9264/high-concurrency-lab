"""Real database measurements. No generated timing values or destructive SQL."""

import json
import platform
import sys
import time
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from concurrency_lab.experiments.dataset import GENERATOR_VERSION
from concurrency_lab.experiments.queries import parse_tree, percentile, query_set
from concurrency_lab.experiments.safety import assert_owned, engine_for, revision, validate_database

DEFAULT_OUTPUT = Path("docs/experiments/002-mysql-index-baseline/runs")


def result_path(directory: Path, database: str, phase: str) -> Path:
    validate_database(database)
    if phase not in ("seed", "baseline", "optimized"):
        raise ValueError("Invalid phase")
    return directory / f"{database}-{phase}.json"


def save_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, indent=2, default=str)
        output.write("\n")


async def dataset_identity(connection: AsyncConnection) -> dict[str, Any]:
    row = (
        (
            await connection.execute(
                text("SELECT seed,order_count,digest,status FROM experiment_dataset WHERE id=1")
            )
        )
        .mappings()
        .one()
    )
    if row["status"] != "ready":
        raise ValueError("Dataset is incomplete; refusing experiment")
    counts = {}
    for table in ("lab_user", "lab_product", "lab_order", "lab_order_item"):
        counts[table] = int(await connection.scalar(text(f"SELECT COUNT(*) FROM {table}")) or 0)
    if counts != {
        "lab_user": 1000,
        "lab_product": 100,
        "lab_order": row["order_count"],
        "lab_order_item": row["order_count"] * 2,
    }:
        raise ValueError("Dataset exact counts do not match manifest")
    checksums = (
        await connection.execute(
            text("CHECKSUM TABLE lab_user,lab_product,lab_order,lab_order_item EXTENDED")
        )
    ).all()
    if any(r[1] is None for r in checksums):
        raise ValueError("Cannot establish real database content checksums")
    return {
        "table_checksums": {r[0].split(".")[-1]: int(r[1]) for r in checksums},
        "seed": row["seed"],
        "order_count": row["order_count"],
        "digest": row["digest"],
        "generator_version": GENERATOR_VERSION,
        "counts": counts,
    }


def load_baseline(directory: Path, database: str, identity: dict[str, Any]) -> dict[str, Any]:
    path = result_path(directory, database, "baseline")
    baseline: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if (
        baseline.get("dataset") != identity
        or baseline.get("database") != database
        or baseline.get("phase") != "baseline"
        or baseline.get("revision") != "0002"
    ):
        raise ValueError("Saved baseline does not match this dataset/revision")
    return baseline


async def collect_sizes(connection: AsyncConnection) -> dict[str, Any]:
    tables = (
        (
            await connection.execute(
                text(
                    "SELECT TABLE_NAME AS table_name, TABLE_ROWS AS estimated_rows, "
                    "DATA_LENGTH AS clustered_bytes_estimate, INDEX_LENGTH AS "
                    "secondary_bytes_estimate FROM information_schema.TABLES WHERE "
                    "TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME"
                )
            )
        )
        .mappings()
        .all()
    )
    indexes = (
        (
            await connection.execute(
                text(
                    "SELECT TABLE_NAME AS table_name, INDEX_NAME AS index_name, "
                    "SEQ_IN_INDEX AS position, COLUMN_NAME AS column_name, NON_UNIQUE AS "
                    "non_unique FROM information_schema.STATISTICS WHERE "
                    "TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX"
                )
            )
        )
        .mappings()
        .all()
    )
    pages = None
    try:
        page_size = int(await connection.scalar(text("SELECT @@innodb_page_size")) or 16384)
        rows = (
            (
                await connection.execute(
                    text(
                        "SELECT table_name,index_name,stat_value FROM mysql.innodb_index_stats "
                        "WHERE database_name=DATABASE() AND stat_name='size' ORDER BY "
                        "table_name,index_name"
                    )
                )
            )
            .mappings()
            .all()
        )
        pages = [
            {
                "table": r["table_name"],
                "index": r["index_name"],
                "pages": int(r["stat_value"]),
                "bytes_estimate": int(r["stat_value"]) * page_size,
            }
            for r in rows
        ]
    except Exception:
        # Optional mysql statistics visibility varies by deployment.
        pass
    return {
        "tables": [dict(r) for r in tables],
        "indexes": [dict(r) for r in indexes],
        "individual_indexes": pages,
        "semantics": (
            "InnoDB allocated page estimates, not exact row bytes or physical file sizes; "
            "TABLE_ROWS is estimated. Per-index stats null if permission unavailable."
        ),
    }


async def measure(database: str, phase: str, repeats: int, directory: Path) -> dict[str, Any]:
    path = result_path(directory, database, phase)
    if path.exists():
        raise ValueError("Refusing to overwrite existing result")
    if phase not in ("baseline", "optimized") or not 3 <= repeats <= 1000:
        raise ValueError("Phase baseline/optimized and repeats in [3,1000] required")
    engine = engine_for(database)
    try:
        async with engine.connect() as connection:
            await assert_owned(connection, database)
            current = await revision(connection)
            if current != ("0002" if phase == "baseline" else "0003"):
                raise ValueError("Wrong migration revision for measurement phase")
            identity = await dataset_identity(connection)
            baseline = (
                load_baseline(directory, database, identity) if phase == "optimized" else None
            )
            if baseline is not None and baseline["repeats"] != repeats:
                raise ValueError("Optimized repeats must match saved baseline")
            for table in ("lab_user", "lab_product", "lab_order", "lab_order_item"):
                await connection.execute(text(f"ANALYZE TABLE {table}"))
            count = identity["order_count"]
            offset = int(count * 0.8)
            started = time.perf_counter()
            boundary = (
                await connection.execute(
                    text(
                        "SELECT created_at,id FROM lab_order ORDER BY created_at DESC,id DESC "
                        "LIMIT 1 OFFSET :offset"
                    ),
                    {"offset": offset - 1},
                )
            ).one()
            cursor_lookup_ms = (time.perf_counter() - started) * 1000
            queries = query_set(count, 500, offset, (boundary[0], boundary[1]))
            measurements = {}
            page_ids = {}
            for name, (sql, parameters) in queries.items():
                statement = text(sql)
                await connection.execute(statement, parameters)  # warm-up, not timed
                timings = []
                result_rows: list[Any] = []
                for _ in range(repeats):
                    start = time.perf_counter()
                    result_rows = list((await connection.execute(statement, parameters)).all())
                    timings.append((time.perf_counter() - start) * 1000)
                plan_rows = (
                    await connection.execute(text("EXPLAIN ANALYZE FORMAT=TREE " + sql), parameters)
                ).all()
                tree = "\n".join(str(row[0]) for row in plan_rows)
                nodes = parse_tree(tree)
                if not nodes:
                    raise ValueError("Could not parse any actual plan metrics")
                accesses = [n["access_rows"] for n in nodes if n["access_rows"] is not None]
                measurements[name] = {
                    "sql": sql,
                    "parameters": parameters,
                    "result_count": len(result_rows),
                    "wall_ms_samples": timings,
                    "p50_ms": percentile(timings, 0.5),
                    "p95_ms": percentile(timings, 0.95),
                    "p99_ms": percentile(timings, 0.99),
                    "serial_queries_per_second": repeats * 1000 / sum(timings),
                    "error_rate": 0,
                    "explain_analyze_tree": tree,
                    "iterators": nodes,
                    "access_operator_rows": sum(accesses) if accesses else None,
                }
                if name in ("offset", "keyset"):
                    page_ids[name] = [int(row[0]) for row in result_rows]
            if page_ids["offset"] != page_ids["keyset"]:
                raise ValueError("OFFSET/keyset page mismatch")
            env = (
                (
                    await connection.execute(
                        text(
                            "SELECT VERSION() AS mysql_version, @@innodb_buffer_pool_size AS "
                            "buffer_pool_bytes, @@transaction_isolation AS isolation_level, "
                            "@@innodb_page_size AS page_bytes"
                        )
                    )
                )
                .mappings()
                .one()
            )
            connections = (
                await connection.execute(text("SHOW STATUS LIKE 'Threads_connected'"))
            ).one()
            result = {
                "schema_version": 1,
                "recorded_at_utc": datetime.now(UTC).isoformat(),
                "database": database,
                "phase": phase,
                "revision": current,
                "dataset": identity,
                "seed_generation": json.loads(
                    result_path(directory, database, "seed").read_text(encoding="utf-8")
                )
                if result_path(directory, database, "seed").exists()
                else None,
                "repeats": repeats,
                "environment": {
                    "mysql": dict(env),
                    "client_os": platform.platform(),
                    "python": sys.version,
                    "sqlalchemy": version("sqlalchemy"),
                    "asyncmy": version("asyncmy"),
                    "clients": 1,
                    "concurrency": 1,
                    "cache": "warm; no buffer-pool flush",
                    "threads_connected": int(connections[1]),
                    "cpu_utilization": None,
                    "memory_utilization": None,
                    "resource_note": (
                        "CPU/memory utilization not sampled; serial QPS is not concurrent API RPS"
                    ),
                },
                "sizes": await collect_sizes(connection),
                "cursor_lookup_ms": cursor_lookup_ms,
                "cursor": {"created_at": boundary[0], "id": boundary[1]},
                "offset": offset,
                "page_ids": page_ids,
                "queries": measurements,
                "scan_metric_note": (
                    "access_operator_rows is sum(actual output rows * loops) for scan/lookup "
                    "iterators; it is not engine physical I/O, not LIMIT output, "
                    "and node times must not be summed."
                ),
            }
            save_result(path, result)
            return result
    finally:
        await engine.dispose()
