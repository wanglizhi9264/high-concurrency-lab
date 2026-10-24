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
        command = (
            'engine.connect() → execute(text("SELECT 1")) → 退出作用域归还连接；不读业务表。'
            if component == "mysql"
            else "共享Redis客户端 → await client.ping() → 将PONG解析为True；不读缓存键。"
        )
        outcome = {
            "running": "已开始有界检查，与另一项探针并发。",
            "success": "检查返回True，结果记为ok。",
            "failure": "检查返回False或发生异常/超时，结果记为unavailable；未公开具体原因。",
        }[state]
        self.emit(
            f"{component} probe {state}",
            component,
            state,
            f"{command}{outcome}整体区间含获取连接与命令；未分离纯排队/建连/SQL耗时。",
        )
