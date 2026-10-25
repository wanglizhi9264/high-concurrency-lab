"""Trusted009record catalogue only; never invokes SQL, scripts or caller-selected paths."""

import re
from pathlib import Path

from pydantic import ValidationError

from concurrency_lab.schemas.scale_experiments import ScaleRun, ScaleSummary
from concurrency_lab.services.visualization import ROOT

RESULT_ROOT = ROOT / "docs/experiments/009-scale-comprehensive-lab/runs"
RUN_ID = re.compile(r"^scale-[0-9]{8}T[0-9]{6}-[0-9a-f]{8}$")


def load_run(identifier: str, directory: Path | None = None) -> ScaleRun:
    if RUN_ID.fullmatch(identifier) is None:
        raise ValueError("Invalid009run ID")
    root = (directory or RESULT_ROOT).resolve()
    folder, path = root / identifier, root / identifier / "result.json"
    try:
        if (
            folder.is_symlink()
            or path.is_symlink()
            or path.resolve().parent.parent != root
            or path.stat().st_size > 8_000_000
        ):
            raise ValueError("Unsafe/oversized009record")
        result = ScaleRun.model_validate_json(path.read_bytes())
        if result.manifest.id != identifier:
            raise ValueError("009record ID mismatch")
        return result
    except (OSError, ValidationError) as error:
        raise ValueError("009record unavailable or invalid") from error


def run_ids() -> list[str]:
    if not RESULT_ROOT.exists():
        return []
    return sorted(
        [
            path.name
            for path in RESULT_ROOT.iterdir()
            if RUN_ID.fullmatch(path.name)
            and not path.is_symlink()
            and (path / "result.json").is_file()
        ],
        reverse=True,
    )[:50]


def summaries() -> list[ScaleSummary]:
    items = []
    for identifier in run_ids():
        result = load_run(identifier)
        items.append(
            ScaleSummary(
                manifest=result.manifest,
                phases=[phase.phase for phase in result.phases],
                limitations=result.limitations,
            )
        )
    return items
