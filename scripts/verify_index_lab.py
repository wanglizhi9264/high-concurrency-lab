"""Run fresh isolated scales, or validate existing saved evidence without modifying data."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

OUTPUT = Path("docs/experiments/002-mysql-index-baseline/runs")


def verify(count: int, directory: Path = OUTPUT) -> None:
    database = f"concurrency_lab_exp_002_{count}"
    baseline = json.loads((directory / f"{database}-baseline.json").read_text(encoding="utf-8"))
    optimized = json.loads((directory / f"{database}-optimized.json").read_text(encoding="utf-8"))
    assert baseline["dataset"] == optimized["dataset"]
    assert baseline["dataset"]["counts"]["lab_order"] == count
    assert baseline["dataset"]["counts"]["lab_order_item"] == count * 2
    assert baseline["revision"] == "0002" and optimized["revision"] == "0003"
    assert baseline["recorded_at_utc"] < optimized["recorded_at_utc"]
    assert baseline["repeats"] == optimized["repeats"]
    for result in (baseline, optimized):
        assert result["page_ids"]["offset"] == result["page_ids"]["keyset"]
        assert len(result["queries"]) == 6
        assert all(q["iterators"] and q["wall_ms_samples"] for q in result["queries"].values())
    for name in baseline["queries"]:
        assert baseline["queries"][name]["sql"] == optimized["queries"][name]["sql"]
        assert baseline["queries"][name]["parameters"] == optimized["queries"][name]["parameters"]
    print(f"{count}: evidence accepted", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--orders",
        type=int,
        nargs="+",
        choices=(10000, 100000, 1000000),
        default=[10000, 100000, 1000000],
    )
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    for count in args.orders:
        if not args.verify_only:
            prefix = [
                sys.executable,
                "-m",
                "concurrency_lab.experiments.index_baseline",
                "--database",
                f"concurrency_lab_exp_002_{count}",
                "--output-dir",
                str(args.output_dir),
            ]
            for action in (
                ["init"],
                ["seed", "--orders", str(count)],
                ["measure", "--phase", "baseline"],
                ["optimize"],
                ["measure", "--phase", "optimized"],
            ):
                subprocess.run([*prefix, *action], check=True)
                print(f"{count}: {action[0]} complete", flush=True)
        verify(count, args.output_dir)


if __name__ == "__main__":
    main()
