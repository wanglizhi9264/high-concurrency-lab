from redis.asyncio import Redis

from concurrency_lab.core.config import Settings


def create_redis(settings: Settings) -> Redis:
    return Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password.get_secret_value(),
        socket_connect_timeout=settings.io_timeout,
        socket_timeout=settings.io_timeout,
        max_connections=settings.redis_max_connections,
        decode_responses=True,
    )
