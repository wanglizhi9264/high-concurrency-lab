"""Source-frozen009run with an owned child and verified experiment-container sampling."""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from concurrency_lab.experiments.resource_sampling import (
    ProcessSampler,
    collect_docker_samples,
    stop_owned_process,
)
from concurrency_lab.experiments.runner import save_result
from concurrency_lab.experiments.safety import ExperimentSettings
from concurrency_lab.experiments.scale.identity import ROOT, source_identity
from concurrency_lab.experiments.scale.safety import SCALES, validate_target
from concurrency_lab.schemas.scale_experiments import ScaleRun


def resolve_experiment_container(project: str) -> dict[str, Any]:
    if re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,62}", project) is None:
        raise ValueError("Invalid Compose project")
    output = subprocess.check_output(
        [
            "docker",
            "compose",
            "-p",
            project,
            "-f",
            "compose.yaml",
            "-f",
            "compose.experiments.yaml",
            "--profile",
            "experiments",
            "ps",
            "-q",
            "mysql-experiment",
        ],
        cwd=ROOT,
        text=True,
    ).split()
    if len(output) != 1:
        raise ValueError("Exactly one explicit project mysql-experiment container required")
    data = json.loads(subprocess.check_output(["docker", "inspect", output[0]], text=True))[0]
    labels = data["Config"]["Labels"]
    if (
        labels["com.docker.compose.project"] != project
        or labels["com.docker.compose.service"] != "mysql-experiment"
    ):
        raise ValueError("Container scope mismatch")
    settings = ExperimentSettings()
    bindings = data["NetworkSettings"]["Ports"]["3306/tcp"]
    if settings.host not in ("127.0.0.1", "localhost") or not any(
        b["HostIp"] == "127.0.0.1" and int(b["HostPort"]) == settings.port for b in bindings
    ):
        raise ValueError(
            "Configured experiment connection does not match verified loopback container"
        )
    return {
        "id": data["Id"],
        "name": data["Name"].lstrip("/"),
        "image": data["Image"],
        "project": project,
        "service": "mysql-experiment",
        "host_port": settings.port,
    }


def run(
    count: int,
    batch_size: int,
    repeats: int,
    project: str,
    output_root: Path,
    allow_ten_million: bool = False,
    max_seconds: int = 1800,
) -> Path:
    database = validate_target(f"concurrency_lab_exp_009_{count}", count, allow_ten_million)
    if not 1 <= batch_size <= 10000 or not 3 <= repeats <= 30 or not 60 <= max_seconds <= 7200:
        raise ValueError("Bounded batch/repeats/run deadline required")
    source = source_identity()
    if source["sources_dirty"]:
        raise ValueError("Commit experiment sources before measurement; dirty runs not published")
    container = resolve_experiment_container(project)
    run_id = "scale-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8]
    directory = output_root / run_id
    directory.mkdir(parents=True, exist_ok=False)
    logs = ROOT / ".pytest_cache/scale-logs"
    logs.mkdir(parents=True, exist_ok=True)
    process = None
    started = time.monotonic()
    samples = []
    try:
        with (
            (logs / f"{run_id}.log").open("xb") as log,
            (directory / "resources.jsonl").open("x", encoding="utf-8") as raw,
        ):
            arguments = [
                sys.executable,
                "-m",
                "concurrency_lab.experiments.scale",
                "--database",
                database,
                "--output-dir",
                str(directory),
                "--orders",
                str(count),
                "--batch-size",
                str(batch_size),
                "--repeats",
                str(repeats),
            ]
            if allow_ten_million:
                arguments.append("--allow-ten-million")
            process = subprocess.Popen(
                arguments,
                cwd=ROOT,
                env={**os.environ, "PYTHONUTF8": "1"},
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            sampler = ProcessSampler()
            while process.poll() is None:
                cycle = time.monotonic()
                if cycle - started > max_seconds:
                    raise ValueError(
                        "Owned009runner deadline exceeded; partial DB/evidence retained"
                    )
                batch = [
                    sampler.collect(process, "owned_009_database_runner"),
                    *collect_docker_samples(
                        [container["id"]], unavailable_scope="009_mysql_experiment_container"
                    ),
                ]
                for sample in batch:
                    samples.append(sample)
                    raw.write(sample.model_dump_json() + "\n")
                raw.flush()
                time.sleep(max(0, 1 - (time.monotonic() - cycle)))
            if process.returncode != 0:
                raise ValueError(
                    "009child failed; preserve raw records and ignored local diagnostics"
                )
        result = json.loads((directory / "database-result.json").read_text(encoding="utf-8"))
        if source_identity() != source or result["manifest"]["source"] != source:
            raise ValueError("009sources changed during measurement")
        begin = datetime.fromisoformat(result["manifest"]["started_at"]).timestamp()
        end = datetime.fromisoformat(result["manifest"]["finished_at"]).timestamp()
        selected = []
        for sample in samples:
            epoch = datetime.fromisoformat(sample.observed_at).timestamp()
            if begin <= epoch <= end:
                selected.append(
                    sample.model_copy(update={"elapsed_s": epoch - begin}).model_dump(mode="json")
                )
        result["resources"] = selected
        result["manifest"]["container"] = container
        result["definitions"]["resources"] = (
            "psutil owned child tree CPU since previous poll/summed RSS; first CPU unknown. "
            "Docker stats separate VM/container CPU and rounded memory estimates; "
            "samples are not per-query attribution."
        )
        result = ScaleRun.model_validate(result).model_dump(mode="json")
        if len(json.dumps(result).encode()) > 8_000_000:
            raise ValueError("Record exceeds public8MB limit; raw data retained, not published")
        save_result(directory / "result.json", result)
        return directory
    except (ValueError, OSError, subprocess.SubprocessError) as failure:
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
    finally:
        stop_owned_process(process)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orders", type=int, choices=SCALES, required=True)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument(
        "--project-name", default=os.getenv("COMPOSE_PROJECT_NAME", "high-concurrency-lab")
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "docs/experiments/009-scale-comprehensive-lab/runs",
    )
    parser.add_argument("--allow-ten-million", action="store_true")
    parser.add_argument("--max-seconds", type=int, default=1800)
    arguments = parser.parse_args()
    print(
        run(
            arguments.orders,
            arguments.batch_size,
            arguments.repeats,
            arguments.project_name,
            arguments.output_dir,
            arguments.allow_ten_million,
            arguments.max_seconds,
        )
    )


if __name__ == "__main__":
    main()
