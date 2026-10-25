"""Fixed receipt intent and bounded worker ownership policy."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from concurrency_lab.schemas.tasks import TaskInput

TERMINAL = frozenset({"succeeded", "failed"})


@dataclass(frozen=True)
class WorkerPolicy:
    timeout_seconds: float = 1
    lease_seconds: float = 5

    def __post_init__(self) -> None:
        if not 0.1 <= self.timeout_seconds <= 10 or not 1 <= self.lease_seconds <= 60:
            raise ValueError("Worker timeout/lease outside laboratory bounds")
        if self.lease_seconds <= self.timeout_seconds + 0.5:
            raise ValueError("Lease must exceed handler deadline by more than0.5s")


def task_fingerprint(intent: TaskInput, retry_of: UUID | None = None) -> str:
    payload = intent.model_dump(mode="json", exclude={"task_id"})
    payload["retry_of"] = retry_of.hex if retry_of else None
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
