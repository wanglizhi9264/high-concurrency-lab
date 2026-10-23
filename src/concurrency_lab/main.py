from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from concurrency_lab.api.routes.health import router
from concurrency_lab.cache.client import create_redis
from concurrency_lab.core.config import Settings
from concurrency_lab.db.session import create_engine


@dataclass
class Resources:
    settings: Settings
    engine: AsyncEngine
    redis: Redis
    sessions: async_sessionmaker[AsyncSession]


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        config = settings if settings is not None else Settings()
        async with AsyncExitStack() as stack:
            engine = create_engine(config)
            stack.push_async_callback(engine.dispose)
            client = create_redis(config)
            stack.push_async_callback(client.aclose)
            app.state.resources = Resources(
                config,
                engine,
                client,
                async_sessionmaker(engine, expire_on_commit=False),
            )
            yield

    application = FastAPI(title="High Concurrency Lab", lifespan=lifespan)
    application.include_router(router)
    return application


app = create_app()
