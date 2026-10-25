"""Raw request recording and exact aggregation; no gevent/Locust imports."""

import csv
import hashlib
import math
import subprocess
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
    "call_id",
]


def source_identity(root: Path) -> dict[str, str | bool]:
    """Capture canonical workload code before starting a new measured process."""
    hasher = hashlib.sha256()
    files = sorted(
        [
            *(root / "src").rglob("*.py"),
            *(root / "benchmarks/locust").glob("*.py"),
            root / "scripts/run_load_test.py",
        ]
    )
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Unsafe workload source path")
        hasher.update(path.relative_to(root).as_posix().encode() + b"\0")
        hasher.update(path.read_text(encoding="utf-8").encode() + b"\0")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    dirty = bool(
        subprocess.check_output(
            [
                "git",
                "status",
                "--porcelain",
                "--untracked-files=normal",
                "--",
                "src",
                "benchmarks/locust",
                "scripts/run_load_test.py",
            ],
            cwd=root,
            text=True,
        ).strip()
    )
    return {
        "revision": head,
        "workload_sources_dirty": dirty,
        "workload_sha256": hasher.hexdigest(),
    }


def validate_load_parameters(users: int, seconds: int, task_rate: float, pool_size: int) -> None:
    LoadParameters(
        users=users, seconds=seconds, task_rate=task_rate, pool_size=pool_size, spawn_rate=500
    )


class RequestCsvRecorder:
    def __init__(self, path: Path) -> None:
        self.output = path.open("x", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.output, fieldnames=REQUEST_FIELDS)
        self.writer.writeheader()
        self.starts_output = path.with_name("starts.csv").open("x", newline="", encoding="utf-8")
        self.starts_writer = csv.DictWriter(
            self.starts_output, fieldnames=["call_id", "started_epoch", "name"]
        )
        self.starts_writer.writeheader()
        self.start_epoch = 0.0
        self.end_epoch = 0.0
        self.start_monotonic = 0.0
        self.end_monotonic = 0.0
        self.peak_users = 0
        self.user_sequence = 0
        self.call_sequence = 0

    def start(self) -> None:
        self.start_epoch = time.time()
        self.start_monotonic = time.perf_counter()

    def finish(self) -> None:
        self.end_epoch = max(self.end_epoch, time.time())
        self.end_monotonic = max(self.end_monotonic, time.perf_counter())
        self.output.flush()
        self.starts_output.flush()

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
        self.starts_output.close()

    def start_call(self, name: str) -> int:
        self.call_sequence += 1
        self.starts_writer.writerow(
            {"call_id": self.call_sequence, "started_epoch": time.time(), "name": name}
        )
        return self.call_sequence


def aggregate_requests(
    path: Path,
    start_epoch: float,
    end_epoch: float,
    duration_s: float,
    starts_path: Path | None = None,
) -> tuple[LoadSummary, list[LoadHistorySample]]:
    if (
        not all(math.isfinite(value) for value in (start_epoch, end_epoch, duration_s))
        or end_epoch <= start_epoch
        or duration_s <= 0
    ):
        raise ValueError("Invalid test window")
    if abs(end_epoch - start_epoch - duration_s) > 0.25:
        raise ValueError("Wall clock changed beyond the 250ms binning tolerance")
    samples: list[float] = []
    failures = unknown = sql_total = http_504 = pool_timeouts = transport_timeouts = 0
    buckets: dict[int, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    completed_ids: set[int] = set()
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
            if row.get("call_id"):
                completed_ids.add(int(row["call_id"]))
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
    started_ids: set[int] = set()
    start_buckets: dict[int, int] = defaultdict(int)
    if starts_path is not None:
        with starts_path.open(encoding="utf-8", newline="") as source:
            for row in csv.DictReader(source):
                identifier = int(row["call_id"])
                issued = float(row["started_epoch"])
                if identifier in started_ids or not start_epoch <= issued <= end_epoch:
                    raise ValueError("Invalid client call start observation")
                started_ids.add(identifier)
                offset = min(int(issued - start_epoch), math.ceil(end_epoch - start_epoch) - 1)
                start_buckets[offset] += 1
        if not completed_ids.issubset(started_ids) or len(completed_ids) != count:
            raise ValueError("Completed request identity does not match client call starts")
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
        client_started=len(started_ids) if starts_path is not None else None,
        client_start_rps=len(started_ids) / duration_s if starts_path is not None else None,
        uncompleted_client_calls=len(started_ids - completed_ids)
        if starts_path is not None
        else None,
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
                client_started=start_buckets[offset] if starts_path is not None else None,
                client_start_rps=start_buckets[offset] / interval
                if starts_path is not None
                else None,
            )
        )
    return summary, history
