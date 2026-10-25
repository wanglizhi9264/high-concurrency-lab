"""Database lease fencing and transactional receipt effects, independent of delivery ACK."""

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import RowMapping
from sqlalchemy.exc import SQLAlchemyError

from concurrency_lab.db.business import BusinessResources, owned_session, validate_business_database
from concurrency_lab.domain.tasks import TERMINAL, WorkerPolicy
from concurrency_lab.observability.recording import RequestObservation
from concurrency_lab.repositories.task_repository import NOW, TaskRepository


class FenceLost(Exception):
    """Raising inside the transaction rolls back even an already inserted receipt."""


@dataclass(frozen=True)
class Claim:
    task_id: str
    token: str
    number: int
    order_id: int
    fault_plan: dict[str, Any] | None


@dataclass(frozen=True)
class ClaimResult:
    disposition: str
    claim: Claim | None = None


class TaskExecution:
    def __init__(
        self,
        resources: BusinessResources,
        database: str,
        scenario: UUID,
        policy: WorkerPolicy,
        worker_id: str,
    ) -> None:
        self.resources, self.database, self.scenario = (
            resources,
            validate_business_database(database),
            scenario,
        )
        self.policy, self.worker_id = policy, worker_id

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[TaskRepository]:
        # Each durable step has its own Session, explicit RC, ownership check and bounded lifetime.
        async with asyncio.timeout(5):
            async with owned_session(self.resources, RequestObservation(self.database)) as database:
                yield TaskRepository(database)

    def in_scope(self, row: RowMapping | None) -> bool:
        return row is not None and row["scenario_id"] == self.scenario.hex

    async def claim(self, identifier: str) -> ClaimResult:
        async with self.transaction() as repository:
            row = await repository.task(identifier, locked=True)
            if not self.in_scope(row):
                return ClaimResult("invalid")
            assert row is not None
            now = await repository.now()
            if row["state"] in TERMINAL:
                return ClaimResult("terminal")
            if row["state"] == "running":
                if row["lease_until"] > now:
                    return ClaimResult("busy")  # Never ACK someone else's active execution.
                await repository.finish_attempt(
                    identifier,
                    row["attempts"],
                    dict(status="abandoned", abandoned_at=now, error="lease_expired"),
                )
                await repository.event(
                    identifier, "lease_expired", "recovery", {"attempt": row["attempts"]}
                )
            elif row["available_at"] > now:
                return ClaimResult("deferred")  # Durable outbox will deliver again when eligible.
            if row["attempts"] >= row["max_attempts"]:
                await repository.change_task(
                    identifier,
                    dict(
                        state="failed",
                        lease_token=None,
                        lease_until=None,
                        finished_at=now,
                        last_error="attempts_exhausted_after_crash",
                    ),
                )
                await repository.event(
                    identifier, "failed", "recovery", {"reason": "attempts_exhausted_after_crash"}
                )
                return ClaimResult("terminal")
            number, token = int(row["attempts"]) + 1, uuid4().hex
            lease = now + timedelta(seconds=self.policy.lease_seconds)
            await repository.change_task(
                identifier,
                dict(
                    state="running",
                    attempts=number,
                    lease_token=token,
                    lease_until=lease,
                    last_error=None,
                ),
            )
            await repository.change_outbox(identifier, dict(next_publish_at=lease))
            await repository.start_attempt(
                dict(
                    task_id=identifier,
                    number=number,
                    worker_id=self.worker_id,
                    status="running",
                    started_at=now,
                    timeout_seconds=self.policy.timeout_seconds,
                    lease_seconds=self.policy.lease_seconds,
                )
            )
            await repository.event(
                identifier,
                "claimed",
                "worker",
                {
                    "attempt": number,
                    "worker_id": self.worker_id,
                    "timeout_seconds": self.policy.timeout_seconds,
                    "lease_seconds": self.policy.lease_seconds,
                },
            )
            return ClaimResult(
                "claimed", Claim(identifier, token, number, row["order_id"], row["fault_plan"])
            )

    async def handler(self, claim: Claim) -> dict[str, Any]:
        plan = claim.fault_plan or {}
        if plan.get("delay_ms", 0):
            await asyncio.sleep(plan["delay_ms"] / 1000)
        if claim.number <= plan.get("fail_first_attempts", 0):
            raise ControlledFailure()
        async with self.transaction() as repository:
            order = await repository.order(claim.order_id)
            if (
                order is None
                or order["scenario_id"] != self.scenario.hex
                or order["status"] != "paid"
            ):
                raise InvalidReceiptOrder()
            return {
                key: str(order[key]) if key in ("total", "unit_price") else order[key]
                for key in (
                    "id",
                    "scenario_id",
                    "user_id",
                    "quantity",
                    "unit_price",
                    "total",
                    "status",
                )
            }

    async def finalize(
        self, claim: Claim, snapshot: dict[str, Any] | None, error: str | None, handler_ms: float
    ) -> bool:
        try:
            async with self.transaction() as repository:
                row = await repository.task(claim.task_id, locked=True)
                now = await repository.now()
                if (
                    not self.in_scope(row)
                    or row is None
                    or row["state"] != "running"
                    or row["lease_token"] != claim.token
                    or row["lease_until"] <= now
                ):
                    return False
                values: dict[str, Any] = dict(lease_token=None, lease_until=None)
                if error is None:
                    order = await repository.order(claim.order_id)
                    if order is None or snapshot is None:
                        raise InvalidReceiptOrder()
                    receipt_id = await repository.materialize_receipt(order, snapshot)
                    values.update(
                        state="succeeded",
                        result_receipt_id=receipt_id,
                        finished_at=NOW,
                        last_error=None,
                    )
                    status = "succeeded"
                else:
                    terminal = claim.number >= row["max_attempts"] or error == "invalid_paid_order"
                    status = "timeout" if error == "handler_timeout" else "failed"
                    due = now + timedelta(seconds=min(2, 0.2 * 2 ** (claim.number - 1)))
                    values.update(
                        state="failed" if terminal else "retry_wait",
                        last_error=error,
                        available_at=due,
                        finished_at=NOW if terminal else None,
                    )
                    await repository.change_outbox(claim.task_id, dict(next_publish_at=due))
                if await repository.change_task(claim.task_id, values, claim.token) != 1:
                    raise FenceLost()
                await repository.finish_attempt(
                    claim.task_id,
                    claim.number,
                    dict(status=status, finished_at=NOW, handler_ms=handler_ms, error=error),
                )
                await repository.event(
                    claim.task_id,
                    values["state"],
                    "worker",
                    {"attempt": claim.number, "error": error, "handler_ms": handler_ms},
                )
            return True  # Commit completed before caller may ACK.
        except FenceLost:
            return False

    async def execute(self, claim: Claim) -> bool:
        started = time.perf_counter()
        snapshot, error = None, None
        try:
            async with asyncio.timeout(self.policy.timeout_seconds):
                snapshot = await self.handler(claim)
        except TimeoutError:
            error = "handler_timeout"
        except ControlledFailure:
            error = "controlled_failure"
        except InvalidReceiptOrder:
            error = "invalid_paid_order"
        except SQLAlchemyError:
            error = "handler_database_unavailable"
        duration = (time.perf_counter() - started) * 1000
        # Finalization errors leave a recoverable lease. Unknown commit is not proven failure.
        return await self.finalize(claim, snapshot, error, duration)

    async def observe_ack(self, identifier: str, message_id: str, outcome: str) -> None:
        async with self.transaction() as repository:
            row = await repository.task(identifier, locked=True)
            if self.in_scope(row):
                await repository.event(
                    identifier,
                    "ack_observed",
                    "redis",
                    {"message_id": message_id, "outcome": outcome},
                )


class ControlledFailure(Exception):
    """Explicit lab configuration actually raised during handler execution."""


class InvalidReceiptOrder(Exception):
    """The fixed handler only accepts a paid order in its scenario."""
