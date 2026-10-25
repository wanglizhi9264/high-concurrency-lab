"""Durable acceptance and readonly lifecycle observations; never starts a worker."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Literal, TypeVar
from uuid import UUID

from redis.exceptions import RedisError
from sqlalchemy import RowMapping
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.exc import TimeoutError as PoolTimeout

from concurrency_lab.cache.task_stream import TaskStream
from concurrency_lab.core.exceptions import BusinessFailure, FailureCode
from concurrency_lab.db.business import BusinessResources, owned_session, pool_gauges
from concurrency_lab.db.errors import mysql_error_code
from concurrency_lab.domain.tasks import task_fingerprint
from concurrency_lab.observability.recording import RequestObservation
from concurrency_lab.repositories.task_repository import NOW, TaskRepository
from concurrency_lab.schemas.tasks import (
    AttemptDTO,
    EventDTO,
    OutboxDTO,
    QueueSnapshot,
    ReceiptDTO,
    RetryInput,
    TaskDetail,
    TaskDTO,
    TaskInput,
    TaskList,
    TaskResult,
)

T = TypeVar("T")


def public_task(row: RowMapping) -> TaskDTO:
    return TaskDTO.model_validate({name: row[name] for name in TaskDTO.model_fields})


class TaskService:
    def __init__(
        self, resources: BusinessResources, observation: RequestObservation, budget: float
    ) -> None:
        self.resources, self.observation, self.budget = resources, observation, budget

    async def transaction(
        self,
        operation: Callable[[TaskRepository], Awaitable[T]],
        isolation: Literal["READ COMMITTED", "REPEATABLE READ"] = "READ COMMITTED",
    ) -> T:
        async with owned_session(self.resources, self.observation, isolation) as database:
            return await operation(TaskRepository(database))

    async def bounded(self, operation: Callable[[], Awaitable[T]]) -> T:
        observation = self.observation
        observation.pool_before, observation.pool_before_offset_ms = (
            pool_gauges(self.resources.engine),
            observation.elapsed(),
        )
        try:
            async with asyncio.timeout(self.budget):
                with observation.span(
                    "Task HTTP workflow", "service", "src/concurrency_lab/services/tasks.py"
                ):
                    return await operation()
        except PoolTimeout as error:
            raise BusinessFailure(FailureCode.POOL) from error
        except TimeoutError as error:
            raise BusinessFailure(FailureCode.BUDGET) from error
        except DBAPIError as error:
            raise BusinessFailure(
                FailureCode.CONFLICT
                if mysql_error_code(error) in (1205, 1213)
                else FailureCode.DATABASE
            ) from error
        finally:
            observation.pool_after, observation.pool_after_offset_ms = (
                pool_gauges(self.resources.engine),
                observation.elapsed(),
            )

    async def create(
        self, intent: TaskInput, retry_of: UUID | None = None, disable_faults: bool = True
    ) -> TaskResult:
        async def create(repository: TaskRepository) -> TaskResult:
            effective = intent
            if retry_of is not None:
                original = await repository.task(retry_of.hex)
                if original is None:
                    raise BusinessFailure(FailureCode.NOT_FOUND)
                if original["state"] != "failed":
                    raise BusinessFailure(FailureCode.TASK_STATE)
                effective = TaskInput(
                    task_id=intent.task_id,
                    order_id=original["order_id"],
                    max_attempts=original["max_attempts"],
                    fault_plan=None if disable_faults else original["fault_plan"],
                )
            fingerprint = task_fingerprint(effective, retry_of)
            existing = await repository.task(effective.task_id.hex)
            if existing:
                if existing["payload_sha256"] != fingerprint:
                    raise BusinessFailure(FailureCode.IDEMPOTENCY)
                return TaskResult(task=public_task(existing), replayed=True)
            order = await repository.order(effective.order_id)
            if order is None:
                raise BusinessFailure(FailureCode.NOT_FOUND)
            if order["status"] != "paid":
                raise BusinessFailure(FailureCode.TASK_STATE)
            await repository.create(
                dict(
                    id=effective.task_id.hex,
                    scenario_id=order["scenario_id"],
                    order_id=order["id"],
                    kind="order_receipt",
                    payload_sha256=fingerprint,
                    fault_plan=effective.fault_plan.model_dump(mode="json")
                    if effective.fault_plan
                    else None,
                    max_attempts=effective.max_attempts,
                    attempts=0,
                    state="queued",
                    available_at=NOW,
                    created_at=NOW,
                    updated_at=NOW,
                    retry_of=retry_of.hex if retry_of else None,
                )
            )
            row = await repository.task(effective.task_id.hex)
            assert row is not None
            return TaskResult(task=public_task(row))

        async def workflow() -> TaskResult:
            try:
                return await self.transaction(create)
            except IntegrityError as error:
                if mysql_error_code(error) != 1062:
                    raise
                # The failed transaction is fully closed before resolving concurrent intent.
                return await self.transaction(create)

        return await self.bounded(workflow)

    async def retry(self, identifier: UUID, intent: RetryInput) -> TaskResult:
        return await self.create(
            TaskInput(task_id=intent.task_id, order_id=1), identifier, intent.disable_faults
        )

    async def detail(self, identifier: UUID) -> TaskDetail:
        async def read(repository: TaskRepository) -> TaskDetail:
            row = await repository.task(identifier.hex)
            if row is None:
                raise BusinessFailure(FailureCode.NOT_FOUND)
            events = await repository.events(identifier.hex)
            receipt = (
                await repository.receipt(row["result_receipt_id"])
                if row["result_receipt_id"]
                else None
            )
            return TaskDetail(
                task=public_task(row),
                outbox=OutboxDTO.model_validate(await repository.outbox(identifier.hex)),
                attempts=[
                    AttemptDTO.model_validate({name: r[name] for name in AttemptDTO.model_fields})
                    for r in await repository.attempts(identifier.hex)
                ],
                events=[
                    EventDTO.model_validate({name: r[name] for name in EventDTO.model_fields})
                    for r in reversed(events[:100])
                ],
                events_truncated=len(events) > 100,
                receipt=ReceiptDTO.model_validate(receipt) if receipt else None,
                worker_command=(
                    f"uv run python -m concurrency_lab.workers.receipts "
                    f"--database {self.observation.database} --scenario {UUID(row['scenario_id'])}"
                ),
            )

        return await self.bounded(lambda: self.transaction(read, "REPEATABLE READ"))

    async def list(self, scope: UUID, limit: int) -> TaskList:
        async def read(repository: TaskRepository) -> TaskList:
            if not await repository.scenario_exists(scope.hex):
                raise BusinessFailure(FailureCode.NOT_FOUND)
            return TaskList(
                tasks=[public_task(row) for row in await repository.list_tasks(scope.hex, limit)]
            )

        return await self.bounded(lambda: self.transaction(read))

    async def queue(self, stream: TaskStream) -> QueueSnapshot:
        async def read(repository: TaskRepository) -> tuple[dict[str, int], datetime]:
            if not await repository.scenario_exists(stream.scenario.hex):
                raise BusinessFailure(FailureCode.NOT_FOUND)
            return await repository.counts(stream.scenario.hex), await repository.now()

        async def collect() -> QueueSnapshot:
            started = time.perf_counter()
            counts, observed = await self.transaction(read)
            try:
                with self.observation.span(
                    "Redis queue snapshot commands",
                    "redis_command",
                    "src/concurrency_lab/cache/task_stream.py",
                ):
                    values = await stream.snapshot()
                available = True
            except (RedisError, TimeoutError):
                values = dict(
                    group_ready=None,
                    retained_entries=None,
                    pending=None,
                    group_lag=None,
                    pttl_ms=None,
                )
                available = False
            return QueueSnapshot(
                scenario_id=stream.scenario,
                observed_at=observed,
                collection_ms=(time.perf_counter() - started) * 1000,
                database_counts=counts,
                redis_available=available,
                **values,
            )

        return await self.bounded(collect)
