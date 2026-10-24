"""Read-only learning APIs. Only the fixed health probes perform live SQL/PING."""

from datetime import UTC, datetime
from typing import Literal, cast

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.pool import QueuePool

from concurrency_lab.schemas.visualization import (
    Architecture,
    ExperimentDetail,
    ExperimentSummary,
    PoolSnapshot,
    ProbeGuide,
    QueryPlan,
    ResultPair,
    TraceResponse,
)
from concurrency_lab.services import visualization as data
from concurrency_lab.services.health import readiness
from concurrency_lab.services.tracing import TraceRecorder

router = APIRouter(prefix="/api/v1", tags=["visualization"])


@router.get("/observability/probe-guide", response_model=ProbeGuide)
async def probe_guide(request: Request) -> ProbeGuide:
    settings = request.app.state.resources.settings
    return ProbeGuide(
        mysql_database=settings.mysql_database,
        readiness_timeout_seconds=settings.readiness_timeout,
        io_timeout_seconds=settings.io_timeout,
        pool_timeout_seconds=settings.db_pool_timeout,
    )


def require_id(experiment_id: str) -> None:
    if experiment_id != data.EXPERIMENT_ID:
        raise HTTPException(404, "Unknown experiment")


def require_scale(scale: int) -> None:
    if scale not in data.SCALES:
        raise HTTPException(422, "Scale must be 10000,100000 or1000000")


@router.get("/architecture", response_model=Architecture)
async def architecture(request: Request) -> Architecture:
    value = data.architecture()
    value.startup = request.app.state.startup_trace
    return value


@router.get("/experiments", response_model=list[ExperimentSummary])
async def experiments() -> list[ExperimentSummary]:
    return data.summaries()


@router.get("/experiments/{experiment_id}", response_model=ExperimentDetail)
async def experiment(experiment_id: str) -> ExperimentDetail:
    require_id(experiment_id)
    return data.experiment_detail()


@router.get("/experiments/{experiment_id}/results", response_model=ResultPair)
async def results(experiment_id: str, scale: int = 1000000) -> ResultPair:
    require_id(experiment_id)
    require_scale(scale)
    try:
        return data.result_pair(scale)
    except data.DataUnavailable as exc:
        raise HTTPException(503, "Trusted experiment data unavailable or invalid") from exc


@router.get("/experiments/{experiment_id}/query-plans", response_model=QueryPlan)
async def plans(
    experiment_id: str,
    scale: int = 1000000,
    phase: Literal["baseline", "optimized"] = "baseline",
    query: Literal["primary_key", "by_user", "user_time", "offset", "keyset", "email"] = "offset",
) -> QueryPlan:
    require_id(experiment_id)
    require_scale(scale)
    try:
        value = data.load_result(scale, phase).queries[query]
        return QueryPlan(
            sql=value.sql,
            parameters=value.parameters,
            raw_tree=value.explain_analyze_tree,
            tree=data.parse_plan_tree(value),
            source=data.result_source(scale, phase),
            note="actual rows为节点输出，loops为循环次数；节点时间含子节点，不可累加。",
        )
    except data.DataUnavailable as exc:
        raise HTTPException(503, "Trusted experiment data unavailable or invalid") from exc


@router.get(
    "/observability/health-trace",
    response_model=TraceResponse,
    responses={503: {"model": TraceResponse}},
)
async def health_trace(request: Request) -> JSONResponse:
    resources = request.app.state.resources
    recorder = TraceRecorder()
    recorder.emit(
        "Handler entered",
        "router",
        "running",
        "GET /api/v1/observability/health-trace，无请求体；"
        "health_trace取共享资源，创建记录器。未计量路由匹配耗时。",
    )
    recorder.emit(
        "Service entered",
        "service",
        "running",
        "readiness通过asyncio.gather并发运行MySQL与Redis两个bounded_check；不会先后串行等待。",
    )
    checks = await readiness(
        resources.engine,
        resources.redis,
        resources.settings.readiness_timeout,
        on_event=recorder.probe,
    )
    healthy = all(value == "ok" for value in checks.values())
    state = "success" if healthy else "failure"
    recorder.emit(
        "Service completed",
        "service",
        state,
        f"两个有界探针已完成：mysql={checks['mysql']}，redis={checks['redis']}；全部ok才就绪。",
    )
    recorder.emit(
        "Response prepared", "router", state, "响应即将序列化返回；不代表字节已经发送或浏览器收到。"
    )
    response = TraceResponse(
        http_status=200 if healthy else 503,
        checks=checks,
        server_elapsed_ms=recorder.elapsed(),
        events=recorder.events,
        limitations=[
            "服务端相对时钟，只观测handler/service/probe区间。",
            "未采集网络、路由匹配、纯连接池等待或SQL单独耗时。",
            "两个探针并发，重叠span不能相加；浏览器往返时间由前端独立测量。",
        ],
    )
    return JSONResponse(status_code=response.http_status, content=response.model_dump(mode="json"))


@router.get("/observability/pool", response_model=PoolSnapshot)
async def pool_snapshot(request: Request) -> PoolSnapshot:
    resources = request.app.state.resources
    pool = cast(QueuePool, resources.engine.sync_engine.pool)
    return PoolSnapshot(
        configured_size=pool.size(),
        max_overflow=resources.settings.db_max_overflow,
        checked_out=pool.checkedout(),
        overflow=max(0, pool.overflow()),
        observed_at=datetime.now(UTC).isoformat(),
        note="瞬时SQLAlchemy pool gauges，不是时间序列；等待队列和纯等待时间尚未接入。",
    )
