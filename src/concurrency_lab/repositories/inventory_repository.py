"""Fixed stock/order SQL. The service owns sessions, transactions and lock ordering."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import RowMapping, func, insert, select, update

from concurrency_lab.db.business import ObservedDatabase
from concurrency_lab.domain.inventory import OrderState
from concurrency_lab.models.commerce import LabProduct
from concurrency_lab.models.inventory import InventoryScenario, PurchaseOrder
from concurrency_lab.schemas.inventory import OrderInput, ScenarioInput

SOURCE = "src/concurrency_lab/repositories/inventory_repository.py"


class InventoryRepository:
    def __init__(self, database: ObservedDatabase) -> None:
        self.database = database

    async def scenario(self, identifier: str, locked: bool = False) -> RowMapping | None:
        statement = select(InventoryScenario.__table__).where(InventoryScenario.id == identifier)
        if locked:
            statement = statement.with_for_update()
        rows = await self.database.fetch_rows(statement, SOURCE)
        return rows[0] if rows else None

    async def create_scenario(self, intent: ScenarioInput, now: datetime) -> None:
        await self.database.execute_change(
            insert(InventoryScenario).values(
                id=intent.scenario_id.hex,
                product_id=intent.product_id,
                initial=intent.initial,
                available=intent.initial,
                reserved=0,
                sold=0,
                created_at=now,
            ),
            SOURCE,
        )

    async def price(self, product_id: int) -> Decimal | None:
        rows = await self.database.fetch_rows(
            select(LabProduct.price).where(LabProduct.id == product_id), SOURCE
        )
        return Decimal(rows[0]["price"]) if rows else None

    async def order(self, identifier: int, locked: bool = False) -> RowMapping | None:
        statement = select(PurchaseOrder.__table__).where(PurchaseOrder.id == identifier)
        if locked:
            statement = statement.with_for_update()
        rows = await self.database.fetch_rows(statement, SOURCE)
        return rows[0] if rows else None

    async def order_by_key(self, key: str) -> RowMapping | None:
        rows = await self.database.fetch_rows(
            select(PurchaseOrder.__table__).where(PurchaseOrder.idempotency_key == key), SOURCE
        )
        return rows[0] if rows else None

    async def create_order(
        self, intent: OrderInput, key: str, fingerprint: str, price: Decimal, now: datetime
    ) -> int | None:
        result = await self.database.execute_change(
            insert(PurchaseOrder).values(
                scenario_id=intent.scenario_id.hex,
                user_id=intent.user_id,
                idempotency_key=key,
                payload_sha256=fingerprint,
                quantity=intent.quantity,
                unit_price=price,
                total=price * intent.quantity,
                status=OrderState.RESERVED,
                created_at=now,
                updated_at=now,
            ),
            SOURCE,
        )
        return result.inserted_id

    async def reserve(self, scenario_id: str, quantity: int) -> int:
        result = await self.database.execute_change(
            update(InventoryScenario)
            .where(InventoryScenario.id == scenario_id, InventoryScenario.available >= quantity)
            .values(
                available=InventoryScenario.available - quantity,
                reserved=InventoryScenario.reserved + quantity,
            ),
            SOURCE,
        )
        return result.affected_rows

    async def settle(self, scenario_id: str, quantity: int, target: OrderState) -> int:
        changes = {"reserved": InventoryScenario.reserved - quantity}
        if target == OrderState.PAID:
            changes["sold"] = InventoryScenario.sold + quantity
        else:
            changes["available"] = InventoryScenario.available + quantity
        result = await self.database.execute_change(
            update(InventoryScenario)
            .where(InventoryScenario.id == scenario_id, InventoryScenario.reserved >= quantity)
            .values(**changes),
            SOURCE,
        )
        return result.affected_rows

    async def change_state(self, identifier: int, target: OrderState, now: datetime) -> int:
        result = await self.database.execute_change(
            update(PurchaseOrder)
            .where(PurchaseOrder.id == identifier, PurchaseOrder.status == OrderState.RESERVED)
            .values(status=target, updated_at=now),
            SOURCE,
        )
        return result.affected_rows

    async def aggregate_orders(self, scenario_id: str) -> list[RowMapping]:
        return await self.database.fetch_rows(
            select(
                PurchaseOrder.status,
                func.count(PurchaseOrder.id).label("orders"),
                func.sum(PurchaseOrder.quantity).label("units"),
            )
            .where(PurchaseOrder.scenario_id == scenario_id)
            .group_by(PurchaseOrder.status),
            SOURCE,
        )
