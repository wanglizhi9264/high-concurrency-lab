"""Read workflows with one independently owned Session and transaction per call."""

import asyncio
from enum import StrEnum

from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import TimeoutError as PoolTimeout

from concurrency_lab.core.exceptions import BusinessFailure, FailureCode
from concurrency_lab.db.business import BusinessResources, ObservedDatabase, pool_gauges
from concurrency_lab.observability.recording import RequestObservation
from concurrency_lab.repositories.order_repository import OrderRepository
from concurrency_lab.repositories.product_repository import ProductRepository
from concurrency_lab.schemas.business import (
    CursorDTO,
    ItemDTO,
    OrderDetailDTO,
    OrderDTO,
    OrderPageDTO,
    PageParameters,
    ProductDTO,
)

SOURCE = "src/concurrency_lab/services/business_service.py"


class QueryOperation(StrEnum):
    PRODUCT = "product"
    USER_ORDERS = "user_orders"
    ORDER_PAGE = "order_page"
    ORDER_DETAIL = "order_detail"
    GLOBAL_ORDER_PAGE = "global_order_page"


class BusinessService:
    def __init__(
        self, resources: BusinessResources, observation: RequestObservation, budget: float
    ) -> None:
        self.resources = resources
        self.observation = observation
        self.budget = budget

    async def execute_read(
        self, operation: QueryOperation, entity_id: int | None, page: PageParameters
    ) -> ProductDTO | OrderPageDTO | OrderDetailDTO:
        observation = self.observation
        observation.pool_before = pool_gauges(self.resources.engine)
        observation.pool_before_offset_ms = observation.elapsed()
        try:
            async with asyncio.timeout(self.budget):
                with observation.span(f"BusinessService.{operation.value}", "service", SOURCE):
                    async with self.resources.sessions() as session, session.begin():
                        with observation.span(
                            "Acquire business connection",
                            "acquire",
                            "src/concurrency_lab/db/business.py",
                        ):
                            await session.connection()
                        database = ObservedDatabase(session, observation)
                        await database.verify_ownership(observation.database)
                        return await self._query_data(database, operation, entity_id, page)
        except PoolTimeout as exc:
            raise BusinessFailure(FailureCode.POOL) from exc
        except TimeoutError as exc:
            with observation.span(
                "Business request budget exhausted", "request_budget", SOURCE
            ) as span:
                span.state = "timeout"
            raise BusinessFailure(FailureCode.BUDGET) from exc
        except DBAPIError as exc:
            raise BusinessFailure(FailureCode.DATABASE) from exc
        finally:
            observation.pool_after = pool_gauges(self.resources.engine)
            observation.pool_after_offset_ms = observation.elapsed()

    async def _query_data(
        self,
        database: ObservedDatabase,
        operation: QueryOperation,
        entity_id: int | None,
        page: PageParameters,
    ) -> ProductDTO | OrderPageDTO | OrderDetailDTO:
        if operation == QueryOperation.GLOBAL_ORDER_PAGE:
            return await self._read_order_page(database, None, page, True)
        if entity_id is None:
            raise BusinessFailure(FailureCode.INVALID)
        if operation == QueryOperation.PRODUCT:
            row = await ProductRepository(database).get_product_by_id(entity_id)
            if row is None:
                raise BusinessFailure(FailureCode.NOT_FOUND)
            return ProductDTO.model_validate(row)
        orders = OrderRepository(database)
        if operation in (QueryOperation.USER_ORDERS, QueryOperation.ORDER_PAGE):
            time_ordered = operation == QueryOperation.ORDER_PAGE
            return await self._read_order_page(database, entity_id, page, time_ordered)
        row = await orders.get_order_by_id(entity_id)
        if row is None:
            raise BusinessFailure(FailureCode.NOT_FOUND)
        detail_items = await orders.get_order_items(entity_id)
        if len(detail_items) > 100:
            raise BusinessFailure(FailureCode.OWNERSHIP)
        return OrderDetailDTO(
            **dict(row), items=[ItemDTO.model_validate(item) for item in detail_items]
        )

    async def _read_order_page(
        self,
        database: ObservedDatabase,
        user_id: int | None,
        page: PageParameters,
        time_ordered: bool,
    ) -> OrderPageDTO:
        rows = await OrderRepository(database).list_orders(user_id, page, time_ordered)
        items = [OrderDTO.model_validate(row) for row in rows[: page.limit]]
        cursor = (
            CursorDTO(before_time=items[-1].created_at, before_id=items[-1].id)
            if time_ordered and len(rows) > page.limit
            else None
        )
        return OrderPageDTO(items=items, next_cursor=cursor)
