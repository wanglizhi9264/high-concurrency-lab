"""One bounded dispatch/consume cycle. DB disposition precedes broker ACK."""

import os
from uuid import UUID, uuid4

from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from concurrency_lab.cache.task_stream import TaskStream
from concurrency_lab.db.business import BusinessResources
from concurrency_lab.domain.tasks import WorkerPolicy
from concurrency_lab.services.task_execution import TaskExecution
from concurrency_lab.workers.dispatcher import Dispatcher


class WorkerRuntime:
    def __init__(
        self,
        resources: BusinessResources,
        stream: TaskStream,
        policy: WorkerPolicy,
        crash_after_claim: bool = False,
    ) -> None:
        self.stream, self.policy = stream, policy
        self.worker_id = f"receipt-{uuid4().hex}"
        self.execution = TaskExecution(
            resources, stream.database, stream.scenario, policy, self.worker_id
        )
        self.dispatcher = Dispatcher(self.execution, stream)
        self.crash_after_claim = crash_after_claim

    async def consume(self) -> str:
        delivery = await self.stream.receive(self.worker_id, int(self.policy.lease_seconds * 1000))
        if delivery is None:
            return "idle"
        message_id, fields = delivery
        try:
            identifier = UUID(fields["task_id"]).hex
        except (KeyError, ValueError, AttributeError):
            await self.stream.acknowledge(message_id)
            return "invalid_message"
        result = await self.execution.claim(identifier)
        safe_ack = result.disposition in ("terminal", "deferred", "invalid")
        if result.claim is not None:
            if self.crash_after_claim:
                print(
                    f'{{"probe":"crash_after_committed_claim","task_id":"{identifier}","exit_code":70}}',
                    flush=True,
                )
                os._exit(70)  # Explicit CLI-only experiment, current child process only.
            safe_ack = await self.execution.execute(result.claim)
        if safe_ack:
            try:
                acknowledged = await self.stream.acknowledge(message_id)
                outcome = "acknowledged" if acknowledged else "not_pending"
            except (RedisError, TimeoutError):
                outcome = "unconfirmed"
            try:
                await self.execution.observe_ack(identifier, message_id, outcome)
            except (SQLAlchemyError, TimeoutError):
                pass  # Missing observation cannot prove absence of an actual ACK.
        return result.disposition

    async def cycle(self, role: str = "both") -> str:
        if role not in ("both", "dispatcher", "consumer"):
            raise ValueError("Unsupported worker role")
        if role in ("both", "dispatcher"):
            await self.dispatcher.publish_due()
        return await self.consume() if role in ("both", "consumer") else "dispatched"
