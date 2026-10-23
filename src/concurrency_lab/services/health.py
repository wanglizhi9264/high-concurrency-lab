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


async def readiness(engine: AsyncEngine, client: Redis, budget: float) -> dict[str, str]:
    mysql, redis = await asyncio.gather(
        bounded_check(lambda: mysql_ping(engine), budget),
        bounded_check(lambda: redis_ping(client), budget),
    )
    return {"mysql": "ok" if mysql else "unavailable", "redis": "ok" if redis else "unavailable"}
