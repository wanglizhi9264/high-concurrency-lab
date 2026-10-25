"""Trusted recorded-load catalogue. No shell, SQL or caller-supplied paths."""

import re
from pathlib import Path

from pydantic import ValidationError

from concurrency_lab.schemas.benchmarks import RecordedLoadRun
from concurrency_lab.services.visualization import ROOT

LOAD_ROOT = ROOT / "docs/experiments/005-real-load-testing/runs"
RUN_ID = re.compile(r"^load-[0-9]{8}T[0-9]{6}-[0-9a-f]{8}$")


def validate_run_id(run_id: str) -> str:
    if RUN_ID.fullmatch(run_id) is None:
        raise ValueError("Invalid recorded run ID")
    return run_id


def load_benchmark(run_id: str, directory: Path = LOAD_ROOT) -> RecordedLoadRun:
    validate_run_id(run_id)
    root = directory.resolve()
    folder = root / run_id
    path = folder / "result.json"
    try:
        if (
            folder.is_symlink()
            or path.is_symlink()
            or path.resolve().parent.parent != root
            or path.stat().st_size > 4_000_000
        ):
            raise ValueError("Unsafe or oversized recorded run")
        result = RecordedLoadRun.model_validate_json(path.read_bytes())
        if result.manifest.id != run_id:
            raise ValueError("Run identity mismatch")
        return result
    except (OSError, ValidationError) as error:
        raise ValueError("Recorded run unavailable or invalid") from error


def benchmark_ids() -> list[str]:
    if not LOAD_ROOT.exists():
        return []
    return sorted(
        [
            path.name
            for path in LOAD_ROOT.iterdir()
            if RUN_ID.fullmatch(path.name)
            and not path.is_symlink()
            and (path / "result.json").is_file()
        ],
        reverse=True,
    )[:50]
