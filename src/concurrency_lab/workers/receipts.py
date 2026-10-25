"""Run the fixed receipt worker in one explicitly owned database/scenario."""

import argparse
import asyncio
import json
import signal
from uuid import UUID

from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from concurrency_lab.cache.client import create_redis
from concurrency_lab.cache.task_stream import TaskStream
from concurrency_lab.core.config import Settings
from concurrency_lab.db.business import BUSINESS_DATABASES, open_business_resources
from concurrency_lab.domain.tasks import WorkerPolicy
from concurrency_lab.services.task_execution import TaskExecution
from concurrency_lab.workers.runtime import WorkerRuntime


async def run(arguments: argparse.Namespace) -> None:
    policy = WorkerPolicy(arguments.timeout_seconds, arguments.lease_seconds)
    settings = Settings().model_copy(
        update={"business_database": arguments.database, "business_enabled": True}
    )
    if not settings.business_writes_enabled:
        raise ValueError("Worker writes require BUSINESS_WRITES_ENABLED=true")
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: loop.call_soon_threadsafe(stop.set))
    async with open_business_resources(settings) as resources:
        client = create_redis(settings)
        try:
            stream = TaskStream(client, arguments.database, arguments.scenario)
            worker = WorkerRuntime(resources, stream, policy, arguments.crash_after_claim)
            execution: TaskExecution = worker.execution
            async with execution.transaction() as repository:
                if not await repository.scenario_exists(arguments.scenario.hex):
                    raise ValueError("Explicit inventory scenario not found in owned database")
            cycles = 0
            while not stop.is_set():
                try:
                    outcome = await worker.cycle(arguments.role)
                except (RedisError, SQLAlchemyError, TimeoutError):
                    outcome = "dependency_unavailable_or_commit_unconfirmed"
                print(
                    json.dumps(
                        {"worker_id": worker.worker_id, "cycle": cycles + 1, "outcome": outcome}
                    ),
                    flush=True,
                )
                cycles += 1
                if arguments.once or (arguments.max_cycles and cycles >= arguments.max_cycles):
                    break
                try:
                    await asyncio.wait_for(stop.wait(), timeout=0.1)
                except TimeoutError:
                    pass
        finally:
            await client.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", choices=sorted(BUSINESS_DATABASES), required=True)
    parser.add_argument("--scenario", type=UUID, required=True)
    parser.add_argument("--role", choices=["both", "dispatcher", "consumer"], default="both")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--max-cycles", type=int, choices=range(1, 10001), metavar="1..10000")
    parser.add_argument("--timeout-seconds", type=float, default=1)
    parser.add_argument("--lease-seconds", type=float, default=5)
    parser.add_argument(
        "--crash-after-claim",
        action="store_true",
        help="Controlled experiment: exit this child70 after durable claim",
    )
    arguments = parser.parse_args()
    try:
        asyncio.run(run(arguments))
    except ValueError as error:
        parser.exit(2, str(error) + "\n")
    except (SQLAlchemyError, RedisError):
        parser.exit(1, "Dependency unavailable; preserve durable state and retry the same scope.\n")


if __name__ == "__main__":
    main()
