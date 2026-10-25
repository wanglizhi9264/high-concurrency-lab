"""Bounded product-cache learning operations; no arbitrary Redis command inputs."""

from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Request

from concurrency_lab.api.routes.business import ServiceDependency
from concurrency_lab.core.exceptions import BusinessFailure, FailureCode
from concurrency_lab.schemas.cache import CacheResponse
from concurrency_lab.services.product_cache import ProductCacheService

router = APIRouter(prefix="/api/v1/business/cache/products", tags=["product-cache"])
ProductIdentifier = Annotated[int, Path(ge=1, le=1000)]
SOURCE = "src/concurrency_lab/api/routes/product_cache.py"


def cache_service(
    request: Request, service: ServiceDependency, identifier: int
) -> ProductCacheService:
    if service is None:
        raise BusinessFailure(FailureCode.DISABLED)
    return ProductCacheService(service, request.app.state.resources.redis, identifier)


@router.get("/{product_id}", response_model=CacheResponse)
async def read_product(
    product_id: ProductIdentifier,
    request: Request,
    service: ServiceDependency,
    mode: Literal["cache", "bypass"] = "cache",
    ttl_seconds: Annotated[int, Query(ge=1, le=60)] = 5,
) -> CacheResponse:
    cache = cache_service(request, service, product_id)
    with cache.observation.span("HTTP GET product cache", "router", SOURCE):
        product = await cache.read(mode == "bypass", ttl_seconds)
    return CacheResponse(data=product, cache=cache.metadata, trace=cache.observation.snapshot())


@router.get("/{product_id}/state", response_model=CacheResponse)
async def inspect_product(
    product_id: ProductIdentifier, request: Request, service: ServiceDependency
) -> CacheResponse:
    cache = cache_service(request, service, product_id)
    with cache.observation.span("HTTP GET cache state", "router", SOURCE):
        await cache.inspect()
    return CacheResponse(cache=cache.metadata, trace=cache.observation.snapshot())


@router.delete("/{product_id}", response_model=CacheResponse)
async def invalidate_product(
    product_id: ProductIdentifier, request: Request, service: ServiceDependency
) -> CacheResponse:
    cache = cache_service(request, service, product_id)
    with cache.observation.span("HTTP DELETE selected product cache", "router", SOURCE):
        await cache.invalidate()
    return CacheResponse(cache=cache.metadata, trace=cache.observation.snapshot())
