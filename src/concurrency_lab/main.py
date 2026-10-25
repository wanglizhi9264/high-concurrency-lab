from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from concurrency_lab.api.routes.benchmarks import router as benchmarks_router
from concurrency_lab.api.routes.business import business_error_handler, business_validation_handler
from concurrency_lab.api.routes.business import router as business_router
from concurrency_lab.api.routes.health import router
from concurrency_lab.api.routes.inventory import router as inventory_router
from concurrency_lab.api.routes.product_cache import router as product_cache_router
from concurrency_lab.api.routes.visualization import router as visualization_router
from concurrency_lab.cache.client import create_redis
from concurrency_lab.core.config import Settings
from concurrency_lab.core.exceptions import BusinessFailure
from concurrency_lab.db.business import (
    BusinessResources,
    configure_business_lock_timeout,
    validate_business_database,
)
from concurrency_lab.db.session import create_engine
from concurrency_lab.observability.http import BusinessObservationMiddleware
from concurrency_lab.services.tracing import TraceRecorder


@dataclass
class Resources:
    settings: Settings
    engine: AsyncEngine
    redis: Redis
    sessions: async_sessionmaker[AsyncSession]
    business: BusinessResources | None = None


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
            business = None
            if config.business_enabled:
                validate_business_database(config.business_database)
                business_config = config.model_copy(
                    update={"mysql_database": config.business_database}
                )
                business_engine = create_engine(business_config)
                if config.business_writes_enabled:
                    configure_business_lock_timeout(
                        business_engine, config.business_lock_wait_timeout
                    )
                stack.push_async_callback(business_engine.dispose)
                business = BusinessResources(
                    business_engine, async_sessionmaker(business_engine, expire_on_commit=False)
                )
            app.state.resources = Resources(
                config,
                engine,
                client,
                async_sessionmaker(engine, expire_on_commit=False),
                business,
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
    application.include_router(business_router)
    application.include_router(product_cache_router)
    application.include_router(inventory_router)
    application.include_router(benchmarks_router)
    application.add_exception_handler(BusinessFailure, business_error_handler)
    application.add_exception_handler(RequestValidationError, business_validation_handler)
    application.add_middleware(BusinessObservationMiddleware)
    return application


app = create_app()
