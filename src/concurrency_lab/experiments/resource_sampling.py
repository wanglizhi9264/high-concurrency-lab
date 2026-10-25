"""Actual owned-process and Docker resource observations shared by explicit experiment runners."""

import json
import subprocess
from datetime import UTC, datetime
from typing import Any

import psutil

from concurrency_lab.schemas.benchmarks import ResourceSample


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
        all_cpu_known = True
        known_members = 0
        result = ResourceSample(
            observed_at=datetime.now(UTC).isoformat(),
            elapsed_s=0,
            scope=scope,
            source="psutil owned process tree: CPU since previous poll, summed RSS",
        )
        try:
            root = psutil.Process(process.pid)
            members = [root, *root.children(recursive=True)]
            for member in members:
                cached = self.processes.get(member.pid)
                if cached is None:
                    member.cpu_percent(None)
                    self.processes[member.pid] = member
                    all_cpu_known = False
                else:
                    cpu += float(cached.cpu_percent(None))
                    known_members += 1
                rss += int(member.memory_info().rss)
            result.cpu_percent = cpu if all_cpu_known else None
            result.memory_bytes = rss
            result.raw = {"members": len(members), "cpu_members_with_baseline": known_members}
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            result.error_code = "process_unavailable"
        return result


def collect_docker_samples(
    container_ids: list[str], unavailable_scope: str = "mysql_redis_containers"
) -> list[ResourceSample]:
    if not container_ids:
        return [
            ResourceSample(
                observed_at=datetime.now(UTC).isoformat(),
                elapsed_s=0,
                scope=unavailable_scope,
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
                scope=unavailable_scope,
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
