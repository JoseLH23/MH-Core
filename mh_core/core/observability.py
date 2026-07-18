"""Middleware HTTP con request ID, métricas y logs seguros."""
from __future__ import annotations

import json
import logging
import re
import time
from uuid import uuid4

from starlette.requests import Request
from starlette.types import ASGIApp

from mh_core.core.runtime_metrics import runtime_metrics

logger = logging.getLogger("mh_core.http")
_NUMBER = re.compile(r"^\d+$")
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}$")


def safe_path(path: str) -> str:
    parts = []
    for segment in path.split("/"):
        if _NUMBER.fullmatch(segment):
            parts.append("{id}")
        elif _UUID.fullmatch(segment):
            parts.append("{uuid}")
        else:
            parts.append(segment[:80])
    return "/".join(parts)[:500]


class ObservabilityMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        request_id = request.headers.get("x-request-id") or str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.perf_counter()
        status_code = 500
        runtime_metrics.begin()

        async def send_with_request_id(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii", errors="ignore")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            duration_ms = int((time.perf_counter() - started) * 1000)
            runtime_metrics.finish(500, duration_ms)
            logger.exception(
                json.dumps(
                    {
                        "event": "http.unhandled_error",
                        "request_id": request_id,
                        "method": request.method,
                        "path": safe_path(request.url.path),
                        "status": 500,
                        "duration_ms": duration_ms,
                    },
                    sort_keys=True,
                )
            )
            raise

        duration_ms = int((time.perf_counter() - started) * 1000)
        runtime_metrics.finish(status_code, duration_ms)
        level = logging.ERROR if status_code >= 500 else logging.WARNING if status_code >= 400 else logging.INFO
        logger.log(
            level,
            json.dumps(
                {
                    "event": "http.response",
                    "request_id": request_id,
                    "method": request.method,
                    "path": safe_path(request.url.path),
                    "status": status_code,
                    "duration_ms": duration_ms,
                },
                sort_keys=True,
            ),
        )
