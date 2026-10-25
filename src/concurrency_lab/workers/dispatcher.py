"""Transactional outbox publication plus durable reconciliation of transient transport."""

from datetime import timedelta

from concurrency_lab.cache.task_stream import TaskStream
from concurrency_lab.domain.tasks import TERMINAL
from concurrency_lab.services.task_execution import TaskExecution


class Dispatcher:
    def __init__(self, execution: TaskExecution, stream: TaskStream) -> None:
        self.execution, self.stream = execution, stream

    async def publish_due(self) -> int:
        async with self.execution.transaction() as repository:
            candidates = await repository.candidates(self.stream.scenario.hex)
        published = 0
        for identifier in candidates:
            async with self.execution.transaction() as repository:
                # Explicit Task→Outbox ordering, independent of optimizer JOIN lock order.
                row = await repository.task(identifier, locked=True)
                if row is None or not self.execution.in_scope(row) or row["state"] in TERMINAL:
                    continue
                outbox = await repository.outbox(identifier, locked=True)
                now = await repository.now()
                if outbox["next_publish_at"] > now:
                    continue
                if row["state"] == "running" and row["lease_until"] > now:
                    continue
                if row["state"] != "running" and row["available_at"] > now:
                    continue
                message_id = await self.stream.publish(identifier)
                await repository.change_outbox(
                    identifier,
                    dict(
                        publish_count=outbox["publish_count"] + 1,
                        last_message_id=message_id,
                        last_published_at=now,
                        next_publish_at=now + timedelta(seconds=5),
                    ),
                )
                await repository.event(
                    identifier, "published", "dispatcher", {"message_id": message_id}
                )
            published += 1
        return published
