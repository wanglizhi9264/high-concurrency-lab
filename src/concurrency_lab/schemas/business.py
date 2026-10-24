"""Business results and actual observations, distinct from health/teaching DTOs."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import Field, JsonValue, model_validator

from concurrency_lab.schemas.visualization import DTO

MAX_ID = 9223372036854775807


class PageParameters(DTO):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=100000)
    before_time: datetime | None = None
    before_id: int | None = Field(default=None, ge=1, le=MAX_ID)

    @model_validator(mode="after")
    def validate_cursor(self) -> Self:
        if (self.before_time is None) != (self.before_id is None):
            raise ValueError("Cursor time and id must be provided together")
        if self.before_time is not None:
            if self.offset:
                raise ValueError("Cursor and offset are mutually exclusive")
            if self.before_time.tzinfo is not None:
                self.before_time = self.before_time.astimezone(UTC).replace(tzinfo=None)
        return self


class ProductDTO(DTO):
    id: int
    sku: str
    name: str
    price: Decimal


class OrderDTO(DTO):
    id: int
    user_id: int
    created_at: datetime
    total: Decimal
    status: str


class ItemDTO(DTO):
    id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal


class CursorDTO(DTO):
    before_time: datetime
    before_id: int


class OrderPageDTO(DTO):
    items: list[OrderDTO]
    next_cursor: CursorDTO | None = None


class OrderDetailDTO(OrderDTO):
    items: list[ItemDTO]


class MeasuredSpan(DTO):
    id: str
    parent_id: str | None
    name: str
    kind: str
    source: str
    start_ms: float = Field(ge=0)
    duration_ms: float = Field(default=0, ge=0)
    state: Literal["success", "error", "timeout", "cancelled"] = "success"
    sql: str | None = None
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    result_count: int | None = None


class BusinessTrace(DTO):
    request_id: str
    evidence: Literal["measured"] = "measured"
    observed_at: str
    unit: Literal["ms"] = "ms"
    environment: dict[str, str]
    service_elapsed_ms: float
    database: str
    spans: list[MeasuredSpan]
    pool_before: dict[str, int]
    pool_after: dict[str, int]
    pool_before_offset_ms: float | None = None
    pool_after_offset_ms: float | None = None
    definitions: dict[str, str]


class BusinessErrorDTO(DTO):
    code: str
    message: str


class BusinessResponse(DTO):
    data: ProductDTO | OrderPageDTO | OrderDetailDTO | None = None
    error: BusinessErrorDTO | None = None
    trace: BusinessTrace
