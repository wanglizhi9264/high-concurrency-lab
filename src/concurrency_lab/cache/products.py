"""Fixed, bounded Redis operations. No SQL, HTTP, key scans or arbitrary scripts."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, cast

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from concurrency_lab.db.business import validate_business_database
from concurrency_lab.observability.recording import RequestObservation
from concurrency_lab.schemas.business import ProductDTO
from concurrency_lab.schemas.cache import CacheEntry

SOURCE = "src/concurrency_lab/cache/products.py"
COMMAND_BUDGET_SECONDS = 0.25
LEASE_MS = 1000
ACQUIRE = """
if redis.call('SET', KEYS[1], ARGV[1], 'NX', 'PX', ARGV[2]) then
    return redis.call('GET', KEYS[2]) or '0'
end
return false
"""
PUBLISH = """
if redis.call('GET', KEYS[1]) == ARGV[1]
   and (redis.call('GET', KEYS[2]) or '0') == ARGV[2] then
    redis.call('SET', KEYS[3], ARGV[3], 'PX', ARGV[4])
    return 1
end
return 0
"""
RELEASE = """
if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end
return 0
"""
INVALIDATE = """
local generation = redis.call('INCR', KEYS[1])
redis.call('DEL', KEYS[2], KEYS[3])
return generation
"""
INSPECT = """
return {redis.call('GET', KEYS[1]) or '0', redis.call('PTTL', KEYS[2]),
        redis.call('MEMORY', 'USAGE', KEYS[2]) or false}
"""


class CacheUnavailable(Exception):
    """Safe cache classification; the original infrastructure message stays private."""


def _generation(value: Any) -> int:
    try:
        result = int(value or 0)
        if result < 0:
            raise ValueError("Negative generation")
        return result
    except (ValueError, TypeError) as error:
        raise CacheUnavailable("invalid_generation") from error


@dataclass(frozen=True)
class CacheKeys:
    value: str
    generation: str
    lease: str


def product_keys(database: str, product_id: int) -> CacheKeys:
    validate_business_database(database)
    if not 1 <= product_id <= 1000:
        raise ValueError("Cache product identifier outside experiment bounds")
    prefix = f"hcl:cache:v1:{{{database}}}:product:{product_id}"
    return CacheKeys(f"{prefix}:value", f"{prefix}:generation", f"{prefix}:lease")


@dataclass(frozen=True)
class CacheLookup:
    generation: int
    product: ProductDTO | None
    invalid: bool = False


class ProductCache:
    def __init__(self, redis: Redis, observation: RequestObservation, product_id: int) -> None:
        self.redis = redis
        self.observation = observation
        self.product_id = product_id
        self.keys = product_keys(observation.database, product_id)

    async def _command(
        self, name: str, keys: list[str], execute: Callable[[], Awaitable[Any]]
    ) -> Any:
        try:
            with self.observation.span(name, "redis_command", SOURCE) as span:
                span.parameters = {f"key_{index}": key for index, key in enumerate(keys, 1)}
                async with asyncio.timeout(COMMAND_BUDGET_SECONDS):
                    return await execute()
        except (RedisError, TimeoutError) as error:
            raise CacheUnavailable("redis_unavailable") from error

    async def _script(self, script: str, keys: list[str], *arguments: str | int) -> Any:
        # redis-py shares EVAL stubs with sync clients; this adapter owns only asyncio.Redis.
        return await cast(Awaitable[Any], self.redis.eval(script, len(keys), *keys, *arguments))

    async def lookup(self) -> CacheLookup:
        generation, raw = await self._command(
            "MGET generation/value",
            [self.keys.generation, self.keys.value],
            lambda: self.redis.mget([self.keys.generation, self.keys.value]),
        )
        current = _generation(generation)
        if raw is None:
            return CacheLookup(current, None)
        try:
            entry = CacheEntry.model_validate_json(raw)
            if (
                entry.database != self.observation.database
                or entry.product.id != self.product_id
                or entry.generation != current
            ):
                raise ValueError("Cache identity mismatch")
            return CacheLookup(current, entry.product)
        except (ValidationError, ValueError):
            with self.observation.span(
                "Reject invalid cache entry", "cache_validation", SOURCE
            ) as span:
                span.state = "error"
            return CacheLookup(current, None, invalid=True)

    async def acquire(self, token: str, lease_ms: int = LEASE_MS) -> int | None:
        result = await self._command(
            "EVAL acquire token lease and generation",
            [self.keys.lease, self.keys.generation],
            lambda: self._script(ACQUIRE, [self.keys.lease, self.keys.generation], token, lease_ms),
        )
        return _generation(result) if result is not None else None

    async def publish(self, product: ProductDTO, generation: int, token: str, ttl_ms: int) -> bool:
        entry = CacheEntry(
            database=self.observation.database, generation=generation, product=product
        )
        result = await self._command(
            "EVAL publish only current generation and lease owner",
            [self.keys.lease, self.keys.generation, self.keys.value],
            lambda: self._script(
                PUBLISH,
                [self.keys.lease, self.keys.generation, self.keys.value],
                token,
                str(generation),
                entry.model_dump_json(),
                ttl_ms,
            ),
        )
        with self.observation.span(
            "Cache fill accepted" if result else "Cache fill fenced out", "cache_fence", SOURCE
        ) as span:
            span.parameters = {"published": bool(result), "generation": generation}
        return bool(result)

    async def release(self, token: str) -> None:
        await self._command(
            "EVAL release only matching token",
            [self.keys.lease],
            lambda: self._script(RELEASE, [self.keys.lease], token),
        )

    async def invalidate(self) -> int:
        return int(
            await self._command(
                "EVAL advance generation and invalidate value/lease",
                [self.keys.generation, self.keys.value, self.keys.lease],
                lambda: self._script(
                    INVALIDATE, [self.keys.generation, self.keys.value, self.keys.lease]
                ),
            )
        )

    async def inspect(self) -> tuple[int, int, int | None]:
        generation, ttl, memory = await self._command(
            "EVAL inspect generation/PTTL/MEMORY USAGE",
            [self.keys.generation, self.keys.value],
            lambda: self._script(INSPECT, [self.keys.generation, self.keys.value]),
        )
        return _generation(generation), int(ttl), int(memory) if memory is not None else None
