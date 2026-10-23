"""Safe experimental CLI. All schema changes run through Alembic."""

import argparse
import asyncio
import json
from pathlib import Path

from alembic import command
from alembic.config import Config

from concurrency_lab.experiments.dataset import seed_database
from concurrency_lab.experiments.runner import (
    DEFAULT_OUTPUT,
    dataset_identity,
    load_baseline,
    measure,
    result_path,
    save_result,
)
from concurrency_lab.experiments.safety import (
    ExperimentSettings,
    assert_owned,
    can_initialize,
    engine_for,
    revision,
    validate_database,
)


def migrate(database: str, target: str) -> None:
    validate_database(database)
    config = Config("alembic.ini")
    config.attributes["database_url"] = ExperimentSettings().url(database)
    command.upgrade(config, target)


async def can_optimize(database: str, directory: Path) -> None:
    engine = engine_for(database)
    try:
        async with engine.connect() as connection:
            await assert_owned(connection, database)
            if await revision(connection) != "0002":
                raise ValueError("Optimization requires baseline revision0002")
            load_baseline(directory, database, await dataset_identity(connection))
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("init")
    seed = sub.add_parser("seed")
    seed.add_argument("--orders", type=int, choices=(10000, 100000, 1000000), required=True)
    seed.add_argument("--seed", type=int, default=20261023)
    seed.add_argument("--batch-size", type=int, default=1000)
    sample = sub.add_parser("measure")
    sample.add_argument("--phase", choices=("baseline", "optimized"), required=True)
    sample.add_argument("--repeats", type=int, default=7)
    sub.add_parser("optimize")
    args = parser.parse_args()
    try:
        validate_database(args.database)
        if args.action == "init":
            asyncio.run(can_initialize(args.database))
            migrate(args.database, "0002")
        elif args.action == "seed":
            path = result_path(args.output_dir, args.database, "seed")
            if path.exists():
                raise ValueError("Refusing to overwrite generation result")
            result = asyncio.run(
                seed_database(args.database, args.orders, args.seed, args.batch_size)
            )
            save_result(path, result)
        elif args.action == "optimize":
            asyncio.run(can_optimize(args.database, args.output_dir))
            migrate(args.database, "0003")
        else:
            result = asyncio.run(measure(args.database, args.phase, args.repeats, args.output_dir))
            print(
                json.dumps(
                    {
                        "database": args.database,
                        "phase": args.phase,
                        "orders": result["dataset"]["order_count"],
                    }
                )
            )
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        parser.exit(2, str(exc) + "\n")
    except Exception:
        # SQLAlchemy and driver errors can embed connection details and data; keep CLI clean.
        parser.exit(
            1,
            "Experiment failed; check service availability, permissions and schema "
            "(details redacted).\n",
        )


if __name__ == "__main__":
    main()
