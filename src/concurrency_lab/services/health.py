import asyncio
from collections.abc import Awaitable, Callable
from typing import cast

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def mysql_ping(engine: AsyncEngine) -> bool:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return True


async def redis_ping(client: Redis) -> bool:
    return bool(await cast(Awaitable[bool], client.ping()))


async def bounded_check(check: Callable[[], Awaitable[bool]], budget: float) -> bool:
    try:
        async with asyncio.timeout(budget):
            return await check()
    except Exception:
        # The public probe deliberately excludes exception messages and credentials.
        return False


async def readiness(
    engine: AsyncEngine,
    client: Redis,
    budget: float,
    on_event: Callable[[str, str], None] | None = None,
) -> dict[str, str]:
    async def observed(name: str, check: Callable[[], Awaitable[bool]]) -> bool:
        if on_event:
            on_event(name, "running")
        result = await bounded_check(check, budget)
        if on_event:
            on_event(name, "success" if result else "failure")
        return result

    mysql, redis = await asyncio.gather(
        observed("mysql", lambda: mysql_ping(engine)),
        observed("redis", lambda: redis_ping(client)),
    )
    return {"mysql": "ok" if mysql else "unavailable", "redis": "ok" if redis else "unavailable"}
