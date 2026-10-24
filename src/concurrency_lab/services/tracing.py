"""Per-request monotonic events; never a fabricated distributed trace."""

import time
from typing import Literal, cast

from concurrency_lab.schemas.visualization import TraceEvent


class TraceRecorder:
    def __init__(self) -> None:
        self.started = time.perf_counter()
        self.events: list[TraceEvent] = []

    def elapsed(self) -> float:
        return (time.perf_counter() - self.started) * 1000

    def emit(self, name: str, component: str, state: str, detail: str) -> None:
        event = TraceEvent(
            id=f"event-{len(self.events)}",
            name=name,
            component=component,
            state=cast(Literal["running", "waiting", "success", "failure"], state),
            offset_ms=self.elapsed(),
            source="server.perf_counter",
            detail=detail,
        )
        self.events.append(event)

    def probe(self, component: str, state: str) -> None:
        self.emit(
            f"{component} probe {state}",
            component,
            state,
            "实际探针整体区间，含获取连接与命令；未分离纯排队/建连/SQL耗时。",
        )
