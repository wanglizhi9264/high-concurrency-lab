"""Bounded real Locust run with owned API process, raw evidence and resource sampling."""

import argparse
import csv
import json
import os
import platform
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import psutil

from concurrency_lab.experiments.load_recording import aggregate_requests
from concurrency_lab.schemas.benchmarks import (
    BusinessMetrics,
    LoadManifest,
    LoadParameters,
    RecordedLoadRun,
    ResourceSample,
)

ROOT = Path(__file__).resolve().parents[1]


def parse_memory_bytes(value: str) -> int:
    parts = value.strip().split()
    if len(parts) == 1:
        import re

        match = re.fullmatch(r"([0-9.]+)([A-Za-z]+)", parts[0])
        if match is None:
            raise ValueError("Invalid Docker memory amount")
        parts = [match[1], match[2]]
    units = {
        "B": 1,
        "kB": 1000,
        "KB": 1000,
        "MB": 1000000,
        "GB": 1000000000,
        "KiB": 1024,
        "MiB": 1048576,
        "GiB": 1073741824,
        "TiB": 1099511627776,
    }
    return int(float(parts[0]) * units[parts[1]])


class ProcessSampler:
    def __init__(self) -> None:
        self.processes: dict[int, Any] = {}

    def collect(self, process: subprocess.Popen[Any], scope: str) -> ResourceSample:
        cpu = 0.0
        rss = 0
        known_cpu = False
        result = ResourceSample(
            observed_at=datetime.now(UTC).isoformat(),
            elapsed_s=0,
            scope=scope,
            source="psutil owned process tree: CPU since previous poll, summed RSS",
        )
        try:
            root = psutil.Process(process.pid)
            for member in [root, *root.children(recursive=True)]:
                cached = self.processes.get(member.pid)
                if cached is None:
                    member.cpu_percent(None)
                    self.processes[member.pid] = member
                else:
                    cpu += float(cached.cpu_percent(None))
                    known_cpu = True
                rss += int(member.memory_info().rss)
            result.cpu_percent = cpu if known_cpu else None
            result.memory_bytes = rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            result.error_code = "process_unavailable"
        return result


def collect_docker_samples(container_ids: list[str]) -> list[ResourceSample]:
    if not container_ids:
        return [
            ResourceSample(
                observed_at=datetime.now(UTC).isoformat(),
                elapsed_s=0,
                scope="mysql_redis_containers",
                source="docker stats",
                error_code="containers_unavailable",
            )
        ]
    try:
        output = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}", *container_ids],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout
        samples = []
        for line in output.splitlines():
            raw = json.loads(line)
            used, limit = raw["MemUsage"].split("/")
            samples.append(
                ResourceSample(
                    observed_at=datetime.now(UTC).isoformat(),
                    elapsed_s=0,
                    scope=f"docker:{raw['Name']}",
                    source="docker stats CLI / Docker Linux VM",
                    cpu_percent=float(raw["CPUPerc"].rstrip("%")),
                    memory_bytes=parse_memory_bytes(used),
                    memory_limit_bytes=parse_memory_bytes(limit),
                    raw=raw,
                )
            )
        return samples
    except (subprocess.SubprocessError, ValueError, KeyError):
        return [
            ResourceSample(
                observed_at=datetime.now(UTC).isoformat(),
                elapsed_s=0,
                scope="mysql_redis_containers",
                source="docker stats",
                error_code="docker_sample_unavailable",
            )
        ]


def stop_owned_process(process: subprocess.Popen[Any] | None) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        root = psutil.Process(process.pid)
        owned = [*root.children(recursive=True), root]
        for member in owned:
            try:
                member.terminate()
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(owned, timeout=5)
        for member in alive:
            member.kill()
        process.wait(timeout=5)
    except psutil.NoSuchProcess:
        pass


def wait_for_owned_api(client: httpx.Client, process: subprocess.Popen[Any]) -> BusinessMetrics:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise ValueError("Owned API stopped during startup; see ignored api.log")
        try:
            response = client.get("/api/v1/observability/business-metrics")
            if response.status_code == 200:
                snapshot = BusinessMetrics.model_validate(response.json())
                if snapshot.status == "ok":
                    return snapshot
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(0.2)
    raise ValueError("Business API not ready; initialize owned business dataset first")


def publish_record(
    directory: Path,
    run_id: str,
    parameters: LoadParameters,
    initial: BusinessMetrics,
    resources: list[ResourceSample],
) -> RecordedLoadRun:
    window = json.loads((directory / "window.json").read_text(encoding="utf-8"))
    start, end, duration = window["start_epoch"], window["end_epoch"], window["duration_s"]
    summary, history = aggregate_requests(directory / "requests.csv", start, end, duration)
    selected_resources = []
    for sample in resources:
        epoch = datetime.fromisoformat(sample.observed_at).timestamp()
        if start <= epoch <= end:
            selected_resources.append(sample.model_copy(update={"elapsed_s": epoch - start}))
    with (directory / "locust_stats.csv").open(encoding="utf-8", newline="") as source:
        locust_statistics = list(csv.DictReader(source))
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    result = RecordedLoadRun(
        manifest=LoadManifest(
            id=run_id,
            start_epoch=start,
            end_epoch=end,
            duration_s=duration,
            parameters=parameters,
            peak_users=window["peak_users"],
            dataset=initial.dataset or {},
            environment={
                "platform": platform.platform(),
                "python": platform.python_version(),
                "locust": version("locust"),
                "psutil": version("psutil"),
                "revision": revision,
                "mysql": initial.mysql_version,
                "application_workers": 1,
                "pool": initial.configuration,
                "csv_history_interval_s": 1,
            },
            raw_files=sorted(
                path.name
                for path in directory.iterdir()
                if path.suffix in (".csv", ".jsonl", ".json")
            ),
        ),
        summary=summary,
        history=history,
        resources=selected_resources,
        locust_statistics=locust_statistics,
        semantics={
            "window": ("Actual test-start through stop/drain/quitting; ramp and drain included."),
            "rate": (
                "users is target concurrency; spawn_rate is users/s; task_rate is closed-loop "
                "tasks/user/s, one request/task, not guaranteed open arrival rate."
            ),
            "rps": "Completed observed HTTP requests / actual monotonic test window seconds.",
            "sql": (
                "Received SQL span attempts / same window; unknown responses counted separately. "
                "Excludes internal pre-ping and unreturned traces."
            ),
            "percentiles": (
                "Linear interpolation over raw response_ms, including failures. "
                "Original Locust rounded histogram stats retained separately."
            ),
            "history": (
                "Actual one-second completion bins, not Locust rolling history. "
                "Last bin may be partial."
            ),
            "locust_csv": (
                "Original history rates/percentiles are rolling; counts cumulative. "
                "Do not average percentiles."
            ),
            "mysql": (
                "Global Questions/Queries include monitoring, health and transactions. "
                "Delta/elapsed is instance statement rate, not business SQL QPS; "
                "reset on Uptime/counter decrease."
            ),
            "resources": (
                "psutil process-tree CPU/summed RSS; first CPU null. Docker CLI uses a separate "
                "VM/container scope. CPU may exceed100%; RSS may double-count shared pages."
            ),
            "timeouts": (
                "HTTP504, pool_timeout and transport timeout overlap; "
                "do not add as mutually exclusive failures."
            ),
        },
        limitations=[
            "Short ramp-inclusive exploratory run, not a capacity or reliable tail-latency claim.",
            (
                "Monitoring competes for pool capacity and issues SQL. "
                "Docker CLI sampling cadence is measured, not assumed."
            ),
            (
                "Closed-loop users reduce offered throughput when requests slow; "
                "client start is not server arrival."
            ),
            (
                "CPU intervals may cross window edges; resource observations "
                "have distinct process/container scopes."
            ),
        ],
    )
    with (directory / "result.json").open("x", encoding="utf-8") as output:
        output.write(result.model_dump_json(indent=2))
    return result


def execute_load_run(parameters: LoadParameters, port: int, output_root: Path) -> None:
    if not 1024 <= port <= 65535 or port in (5173, 5174, 18002):
        raise ValueError("Use an unused dedicated loopback port, not a preview port")
    if parameters.users / parameters.spawn_rate + 2 > parameters.seconds:
        raise ValueError("Duration must cover user ramp plus at least two seconds")
    with socket.socket() as check:
        check.bind(("127.0.0.1", port))
    run_id = "load-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8]
    directory = output_root / run_id
    directory.mkdir(parents=True, exist_ok=False)
    environment = dict(
        os.environ,
        BUSINESS_ENABLED="true",
        BUSINESS_DATABASE="concurrency_lab_business",
        DB_POOL_SIZE=str(parameters.pool_size),
        DB_MAX_OVERFLOW="0",
        DB_POOL_TIMEOUT="1",
        BUSINESS_REQUEST_TIMEOUT="5",
    )
    api_process = locust_process = None
    creation = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        with (
            (directory / "api.log").open("x", encoding="utf-8") as api_log,
            (directory / "locust.log").open("x", encoding="utf-8") as locust_log,
        ):
            api_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "concurrency_lab.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=ROOT,
                env=environment,
                stdout=api_log,
                stderr=subprocess.STDOUT,
                creationflags=creation,
            )
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=2
            ) as client:
                initial = wait_for_owned_api(client, api_process)
                containers = subprocess.run(
                    ["docker", "compose", "ps", "-q", "mysql", "redis"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=True,
                ).stdout.split()
                locust_process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "locust",
                        "-f",
                        str(ROOT / "benchmarks/locust/locustfile.py"),
                        "--headless",
                        "--only-summary",
                        "--host",
                        f"http://127.0.0.1:{port}",
                        "--users",
                        str(parameters.users),
                        "--spawn-rate",
                        str(parameters.spawn_rate),
                        "--run-time",
                        f"{parameters.seconds}s",
                        "--stop-timeout",
                        "10",
                        "--csv",
                        str(directory.resolve() / "locust"),
                        "--csv-full-history",
                        "--exit-code-on-error",
                        "0",
                        "--lab-output",
                        str(directory.resolve()),
                        "--lab-task-rate",
                        str(parameters.task_rate),
                        "--lab-scenario",
                        parameters.scenario,
                    ],
                    cwd=ROOT,
                    env=environment,
                    stdout=locust_log,
                    stderr=subprocess.STDOUT,
                    creationflags=creation,
                )
                sampler = ProcessSampler()
                samples = []
                deadline = time.monotonic() + parameters.seconds + 45
                with (directory / "resources.jsonl").open("x", encoding="utf-8") as resource_file:
                    while locust_process.poll() is None:
                        if time.monotonic() > deadline:
                            raise ValueError("Owned load process exceeded bounded runtime")
                        cycle = time.monotonic()
                        batch = [
                            sampler.collect(api_process, "api_process_tree"),
                            sampler.collect(locust_process, "locust_process_tree"),
                        ]
                        try:
                            metrics = BusinessMetrics.model_validate(
                                client.get("/api/v1/observability/business-metrics").json()
                            )
                            batch.append(
                                ResourceSample(
                                    observed_at=datetime.now(UTC).isoformat(),
                                    elapsed_s=0,
                                    scope="business_pool_mysql_instance",
                                    source="live business monitor",
                                    business=metrics,
                                )
                            )
                        except (httpx.HTTPError, ValueError):
                            batch.append(
                                ResourceSample(
                                    observed_at=datetime.now(UTC).isoformat(),
                                    elapsed_s=0,
                                    scope="business_pool_mysql_instance",
                                    source="live business monitor",
                                    error_code="monitor_unavailable",
                                )
                            )
                        batch.extend(collect_docker_samples(containers))
                        for sample in batch:
                            resource_file.write(sample.model_dump_json() + "\n")
                        resource_file.flush()
                        samples.extend(batch)
                        time.sleep(max(0, 1 - (time.monotonic() - cycle)))
                if locust_process.returncode != 0:
                    raise ValueError("Locust did not complete normally; raw files retained")
                result = publish_record(directory, run_id, parameters, initial, samples)
                print(
                    json.dumps(
                        {
                            "id": run_id,
                            "users": parameters.users,
                            "requests": result.summary.requests,
                            "failures": result.summary.failures,
                            "completed_rps": result.summary.completed_rps,
                        }
                    )
                )
    except (ValueError, OSError, subprocess.SubprocessError):
        with (directory / "incomplete.json").open("x", encoding="utf-8") as output:
            json.dump({"complete": False, "reason": "run_or_publication_failed"}, output)
        raise
    finally:
        stop_owned_process(locust_process)
        stop_owned_process(api_process)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--users", type=int, choices=(10, 50, 100, 500), required=True)
    parser.add_argument("--seconds", type=int, default=15)
    parser.add_argument("--pool-size", type=int, default=5)
    parser.add_argument("--task-rate", type=float, default=1)
    parser.add_argument("--spawn-rate", type=float, default=500)
    parser.add_argument("--scenario", choices=("mixed", "hot", "normal", "deep"), default="mixed")
    parser.add_argument("--port", type=int, default=18003)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "docs/experiments/005-real-load-testing/runs"
    )
    arguments = parser.parse_args()
    parameters = LoadParameters(
        users=arguments.users,
        seconds=arguments.seconds,
        pool_size=arguments.pool_size,
        task_rate=arguments.task_rate,
        spawn_rate=arguments.spawn_rate,
        scenario=arguments.scenario,
    )
    execute_load_run(parameters, arguments.port, arguments.output_dir)


if __name__ == "__main__":
    main()
