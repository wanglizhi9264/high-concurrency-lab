"""Write intent, persisted inventory and actual audit responses."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field

from concurrency_lab.domain.inventory import OrderState
from concurrency_lab.schemas.business import MAX_ID, BusinessErrorDTO, BusinessTrace
from concurrency_lab.schemas.observations import CollectionTimestamp
from concurrency_lab.schemas.visualization import DTO


class ScenarioInput(DTO):
    scenario_id: UUID
    product_id: int = Field(ge=1, le=1000)
    initial: int = Field(ge=0, le=10000)


class OrderInput(DTO):
    scenario_id: UUID
    user_id: int = Field(ge=1, le=MAX_ID)
    quantity: int = Field(ge=1, le=100)


class TransitionInput(DTO):
    target: Literal[OrderState.PAID, OrderState.CANCELLED]


class ScenarioDTO(DTO):
    id: UUID
    product_id: int
    initial: int
    available: int
    reserved: int
    sold: int
    created_at: datetime


class PurchaseOrderDTO(DTO):
    id: int
    scenario_id: UUID
    user_id: int
    idempotency_key: UUID
    quantity: int
    unit_price: Decimal
    total: Decimal
    status: OrderState
    created_at: datetime
    updated_at: datetime


class ScenarioResult(DTO):
    scenario: ScenarioDTO
    replayed: bool = False


class OrderResult(DTO):
    order: PurchaseOrderDTO
    replayed: bool = False
    applied: bool = False


class InventoryAudit(DTO):
    scenario: ScenarioDTO
    observed_at: CollectionTimestamp
    order_units: dict[str, int]
    order_counts: dict[str, int]
    checks: dict[str, bool]
    all_pass: bool


class InventoryResponse(DTO):
    data: ScenarioResult | OrderResult | InventoryAudit | None = None
    error: BusinessErrorDTO | None = None
    trace: BusinessTrace
