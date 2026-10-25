"""Bounded live monitoring; acquisition competes with workload and is not hidden."""

import asyncio
import time
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError

from concurrency_lab.core.config import Settings
from concurrency_lab.core.exceptions import BusinessFailure
from concurrency_lab.db.business import BusinessResources, pool_gauges
from concurrency_lab.repositories.metrics_repository import read_business_metrics
from concurrency_lab.schemas.benchmarks import BusinessMetrics


async def collect_business_metrics(
    resources: BusinessResources | None, settings: Settings
) -> BusinessMetrics:
    start = time.perf_counter()
    result = BusinessMetrics(
        observed_at=datetime.now(UTC).isoformat(),
        collection_ms=0,
        status="disabled" if resources is None else "unavailable",
        database=settings.business_database,
        pool=pool_gauges(resources.engine) if resources else {},
        configuration={
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_timeout_seconds": settings.db_pool_timeout,
            "request_timeout_seconds": settings.business_request_timeout,
            "inventory_lock_wait_seconds": (
                settings.business_lock_wait_timeout if settings.business_writes_enabled else None
            ),
        },
    )
    if resources is not None:
        try:
            async with asyncio.timeout(settings.business_request_timeout):
                async with resources.engine.connect() as connection:
                    await read_business_metrics(connection, result)
            result.status = "ok"
        except BusinessFailure as error:
            result.error_code = error.code.value
        except (SQLAlchemyError, TimeoutError):
            result.error_code = "monitor_unavailable"
    result.collection_ms = (time.perf_counter() - start) * 1000
    result.observed_at = datetime.now(UTC).isoformat()
    return result
