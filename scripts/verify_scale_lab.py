"""Readonly validation of complete009records against their exclusive raw phase files."""

import argparse
import json
from pathlib import Path

from concurrency_lab.schemas.benchmarks import ResourceSample
from concurrency_lab.schemas.scale_experiments import ScalePhase, ScaleRun
from concurrency_lab.services.scale_results import RESULT_ROOT, RUN_ID, load_run


def verify_record(directory: Path) -> ScaleRun:
    record = load_run(directory.name, directory.parent)
    if record.manifest.source.sources_dirty:
        raise ValueError("Formal009record must identify a clean source checkpoint")
    for phase in record.phases:
        actual = ScalePhase.model_validate_json((directory / f"{phase.phase}.json").read_bytes())
        if actual != phase:
            raise ValueError("Published phase differs from raw exclusive evidence")
    seed = json.loads((directory / "seed.json").read_text(encoding="utf-8"))
    if seed["dataset"] != record.phases[0].dataset.model_dump(mode="json"):
        raise ValueError("Seed identity differs from measured database identity")
    for table in ("scale_order", "scale_order_partitioned"):
        observation = record.phases[-1].tables[table]
        if not observation.queries["user_projection"].covering_observed:
            raise ValueError(
                "Covering projection was not actually observed; retain and investigate"
            )
    partitioned = record.phases[-1].tables["scale_order_partitioned"].queries
    if (
        partitioned["time_range"].selected_partitions != ["p3"]
        or len(partitioned["id_without_time"].selected_partitions or []) != 5
    ):
        raise ValueError("Actual pruning/non-pruning evidence missing")
    raw_process_seen = False
    with (directory / "resources.jsonl").open(encoding="utf-8") as source:
        for line in source:
            point = ResourceSample.model_validate_json(line)
            if point.scope == "owned_009_database_runner" and not raw_process_seen:
                if point.cpu_percent is not None:
                    raise ValueError("Initial process CPU has no prior poll baseline")
                raw_process_seen = True
    if not raw_process_seen or not record.resources:
        raise ValueError("Actual resource observations missing")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=RESULT_ROOT)
    parser.add_argument("--require-scales", type=int, nargs="+", default=[10000, 1000000])
    arguments = parser.parse_args()
    observed = set()
    for directory in sorted(arguments.output_dir.iterdir()):
        if RUN_ID.fullmatch(directory.name) and (directory / "result.json").is_file():
            result = verify_record(directory)
            observed.add(result.manifest.order_count)
            print(f"{directory.name}: actual{result.manifest.order_count}rows evidence accepted")
    if not set(arguments.require_scales) <= observed:
        raise ValueError("Required actual scales not recorded")


if __name__ == "__main__":
    main()
