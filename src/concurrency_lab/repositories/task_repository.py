"""Fixed task SQL, explicit lock order is chosen by workflows, no implicit ORM cache."""

from datetime import datetime
from typing import Any, cast

from sqlalchemy import RowMapping, func, insert, select, update
from sqlalchemy.dialects.mysql import insert as mysql_insert

from concurrency_lab.db.business import ObservedDatabase
from concurrency_lab.models.inventory import InventoryScenario, PurchaseOrder
from concurrency_lab.models.tasks import (
    DurableTask,
    OrderReceipt,
    TaskAttempt,
    TaskEvent,
    TaskOutbox,
)

SOURCE = "src/concurrency_lab/repositories/task_repository.py"
NOW = func.utc_timestamp(6)


class TaskRepository:
    def __init__(self, database: ObservedDatabase) -> None:
        self.database = database

    async def now(self) -> datetime:
        rows = await self.database.fetch_rows(select(NOW.label("now")), SOURCE)
        return cast(datetime, rows[0]["now"])

    async def task(self, identifier: str, locked: bool = False) -> RowMapping | None:
        statement = select(DurableTask.__table__).where(DurableTask.id == identifier)
        if locked:
            statement = statement.with_for_update()
        rows = await self.database.fetch_rows(statement, SOURCE)
        return rows[0] if rows else None

    async def outbox(self, identifier: str, locked: bool = False) -> RowMapping:
        statement = select(TaskOutbox.__table__).where(TaskOutbox.task_id == identifier)
        if locked:
            statement = statement.with_for_update()
        return (await self.database.fetch_rows(statement, SOURCE))[0]

    async def order(self, identifier: int) -> RowMapping | None:
        rows = await self.database.fetch_rows(
            select(PurchaseOrder.__table__).where(PurchaseOrder.id == identifier), SOURCE
        )
        return rows[0] if rows else None

    async def scenario_exists(self, scope: str) -> bool:
        return bool(
            await self.database.fetch_rows(
                select(InventoryScenario.id).where(InventoryScenario.id == scope), SOURCE
            )
        )

    async def create(self, values: dict[str, Any]) -> None:
        await self.database.execute_change(insert(DurableTask).values(**values), SOURCE)
        await self.database.execute_change(
            insert(TaskOutbox).values(task_id=values["id"], next_publish_at=NOW, publish_count=0),
            SOURCE,
        )
        await self.event(values["id"], "created", "api", {})

    async def event(self, identifier: str, kind: str, source: str, details: dict[str, Any]) -> None:
        await self.database.execute_change(
            insert(TaskEvent).values(
                task_id=identifier, occurred_at=NOW, kind=kind, source=source, details=details
            ),
            SOURCE,
        )

    async def list_tasks(self, scope: str, limit: int) -> list[RowMapping]:
        return await self.database.fetch_rows(
            select(DurableTask.__table__)
            .where(DurableTask.scenario_id == scope)
            .order_by(DurableTask.created_at.desc(), DurableTask.id.desc())
            .limit(limit),
            SOURCE,
        )

    async def counts(self, scope: str) -> dict[str, int]:
        rows = await self.database.fetch_rows(
            select(DurableTask.state, func.count().label("count"))
            .where(DurableTask.scenario_id == scope)
            .group_by(DurableTask.state),
            SOURCE,
        )
        return {row["state"]: int(row["count"]) for row in rows}

    async def attempts(self, identifier: str) -> list[RowMapping]:
        return await self.database.fetch_rows(
            select(TaskAttempt.__table__)
            .where(TaskAttempt.task_id == identifier)
            .order_by(TaskAttempt.number)
            .limit(5),
            SOURCE,
        )

    async def events(self, identifier: str) -> list[RowMapping]:
        return await self.database.fetch_rows(
            select(TaskEvent.__table__)
            .where(TaskEvent.task_id == identifier)
            .order_by(TaskEvent.id.desc())
            .limit(101),
            SOURCE,
        )

    async def receipt(self, identifier: int) -> RowMapping | None:
        rows = await self.database.fetch_rows(
            select(OrderReceipt.__table__).where(OrderReceipt.id == identifier), SOURCE
        )
        return rows[0] if rows else None

    async def candidates(self, scope: str) -> list[str]:
        rows = await self.database.fetch_rows(
            select(DurableTask.id)
            .join(TaskOutbox, TaskOutbox.task_id == DurableTask.id)
            .where(
                DurableTask.scenario_id == scope,
                TaskOutbox.next_publish_at <= NOW,
                (
                    (DurableTask.state.in_(["queued", "retry_wait"]))
                    & (DurableTask.available_at <= NOW)
                )
                | ((DurableTask.state == "running") & (DurableTask.lease_until <= NOW)),
            )
            .order_by(TaskOutbox.next_publish_at, DurableTask.id)
            .limit(5),
            SOURCE,
        )
        return [row["id"] for row in rows]

    async def change_task(
        self, identifier: str, values: dict[str, Any], token: str | None = None
    ) -> int:
        statement = update(DurableTask).where(DurableTask.id == identifier)
        if token is not None:
            statement = statement.where(
                DurableTask.state == "running",
                DurableTask.lease_token == token,
                DurableTask.lease_until > NOW,
            )
        result = await self.database.execute_change(
            statement.values(**values, updated_at=NOW), SOURCE
        )
        return result.affected_rows

    async def change_outbox(self, identifier: str, values: dict[str, Any]) -> None:
        await self.database.execute_change(
            update(TaskOutbox).where(TaskOutbox.task_id == identifier).values(**values), SOURCE
        )

    async def start_attempt(self, values: dict[str, Any]) -> None:
        await self.database.execute_change(insert(TaskAttempt).values(**values), SOURCE)

    async def finish_attempt(self, identifier: str, number: int, values: dict[str, Any]) -> None:
        await self.database.execute_change(
            update(TaskAttempt)
            .where(
                TaskAttempt.task_id == identifier,
                TaskAttempt.number == number,
                TaskAttempt.status == "running",
            )
            .values(**values),
            SOURCE,
        )

    async def materialize_receipt(self, order: RowMapping, snapshot: dict[str, Any]) -> int:
        statement = mysql_insert(OrderReceipt).values(
            order_id=order["id"], total=order["total"], snapshot=snapshot, created_at=NOW
        )
        await self.database.execute_change(
            statement.on_duplicate_key_update(id=OrderReceipt.id), SOURCE
        )
        rows = await self.database.fetch_rows(
            select(OrderReceipt.id).where(OrderReceipt.order_id == order["id"]).with_for_update(),
            SOURCE,
        )
        return int(rows[0]["id"])
