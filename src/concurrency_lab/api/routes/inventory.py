"""Explicitly enabled inventory writes and readonly persisted-state inspection."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Request, Response

from concurrency_lab.api.routes.business import Identifier
from concurrency_lab.core.exceptions import BusinessFailure, FailureCode
from concurrency_lab.schemas.inventory import (
    InventoryResponse,
    OrderInput,
    ScenarioInput,
    TransitionInput,
)
from concurrency_lab.services.inventory_service import InventoryService

router = APIRouter(prefix="/api/v1/business", tags=["inventory"])
SOURCE = "src/concurrency_lab/api/routes/inventory.py"


def inventory_service(request: Request, write: bool = False) -> InventoryService:
    resources = request.app.state.resources
    if resources.business is None:
        raise BusinessFailure(FailureCode.DISABLED)
    if write and not resources.settings.business_writes_enabled:
        with request.state.business_observation.span(
            "Inventory write gate rejected", "validation", SOURCE
        ) as span:
            span.state = "error"
            raise BusinessFailure(FailureCode.WRITES_DISABLED)
    return InventoryService(
        resources.business,
        request.state.business_observation,
        resources.settings.business_request_timeout,
    )


@router.post("/inventory/scenarios", response_model=InventoryResponse)
async def create_scenario(
    intent: ScenarioInput, request: Request, response: Response
) -> InventoryResponse:
    service = inventory_service(request, write=True)
    with service.observation.span("HTTP POST new stock scenario", "router", SOURCE):
        data = await service.create_scenario(intent)
    response.status_code = 200 if data.replayed else 201
    return InventoryResponse(data=data, trace=service.observation.snapshot())


@router.get("/inventory/scenarios/{scenario_id}", response_model=InventoryResponse)
async def get_scenario(scenario_id: UUID, request: Request) -> InventoryResponse:
    service = inventory_service(request)
    with service.observation.span("HTTP GET stock scenario", "router", SOURCE):
        data = await service.get_scenario(scenario_id)
    return InventoryResponse(data=data, trace=service.observation.snapshot())


@router.get("/inventory/scenarios/{scenario_id}/audit", response_model=InventoryResponse)
async def audit_scenario(scenario_id: UUID, request: Request) -> InventoryResponse:
    service = inventory_service(request)
    with service.observation.span("HTTP GET persisted inventory audit", "router", SOURCE):
        data = await service.audit(scenario_id)
    return InventoryResponse(data=data, trace=service.observation.snapshot())


@router.post("/purchases/orders", response_model=InventoryResponse)
async def create_order(
    intent: OrderInput,
    request: Request,
    response: Response,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> InventoryResponse:
    service = inventory_service(request, write=True)
    with service.observation.span("HTTP POST idempotent purchase order", "router", SOURCE):
        data = await service.create_order(intent, idempotency_key)
    response.status_code = 201 if data.applied else 200
    return InventoryResponse(data=data, trace=service.observation.snapshot())


@router.get("/purchases/orders/by-key/{key}", response_model=InventoryResponse)
async def get_order_by_key(key: UUID, request: Request) -> InventoryResponse:
    service = inventory_service(request)
    with service.observation.span("HTTP GET order by original intent key", "router", SOURCE):
        data = await service.get_order(key)
    return InventoryResponse(data=data, trace=service.observation.snapshot())


@router.get("/purchases/orders/{order_id}", response_model=InventoryResponse)
async def get_order(order_id: Identifier, request: Request) -> InventoryResponse:
    service = inventory_service(request)
    with service.observation.span("HTTP GET purchase order", "router", SOURCE):
        data = await service.get_order(order_id)
    return InventoryResponse(data=data, trace=service.observation.snapshot())


@router.post("/purchases/orders/{order_id}/state", response_model=InventoryResponse)
async def change_state(
    order_id: Identifier, intent: TransitionInput, request: Request
) -> InventoryResponse:
    service = inventory_service(request, write=True)
    with service.observation.span("HTTP POST order terminal state", "router", SOURCE):
        data = await service.transition(order_id, intent.target)
    return InventoryResponse(data=data, trace=service.observation.snapshot())
