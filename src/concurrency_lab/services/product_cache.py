"""Product Cache-Aside policy. MySQL reads retain their existing transaction owner."""

import asyncio
import secrets
from datetime import UTC, datetime
from typing import cast

from redis.asyncio import Redis

from concurrency_lab.cache.products import CacheUnavailable, ProductCache
from concurrency_lab.core.exceptions import BusinessFailure, FailureCode
from concurrency_lab.domain.cache import CacheTtl
from concurrency_lab.schemas.business import PageParameters, ProductDTO
from concurrency_lab.schemas.cache import CacheObservation
from concurrency_lab.services.business_service import BusinessService, QueryOperation

SOURCE = "src/concurrency_lab/services/product_cache.py"
COORDINATION_SECONDS = 0.25
POLL_SECONDS = 0.025


class ProductCacheService:
    def __init__(self, business: BusinessService, redis: Redis, product_id: int) -> None:
        self.business = business
        self.observation = business.observation
        self.product_id = product_id
        self.cache = ProductCache(redis, self.observation, product_id)
        self.metadata = CacheObservation(
            observed_at=datetime.now(UTC).isoformat(), outcome="miss", key=self.cache.keys.value
        )

    def _degraded(self, failure: CacheUnavailable) -> None:
        self.metadata.outcome = "degraded"
        self.metadata.redis_available = str(failure) != "redis_unavailable"
        self.metadata.reason = str(failure)
        if self.metadata.initial_lookup == "skipped":
            self.metadata.initial_lookup = "unknown"

    async def _mysql(self) -> ProductDTO:
        self.metadata.served_from = "mysql"
        return cast(
            ProductDTO,
            await self.business.execute_read(
                QueryOperation.PRODUCT, self.product_id, PageParameters()
            ),
        )

    async def _wait_for_fill(self) -> ProductDTO | None:
        with self.observation.span(
            "Bounded cache fill coordination", "cache_coordination", SOURCE
        ) as span:
            try:
                async with asyncio.timeout(COORDINATION_SECONDS):
                    while True:
                        await asyncio.sleep(POLL_SECONDS)
                        lookup = await self.cache.lookup()
                        if lookup.product is not None:
                            self.metadata.generation = lookup.generation
                            self.metadata.outcome = "coalesced"
                            self.metadata.served_from = "redis"
                            return lookup.product
            except TimeoutError:
                span.state = "timeout"
        self.metadata.reason = "coordination_deadline"
        return None

    async def _owned_fill(self, token: str, generation: int, ttl_seconds: int) -> ProductDTO:
        try:
            lookup = await self.cache.lookup()
            if lookup.product is not None:
                self.metadata.outcome = "coalesced"
                self.metadata.served_from = "redis"
                return lookup.product
            product = await self._mysql()
            ttl = CacheTtl(ttl_seconds)
            ttl_ms = ttl.expiration_ms(secrets.randbelow(ttl.jitter_limit_ms + 1))
            try:
                self.metadata.fill_published = await self.cache.publish(
                    product, generation, token, ttl_ms
                )
                if not self.metadata.fill_published:
                    self.metadata.reason = "generation_or_lease_changed"
            except CacheUnavailable as failure:
                self._degraded(failure)
            # A failed cache publication never repeats an already completed SQL read.
            return product
        finally:
            try:
                await self.cache.release(token)
            except CacheUnavailable as failure:
                self._degraded(failure)  # Lease TTL is the bounded cancellation/failure backstop.

    async def read(self, bypass: bool, ttl_seconds: int) -> ProductDTO:
        if not 1 <= ttl_seconds <= 60:
            raise BusinessFailure(FailureCode.INVALID)
        try:
            async with asyncio.timeout(self.business.budget):
                with self.observation.span("Product Cache-Aside", "service", SOURCE):
                    if bypass:
                        self.metadata.outcome = "bypass"
                        return await self._mysql()
                    try:
                        lookup = await self.cache.lookup()
                        self.metadata.redis_available = True
                        self.metadata.generation = lookup.generation
                        self.metadata.initial_lookup = "hit" if lookup.product else "miss"
                        if lookup.product is not None:
                            self.metadata.outcome = "hit"
                            self.metadata.served_from = "redis"
                            return lookup.product
                        if lookup.invalid:
                            self.metadata.reason = "invalid_entry"
                        token = secrets.token_hex(16)
                        generation = await self.cache.acquire(token)
                        if generation is not None:
                            self.metadata.generation = generation
                            return await self._owned_fill(token, generation, ttl_seconds)
                        product = await self._wait_for_fill()
                        if product is not None:
                            return product
                    except CacheUnavailable as failure:
                        self._degraded(failure)
                    return await self._mysql()  # Unleased fallback never publishes cache data.
        except TimeoutError as failure:
            raise BusinessFailure(FailureCode.BUDGET) from failure
        finally:
            self.metadata.observed_at = datetime.now(UTC).isoformat()

    async def inspect(self) -> None:
        self.metadata.outcome = "inspected"
        try:
            generation, ttl, memory = await self.cache.inspect()
            self.metadata.generation = generation
            self.metadata.ttl_ms = ttl
            self.metadata.memory_bytes = memory
            self.metadata.redis_available = True
        except CacheUnavailable as failure:
            self._degraded(failure)
        self.metadata.observed_at = datetime.now(UTC).isoformat()

    async def invalidate(self) -> None:
        try:
            self.metadata.generation = await self.cache.invalidate()
            self.metadata.outcome = "invalidated"
            self.metadata.redis_available = True
        except CacheUnavailable as failure:
            self._degraded(failure)
        self.metadata.observed_at = datetime.now(UTC).isoformat()
