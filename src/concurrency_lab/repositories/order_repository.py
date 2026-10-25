"""Bounded orders and a fixed detail JOIN; no lazy relationships or N+1."""

from sqlalchemy import RowMapping, and_, or_, select

from concurrency_lab.db.business import ObservedDatabase
from concurrency_lab.models.commerce import LabOrder, LabOrderItem, LabProduct
from concurrency_lab.schemas.business import PageParameters

SOURCE = "src/concurrency_lab/repositories/order_repository.py"


class OrderRepository:
    def __init__(self, database: ObservedDatabase) -> None:
        self.database = database

    async def list_orders(
        self, user_id: int | None, page: PageParameters, time_ordered: bool
    ) -> list[RowMapping]:
        statement = select(LabOrder.__table__)
        if user_id is not None:
            statement = statement.where(LabOrder.user_id == user_id)
        if time_ordered:
            if page.before_time is not None:
                statement = statement.where(
                    or_(
                        LabOrder.created_at < page.before_time,
                        and_(LabOrder.created_at == page.before_time, LabOrder.id < page.before_id),
                    )
                )
            statement = statement.order_by(LabOrder.created_at.desc(), LabOrder.id.desc())
        else:
            statement = statement.order_by(LabOrder.id)
        # One look-ahead row proves whether a following page exists; it is not returned to users.
        statement = statement.limit(page.limit + 1).offset(page.offset)
        with self.database.observation.span("OrderRepository.list_orders", "repository", SOURCE):
            return await self.database.fetch_rows(statement, SOURCE)

    async def get_order_by_id(self, order_id: int) -> RowMapping | None:
        with self.database.observation.span(
            "OrderRepository.get_order_by_id", "repository", SOURCE
        ):
            rows = await self.database.fetch_rows(
                select(LabOrder.__table__).where(LabOrder.id == order_id), SOURCE
            )
            return rows[0] if rows else None

    async def get_order_items(self, order_id: int) -> list[RowMapping]:
        statement = (
            select(
                LabOrderItem.id,
                LabOrderItem.product_id,
                LabProduct.name.label("product_name"),
                LabOrderItem.quantity,
                LabOrderItem.unit_price,
            )
            .join(LabProduct, LabProduct.id == LabOrderItem.product_id)
            .where(LabOrderItem.order_id == order_id)
            .order_by(LabOrderItem.id)
            .limit(101)
        )
        with self.database.observation.span(
            "OrderRepository.get_order_items JOIN product", "repository", SOURCE
        ):
            return await self.database.fetch_rows(statement, SOURCE)
