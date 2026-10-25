"""Bounded task intent/observations. Process control remains an explicit CLI operation."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response

from concurrency_lab.cache.task_stream import TaskStream
from concurrency_lab.core.exceptions import BusinessFailure, FailureCode
from concurrency_lab.schemas.tasks import RetryInput, TaskInput, TaskResponse
from concurrency_lab.services.tasks import TaskService

router = APIRouter(prefix="/api/v1/business", tags=["tasks"])


def task_service(request: Request, write: bool = False) -> TaskService:
    resources = request.app.state.resources
    if resources.business is None:
        raise BusinessFailure(FailureCode.DISABLED)
    if write and not resources.settings.business_writes_enabled:
        with request.state.business_observation.span(
            "Task write gate rejected", "validation", "src/concurrency_lab/api/routes/tasks.py"
        ):
            raise BusinessFailure(FailureCode.WRITES_DISABLED)
    return TaskService(
        resources.business,
        request.state.business_observation,
        resources.settings.business_request_timeout,
    )


@router.post("/tasks", response_model=TaskResponse)
async def create_task(intent: TaskInput, request: Request, response: Response) -> TaskResponse:
    service = task_service(request, True)
    data = await service.create(intent)
    response.status_code = 200 if data.replayed else 201
    return TaskResponse(data=data, trace=service.observation.snapshot())


@router.post("/tasks/{identifier}/retry", response_model=TaskResponse)
async def retry_task(
    identifier: UUID, intent: RetryInput, request: Request, response: Response
) -> TaskResponse:
    service = task_service(request, True)
    data = await service.retry(identifier, intent)
    response.status_code = 200 if data.replayed else 201
    return TaskResponse(data=data, trace=service.observation.snapshot())


@router.get("/tasks", response_model=TaskResponse)
async def list_tasks(
    request: Request, scenario_id: UUID, limit: Annotated[int, Query(ge=1, le=20)] = 20
) -> TaskResponse:
    service = task_service(request)
    return TaskResponse(
        data=await service.list(scenario_id, limit), trace=service.observation.snapshot()
    )


@router.get("/tasks/{identifier}", response_model=TaskResponse)
async def task_detail(identifier: UUID, request: Request) -> TaskResponse:
    service = task_service(request)
    return TaskResponse(data=await service.detail(identifier), trace=service.observation.snapshot())


@router.get("/task-queues/{scenario_id}", response_model=TaskResponse)
async def queue_detail(scenario_id: UUID, request: Request) -> TaskResponse:
    service = task_service(request)
    resources = request.app.state.resources
    stream = TaskStream(resources.redis, resources.settings.business_database, scenario_id)
    return TaskResponse(data=await service.queue(stream), trace=service.observation.snapshot())
