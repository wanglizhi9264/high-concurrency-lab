from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from concurrency_lab.api.routes.health import router
from concurrency_lab.api.routes.visualization import router as visualization_router
from concurrency_lab.cache.client import create_redis
from concurrency_lab.core.config import Settings
from concurrency_lab.db.session import create_engine
from concurrency_lab.services.tracing import TraceRecorder


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
            startup = TraceRecorder()
            startup.emit("Lifespan entered", "router", "running", "应用资源初始化开始。")
            engine = create_engine(config)
            startup.emit(
                "Engine created (lazy)", "pool", "success", "创建池对象，不代表远端连接已建立。"
            )
            stack.push_async_callback(engine.dispose)
            client = create_redis(config)
            startup.emit(
                "Redis client created (lazy)", "redis", "success", "创建客户端，不代表已执行PING。"
            )
            stack.push_async_callback(client.aclose)
            app.state.resources = Resources(
                config,
                engine,
                client,
                async_sessionmaker(engine, expire_on_commit=False),
            )
            startup.emit(
                "Session factory registered",
                "session",
                "success",
                "注册工厂；没有启动事务或自动建表。",
            )
            app.state.startup_trace = startup.events
            yield

    application = FastAPI(title="High Concurrency Lab", lifespan=lifespan)
    application.include_router(router)
    application.include_router(visualization_router)
    return application


app = create_app()
