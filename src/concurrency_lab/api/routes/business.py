"""Typed HTTP mapping and explicit dependency injection; SQL stays in repositories."""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from concurrency_lab.core.exceptions import BusinessFailure, FailureCode
from concurrency_lab.observability.recording import RequestObservation
from concurrency_lab.schemas.business import (
    MAX_ID,
    BusinessErrorDTO,
    BusinessResponse,
    PageParameters,
)
from concurrency_lab.services.business_service import BusinessService, QueryOperation

router = APIRouter(prefix="/api/v1/business", tags=["business"])
Identifier = Annotated[int, Path(ge=1, le=MAX_ID)]
Paging = Annotated[PageParameters, Query()]
SOURCE = "src/concurrency_lab/api/routes/business.py"
ERRORS: dict[FailureCode, tuple[int, str]] = {
    FailureCode.INVALID: (422, "Check positive IDs, bounded limits and paired cursor parameters."),
    FailureCode.DISABLED: (503, "Enable the isolated business lab and initialize its dataset."),
    FailureCode.NOT_FOUND: (404, "Requested record was not found."),
    FailureCode.OWNERSHIP: (503, "Business dataset ownership or readiness check failed."),
    FailureCode.DATABASE: (503, "Business database unavailable; internal details redacted."),
    FailureCode.POOL: (
        503,
        "Business connection acquisition timed out; retry after capacity recovers.",
    ),
    FailureCode.BUDGET: (504, "Business request budget exhausted; retry only this read operation."),
}


def get_business_service(request: Request) -> BusinessService | None:
    resources = request.app.state.resources
    if resources.business is None:
        return None
    return BusinessService(
        resources.business,
        request.state.business_observation,
        resources.settings.business_request_timeout,
    )


ServiceDependency = Annotated[BusinessService | None, Depends(get_business_service)]


async def business_error_handler(request: Request, error: Exception) -> JSONResponse:
    failure = cast(BusinessFailure, error)
    status, message = ERRORS[failure.code]
    observation = cast(RequestObservation, request.state.business_observation)
    response = BusinessResponse(
        error=BusinessErrorDTO(code=failure.code.value, message=message),
        trace=observation.snapshot(),
    )
    return JSONResponse(status_code=status, content=response.model_dump(mode="json"))


async def business_validation_handler(request: Request, error: Exception) -> JSONResponse:
    if not request.url.path.startswith("/api/v1/business/"):
        return await request_validation_exception_handler(
            request, cast(RequestValidationError, error)
        )
    observation = cast(RequestObservation, request.state.business_observation)
    with observation.span("Business input validation rejected", "validation", SOURCE) as span:
        span.state = "error"
    return await business_error_handler(request, BusinessFailure(FailureCode.INVALID))


async def execute_query(
    request: Request,
    service: BusinessService | None,
    operation: QueryOperation,
    entity_id: int,
    page: PageParameters,
) -> BusinessResponse:
    observation = cast(RequestObservation, request.state.business_observation)
    with observation.span(f"HTTP GET {operation.value}", "router", SOURCE):
        if service is None:
            raise BusinessFailure(FailureCode.DISABLED)
        data = await service.execute_read(operation, entity_id, page)
    return BusinessResponse(data=data, trace=observation.snapshot())


@router.get("/products/{product_id}", response_model=BusinessResponse)
async def get_product(
    product_id: Identifier, request: Request, service: ServiceDependency
) -> BusinessResponse:
    return await execute_query(
        request, service, QueryOperation.PRODUCT, product_id, PageParameters()
    )


@router.get("/users/{user_id}/orders", response_model=BusinessResponse)
async def get_user_orders(
    user_id: Identifier, request: Request, page: Paging, service: ServiceDependency
) -> BusinessResponse:
    if page.before_id is not None:
        raise BusinessFailure(FailureCode.INVALID)
    return await execute_query(request, service, QueryOperation.USER_ORDERS, user_id, page)


@router.get("/users/{user_id}/order-page", response_model=BusinessResponse)
async def get_user_order_page(
    user_id: Identifier, request: Request, page: Paging, service: ServiceDependency
) -> BusinessResponse:
    return await execute_query(request, service, QueryOperation.ORDER_PAGE, user_id, page)


@router.get("/orders/{order_id}", response_model=BusinessResponse)
async def get_order_details(
    order_id: Identifier, request: Request, service: ServiceDependency
) -> BusinessResponse:
    return await execute_query(
        request, service, QueryOperation.ORDER_DETAIL, order_id, PageParameters()
    )
