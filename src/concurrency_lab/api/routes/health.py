from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from concurrency_lab.services.health import readiness

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    resources = request.app.state.resources
    checks = await readiness(
        resources.engine, resources.redis, resources.settings.readiness_timeout
    )
    healthy = all(value == "ok" for value in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ready" if healthy else "unavailable", "checks": checks},
    )
