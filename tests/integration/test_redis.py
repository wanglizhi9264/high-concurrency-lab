from concurrency_lab.cache.client import create_redis
from concurrency_lab.core.config import Settings


async def test_redis_ping():
    client = create_redis(Settings())
    try:
        assert await client.ping()
    finally:
        await client.aclose()
