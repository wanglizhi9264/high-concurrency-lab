"""Raw request recording and exact aggregation; no gevent/Locust imports."""

import csv
import math
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from concurrency_lab.experiments.queries import percentile
from concurrency_lab.schemas.benchmarks import LoadHistorySample, LoadParameters, LoadSummary

REQUEST_FIELDS = [
    "completed_epoch",
    "response_ms",
    "status",
    "failed",
    "sql_attempts",
    "error_code",
    "error_type",
    "request_id",
    "name",
    "started_epoch",
]


def validate_load_parameters(users: int, seconds: int, task_rate: float, pool_size: int) -> None:
    LoadParameters(
        users=users, seconds=seconds, task_rate=task_rate, pool_size=pool_size, spawn_rate=500
    )


class RequestCsvRecorder:
    def __init__(self, path: Path) -> None:
        self.output = path.open("x", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.output, fieldnames=REQUEST_FIELDS)
        self.writer.writeheader()
        self.start_epoch = 0.0
        self.end_epoch = 0.0
        self.start_monotonic = 0.0
        self.end_monotonic = 0.0
        self.peak_users = 0
        self.user_sequence = 0

    def start(self) -> None:
        self.start_epoch = time.time()
        self.start_monotonic = time.perf_counter()

    def finish(self) -> None:
        self.end_epoch = max(self.end_epoch, time.time())
        self.end_monotonic = max(self.end_monotonic, time.perf_counter())
        self.output.flush()

    def record(self, row: dict[str, Any], users: int) -> None:
        self.writer.writerow(row)
        self.peak_users = max(self.peak_users, users)
        self.end_epoch = time.time()
        self.end_monotonic = time.perf_counter()

    def next_user(self) -> int:
        self.user_sequence += 1
        return self.user_sequence

    def close(self) -> None:
        self.output.close()


def aggregate_requests(
    path: Path, start_epoch: float, end_epoch: float, duration_s: float
) -> tuple[LoadSummary, list[LoadHistorySample]]:
    if end_epoch <= start_epoch or duration_s <= 0 or not math.isfinite(duration_s):
        raise ValueError("Invalid test window")
    samples: list[float] = []
    failures = unknown = sql_total = http_504 = pool_timeouts = transport_timeouts = 0
    buckets: dict[int, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    with path.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            latency = float(row["response_ms"])
            completed = float(row["completed_epoch"])
            if (
                not math.isfinite(latency)
                or latency < 0
                or not start_epoch <= completed <= end_epoch
            ):
                raise ValueError("Invalid request observation")
            samples.append(latency)
            failed = int(row["failed"])
            if failed not in (0, 1):
                raise ValueError("Invalid failure flag")
            failures += failed
            sql = int(row["sql_attempts"]) if row["sql_attempts"] else None
            if sql is not None and sql < 0:
                raise ValueError("Invalid SQL count")
            unknown += sql is None
            sql_total += sql or 0
            http_504 += row["status"] == "504"
            pool_timeouts += row["error_code"] == "pool_timeout"
            transport_timeouts += "timeout" in row["error_type"].lower()
            # The final bin is right-closed, so a completion exactly at end is not lost.
            offset = min(int(completed - start_epoch), math.ceil(end_epoch - start_epoch) - 1)
            bucket = buckets[offset]
            bucket[0] += 1
            bucket[1] += failed
            bucket[2] += sql or 0
            bucket[3] += sql is not None
    count = len(samples)
    known = count - unknown
    summary = LoadSummary(
        requests=count,
        failures=failures,
        completed_rps=count / duration_s,
        error_rate=failures / count if count else 0,
        p50_ms=percentile(samples, 0.5) if samples else None,
        p95_ms=percentile(samples, 0.95) if samples else None,
        p99_ms=percentile(samples, 0.99) if samples else None,
        observed_sql_attempts_per_s=sql_total / duration_s if known else None,
        unknown_sql_responses=unknown,
        sql_response_coverage=known / count if count else 0,
        http_504=http_504,
        pool_timeouts=pool_timeouts,
        transport_timeouts=transport_timeouts,
    )
    history = []
    wall_window = end_epoch - start_epoch
    for offset in range(math.ceil(wall_window)):
        interval = min(1.0, wall_window - offset)
        completed, failed, sql, known_count = buckets[offset]
        history.append(
            LoadHistorySample(
                elapsed_s=float(offset),
                interval_s=interval,
                completed=completed,
                completed_rps=completed / interval,
                failures=failed,
                observed_sql_attempts_per_s=sql / interval if known_count else None,
            )
        )
    return summary, history
