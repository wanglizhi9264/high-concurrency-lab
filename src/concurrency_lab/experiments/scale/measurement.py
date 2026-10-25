"""Actual single-client query observations and physical-layout evidence."""

import hashlib
import json
import platform
import time
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

from sqlalchemy import CursorResult, select, text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection

from concurrency_lab.experiments.queries import parse_tree, percentile
from concurrency_lab.experiments.runner import save_result
from concurrency_lab.experiments.scale.dataset import dataset_identity
from concurrency_lab.experiments.scale.identity import source_identity
from concurrency_lab.experiments.scale.queries import partition_observation, query_cases
from concurrency_lab.experiments.scale.safety import REVISIONS, assert_owned, engine_for
from concurrency_lab.models.scale import QUERY_TABLES, TABLE_NAMES, tables

PHASES = ("baseline", "composite", "covering")


async def schema_statistics(connection: AsyncConnection) -> dict[str, Any]:
    schemas, indexes = {}, {}
    for name in sorted(TABLE_NAMES):
        schemas[name] = (await connection.execute(text(f"SHOW CREATE TABLE {name}"))).one()[1]
        indexes[name] = [
            dict(r) for r in (await connection.execute(text(f"SHOW INDEX FROM {name}"))).mappings()
        ]
    sizes = [
        dict(r)
        for r in (
            await connection.execute(
                text(
                    "SELECT TABLE_NAME AS table_name,TABLE_ROWS AS "
                    "estimated_rows,DATA_LENGTH AS clustered_bytes_estimate,INDEX_LENGTH "
                    "AS secondary_bytes_estimate FROM information_schema.tables WHERE "
                    "table_schema=DATABASE() ORDER BY TABLE_NAME"
                )
            )
        ).mappings()
    ]
    partitions = [
        dict(r)
        for r in (
            await connection.execute(
                text(
                    "SELECT TABLE_NAME AS table_name,PARTITION_NAME AS "
                    "partition_name,TABLE_ROWS AS estimated_rows,DATA_LENGTH AS "
                    "clustered_bytes_estimate,INDEX_LENGTH AS secondary_bytes_estimate "
                    "FROM information_schema.partitions WHERE table_schema=DATABASE() "
                    "ORDER BY TABLE_NAME,PARTITION_ORDINAL_POSITION"
                )
            )
        ).mappings()
    ]
    page_stats, page_error = None, None
    try:
        page_size = int(await connection.scalar(text("SELECT @@innodb_page_size")) or 16384)
        rows = (
            await connection.execute(
                text(
                    "SELECT table_name,index_name,stat_value FROM mysql.innodb_index_stats "
                    "WHERE database_name=DATABASE() AND stat_name='size' ORDER BY "
                    "table_name,index_name"
                )
            )
        ).mappings()
        page_stats = [
            dict(
                table=r["table_name"],
                index=r["index_name"],
                pages=int(r["stat_value"]),
                bytes_estimate=int(r["stat_value"]) * page_size,
            )
            for r in rows
        ]
    except DBAPIError as error:
        if getattr(error.orig, "args", (None,))[0] not in (1142, 1044):
            raise
        page_error = "index_statistics_permission_unavailable"
    return {
        "observed_at": datetime.now(UTC).isoformat(),
        "show_create": schemas,
        "indexes": indexes,
        "tables": sizes,
        "partitions": partitions,
        "index_pages": page_stats,
        "index_pages_error": page_error,
        "semantics": "InnoDB allocated-page estimates, not physical file bytes. "
        "TABLE_ROWS/cardinality estimates differ from exact streamed count. "
        "Partition index table names retained verbatim.",
    }


async def mysql_snapshot(connection: AsyncConnection) -> dict[str, Any]:
    environment = dict(
        (
            await connection.execute(
                text(
                    "SELECT VERSION() AS mysql_version,@@innodb_buffer_pool_size AS "
                    "buffer_pool_bytes,@@innodb_page_size AS "
                    "page_bytes,@@transaction_isolation AS isolation_level"
                )
            )
        )
        .mappings()
        .one()
    )
    status = (
        await connection.execute(
            text(
                "SHOW GLOBAL STATUS WHERE Variable_name IN "
                "('Threads_connected','Threads_running','Questions','Queries','Uptime')"
            )
        )
    ).all()
    return {
        "observed_at": datetime.now(UTC).isoformat(),
        "configuration": environment,
        "global_status": {str(r[0]): int(r[1]) for r in status},
        "semantics": "Whole experiment-instance counters, including monitoring/other DBs; "
        "not workload-attributed QPS",
    }


async def _execute_stage(
    connection: AsyncConnection,
    sql: str,
    parameters: dict[str, Any],
    raw: dict[str, Any],
    stage: str,
) -> CursorResult[Any]:
    raw["last_stage"] = stage
    clock = time.perf_counter()
    try:
        return await connection.execute(text(sql), parameters)
    except SQLAlchemyError as error:
        raw.update(
            error_type=type(error).__name__,
            failed_stage=stage,
            failed_stage_client_ms=(time.perf_counter() - clock) * 1000,
            failed_at=datetime.now(UTC).isoformat(),
        )
        raise


async def measure_query(
    connection: AsyncConnection,
    sql: str,
    parameters: dict[str, Any],
    repeats: int,
    partial: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw = partial if partial is not None else {}
    raw.update(
        sql=sql,
        parameters=parameters,
        started_at=datetime.now(UTC).isoformat(),
        warmup_completed=False,
        completed_client_ms_samples=[],
    )
    await _execute_stage(connection, sql, parameters, raw, "warmup")
    raw["warmup_completed"] = True
    samples, result = [], []
    for number in range(repeats):
        started = time.perf_counter()
        result = list(
            (await _execute_stage(connection, sql, parameters, raw, f"select_{number + 1}")).all()
        )
        samples.append((time.perf_counter() - started) * 1000)
        raw["completed_client_ms_samples"] = list(samples)
    tree = "\n".join(
        str(r[0])
        for r in (
            await _execute_stage(
                connection, "EXPLAIN ANALYZE FORMAT=TREE " + sql, parameters, raw, "explain_analyze"
            )
        ).all()
    )
    raw["tree"] = tree
    json_plan = json.loads(
        str(
            (
                await _execute_stage(
                    connection, "EXPLAIN FORMAT=JSON " + sql, parameters, raw, "explain_json"
                )
            ).scalar_one()
        )
    )
    raw["json_plan"] = json_plan
    nodes = parse_tree(tree)
    if not nodes:
        raise ValueError("No actual EXPLAIN ANALYZE iterator observations")
    accesses = [n["access_rows"] for n in nodes if n["access_rows"] is not None]
    rows = [list(row) for row in result]
    return {
        "sql": sql,
        "parameters": parameters,
        "warmups": 1,
        "repeats": repeats,
        "client_ms_samples": samples,
        "p50_ms": percentile(samples, 0.5),
        "p95_ms": percentile(samples, 0.95),
        "p99_ms": percentile(samples, 0.99),
        "serial_selects_per_second": repeats * 1000 / sum(samples),
        "attempts": repeats,
        "failures": 0,
        "error_rate": 0.0,
        "result_count": len(rows),
        "result_rows": rows,
        "result_sha256": hashlib.sha256(
            json.dumps(rows, default=str, separators=(",", ":")).encode()
        ).hexdigest(),
        "tree": tree,
        "json_plan": json_plan,
        "iterators": nodes,
        "access_operator_rows": sum(accesses) if accesses else None,
        **partition_observation(json_plan),
    }


async def measure_phase(
    database: str, phase: str, repeats: int, directory: Path, baseline: dict[str, Any] | None
) -> dict[str, Any]:
    if phase not in PHASES or not 3 <= repeats <= 30:
        raise ValueError("Bounded009phase/repeats required")
    output = directory / f"{phase}.json"
    if output.exists():
        raise FileExistsError("Phase evidence already exists")
    engine = engine_for(database)
    started, source = datetime.now(UTC).isoformat(), source_identity()
    try:
        async with engine.connect() as connection:
            revision = await assert_owned(connection, database)
            if revision != REVISIONS[PHASES.index(phase)]:
                raise ValueError("Wrong schema revision for phase")
            identity = await dataset_identity(connection)
            if baseline and identity != baseline["dataset"]:
                raise ValueError("Query data changed across phases")
            for name in QUERY_TABLES:
                await connection.execute(text(f"ANALYZE TABLE {name}"))
            before = await mysql_snapshot(connection)
            count = identity["order_count"]
            offset = int(count * 0.8)
            observations: dict[str, Any] = {}
            for name in QUERY_TABLES:
                clock = time.perf_counter()
                boundary = (
                    await connection.execute(
                        select(tables[name].c.created_at, tables[name].c.id)
                        .order_by(tables[name].c.created_at.desc(), tables[name].c.id.desc())
                        .offset(max(0, offset - 1))
                        .limit(1)
                    )
                ).one()
                lookup_ms = (time.perf_counter() - clock) * 1000
                cursor = (boundary[0], int(boundary[1]))
                queries: dict[str, Any] = {}
                for case, (sql, parameters) in query_cases(name, count, cursor).items():
                    partial: dict[str, Any] = {}
                    try:
                        queries[case] = await measure_query(
                            connection, sql, parameters, repeats, partial
                        )
                    except (SQLAlchemyError, ValueError) as error:
                        save_result(
                            directory / f"{phase}-{name}-{case}-failure.json",
                            {
                                "complete": False,
                                "phase": phase,
                                "table": name,
                                "case": case,
                                "error_type": type(error).__name__,
                                "partial_query": partial,
                                "completed_queries_this_table": queries,
                                "completed_tables": observations,
                                "source": source,
                                "dataset": identity,
                            },
                        )
                        raise
                    if (
                        baseline
                        and queries[case]["result_sha256"]
                        != baseline["tables"][name]["queries"][case]["result_sha256"]
                    ):
                        raise ValueError("Query result changed across index phases")
                pages = {
                    case: [r[0] for r in queries[case]["result_rows"]]
                    for case in ("offset", "keyset")
                }
                if pages["offset"] != pages["keyset"]:
                    raise ValueError("Stable OFFSET/keyset pages differ")
                observations[name] = {
                    "cursor_lookup_ms": lookup_ms,
                    "cursor": {"created_at": cursor[0], "id": cursor[1]},
                    "offset": offset,
                    "page_ids": pages,
                    "queries": queries,
                }
            for case in observations[QUERY_TABLES[0]]["queries"]:
                if (
                    observations[QUERY_TABLES[0]]["queries"][case]["result_sha256"]
                    != observations[QUERY_TABLES[1]]["queries"][case]["result_sha256"]
                ):
                    raise ValueError("Ordinary/partitioned logical query results differ")
            statistics = await schema_statistics(connection)
            after = await mysql_snapshot(connection)
            result = {
                "phase": phase,
                "revision": revision,
                "started_at": started,
                "finished_at": datetime.now(UTC).isoformat(),
                "source": source,
                "dataset": identity,
                "repeats": repeats,
                "tables": observations,
                "statistics": statistics,
                "mysql_before": before,
                "mysql_after": after,
                "environment": {
                    "client_os": platform.platform(),
                    "python": platform.python_version(),
                    "sqlalchemy": version("sqlalchemy"),
                    "asyncmy": version("asyncmy"),
                    "clients": 1,
                    "cache": "warm; one warmup; no buffer pool flush",
                },
            }
            if source_identity() != source:
                raise ValueError("Sources changed during phase")
            save_result(output, result)
            return result
    finally:
        await engine.dispose()
