from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from concurrency_lab.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,
        connect_args={"connect_timeout": settings.io_timeout},
    )


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One session per request. Callers use session.begin() for writes."""
    async with request.app.state.resources.sessions() as session:
        yield session
