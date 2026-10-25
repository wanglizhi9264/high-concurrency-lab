"""Cache copies and observations, separate from authoritative business records."""

from typing import Literal

from pydantic import Field

from concurrency_lab.schemas.business import BusinessErrorDTO, BusinessTrace, ProductDTO
from concurrency_lab.schemas.observations import CollectionTimestamp
from concurrency_lab.schemas.visualization import DTO


class CacheEntry(DTO):
    schema_version: Literal[1] = 1
    database: str
    generation: int = Field(ge=0)
    product: ProductDTO


class CacheObservation(DTO):
    evidence: Literal["measured"] = "measured"
    observed_at: CollectionTimestamp
    outcome: Literal["bypass", "hit", "miss", "coalesced", "degraded", "inspected", "invalidated"]
    initial_lookup: Literal["hit", "miss", "unknown", "skipped"] = "skipped"
    served_from: Literal["mysql", "redis"] | None = None
    key: str
    generation: int | None = Field(default=None, ge=0)
    redis_available: bool | None = None
    ttl_ms: int | None = Field(default=None, ge=-2)
    memory_bytes: int | None = Field(default=None, ge=0)
    fill_published: bool | None = None
    reason: str | None = None
    source: str = "src/concurrency_lab/services/product_cache.py"


class CacheResponse(DTO):
    data: ProductDTO | None = None
    error: BusinessErrorDTO | None = None
    cache: CacheObservation
    trace: BusinessTrace
