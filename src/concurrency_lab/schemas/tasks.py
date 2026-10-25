"""Task HTTP observations are separate from asynchronous execution history."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BeforeValidator, Field

from concurrency_lab.schemas.business import MAX_ID, BusinessErrorDTO, BusinessTrace
from concurrency_lab.schemas.visualization import DTO


def database_utc(value: Any) -> Any:
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


DatabaseUTC = Annotated[datetime, BeforeValidator(database_utc)]


class ControlledFaultPlan(DTO):
    evidence_type: Literal["controlled_fault_configuration"] = "controlled_fault_configuration"
    fail_first_attempts: int = Field(default=0, ge=0, le=5)
    delay_ms: int = Field(default=0, ge=0, le=5000)


class TaskInput(DTO):
    task_id: UUID
    order_id: int = Field(ge=1, le=MAX_ID)
    max_attempts: int = Field(default=3, ge=1, le=5)
    fault_plan: ControlledFaultPlan | None = None


class RetryInput(DTO):
    task_id: UUID
    disable_faults: bool = True


class TaskDTO(DTO):
    id: UUID
    scenario_id: UUID
    order_id: int
    kind: Literal["order_receipt"]
    fault_plan: ControlledFaultPlan | None
    max_attempts: int
    attempts: int
    state: Literal["queued", "running", "retry_wait", "succeeded", "failed"]
    available_at: DatabaseUTC
    lease_until: DatabaseUTC | None
    last_error: str | None
    result_receipt_id: int | None
    retry_of: UUID | None
    created_at: DatabaseUTC
    updated_at: DatabaseUTC
    finished_at: DatabaseUTC | None


class OutboxDTO(DTO):
    task_id: UUID
    next_publish_at: DatabaseUTC
    publish_count: int
    last_message_id: str | None
    last_published_at: DatabaseUTC | None


class AttemptDTO(DTO):
    number: int
    worker_id: str
    status: str
    started_at: DatabaseUTC
    finished_at: DatabaseUTC | None
    abandoned_at: DatabaseUTC | None
    handler_ms: float | None
    error: str | None
    timeout_seconds: float
    lease_seconds: float


class EventDTO(DTO):
    id: int
    occurred_at: DatabaseUTC
    kind: str
    source: str
    details: dict[str, Any]


class ReceiptDTO(DTO):
    id: int
    order_id: int
    total: Decimal
    snapshot: dict[str, Any]
    created_at: DatabaseUTC


class TaskResult(DTO):
    task: TaskDTO
    replayed: bool = False


class TaskDetail(DTO):
    task: TaskDTO
    outbox: OutboxDTO
    attempts: list[AttemptDTO]
    events: list[EventDTO]
    events_truncated: bool
    receipt: ReceiptDTO | None
    worker_command: str
    source: str = "MySQL persisted task/attempt/event/outbox/receipt"
    definitions: list[str] = Field(
        default_factory=lambda: [
            "handler_ms: monotonic handler phase only; excludes claim/finalization/ACK",
            "abandoned_at: recovery observation, not worker finish; crash duration stays unknown",
            "publication confirmation and ACK observation can be absent after a real side effect",
            "lease_until does not prove the worker process is alive",
        ]
    )


class TaskList(DTO):
    tasks: list[TaskDTO]


class QueueSnapshot(DTO):
    scenario_id: UUID
    observed_at: DatabaseUTC
    collection_ms: float
    database_counts: dict[str, int]
    redis_available: bool
    group_ready: bool | None
    retained_entries: int | None
    pending: int | None
    group_lag: int | None
    pttl_ms: int | None
    source: str = "Independent MySQL counts and Redis XLEN/XPENDING/XINFO GROUPS/PTTL; not atomic"
    definitions: list[str] = Field(
        default_factory=lambda: [
            "retained_entries is XLEN, including acknowledged history; not backlog",
            "pending is delivered but not acknowledged; group_lag may be unknown",
            "unavailable observations remain null; database state is authoritative",
        ]
    )


class TaskResponse(DTO):
    data: TaskResult | TaskDetail | TaskList | QueueSnapshot | None = None
    error: BusinessErrorDTO | None = None
    trace: BusinessTrace
