"""Correlation and header-preparation observation for business HTTP requests."""

import json
import logging

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from concurrency_lab.observability.recording import RequestObservation

logger = logging.getLogger("concurrency_lab.requests")


class BusinessObservationMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith("/api/v1/business/"):
            await self.app(scope, receive, send)
            return
        config = scope["app"].state.resources.settings
        observation = RequestObservation(config.business_database)
        scope.setdefault("state", {})["business_observation"] = observation

        async def send_observed(message: Message) -> None:
            if message["type"] == "http.response.start":
                elapsed = observation.elapsed()
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = observation.request_id
                headers["X-Process-Time-Ms"] = f"{elapsed:.3f}"
                logger.info(
                    json.dumps(
                        {
                            "event": "business_response_prepared",
                            "request_id": observation.request_id,
                            "method": scope["method"],
                            "status": message["status"],
                            "duration_ms": elapsed,
                            "evidence": "measured",
                        }
                    )
                )
            await send(message)

        await self.app(scope, receive, send_observed)
