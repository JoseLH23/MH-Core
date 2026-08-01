"""Aplicación mínima para operar Marketing de MindHigh en producción.

No registra investigación, automatización, video, agentes ni integraciones
analíticas completas. Expone únicamente salud y el router gobernado de campañas.
"""
from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

load_dotenv()

from apps.mindhigh.routes.marketing_routes import (  # noqa: E402
    knowledge_service,
    router as marketing_router,
)
from mh_core.services.governed_knowledge_service import (  # noqa: E402
    KnowledgeUnavailableError,
)

_MIN_SERVICE_KEY_LENGTH = 32
_MAX_CAMPAIGN_BODY_BYTES = 64 * 1024
_CAMPAIGN_PATH = "/mindhigh/marketing/campaigns/draft"
_REQUIRED_DOCUMENT_IDS = frozenset(
    {"brand", "marketing_strategy", "offer", "agent_rules"}
)
_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


class CampaignBodyLimitMiddleware:
    """Limita cuerpos con o sin Content-Length y los reproduce al downstream."""

    def __init__(self, app, *, max_bytes: int = _MAX_CAMPAIGN_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: dict[str, Any], receive, send) -> None:
        if (
            scope.get("type") != "http"
            or scope.get("method") != "POST"
            or scope.get("path") != _CAMPAIGN_PATH
        ):
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        declared_length = headers.get(b"content-length")
        if declared_length is not None:
            try:
                parsed_length = int(declared_length)
            except ValueError:
                await self._reject(scope, receive, send, 400, "Solicitud inválida.")
                return
            if parsed_length < 0 or parsed_length > self.max_bytes:
                await self._reject(scope, receive, send, 413, "Solicitud demasiado grande.")
                return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            body.extend(message.get("body", b""))
            if len(body) > self.max_bytes:
                await self._reject(scope, receive, send, 413, "Solicitud demasiado grande.")
                return
            if not message.get("more_body", False):
                break

        delivered = False

        async def replay_receive() -> dict[str, Any]:
            nonlocal delivered
            if delivered:
                return {"type": "http.request", "body": b"", "more_body": False}
            delivered = True
            return {
                "type": "http.request",
                "body": bytes(body),
                "more_body": False,
            }

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _reject(scope, receive, send, status_code: int, detail: str) -> None:
        response = JSONResponse(
            status_code=status_code,
            content={"detail": detail},
            headers=_SECURITY_HEADERS,
        )
        await response(scope, receive, send)


def _production(environment: str | None = None) -> bool:
    selected = environment if environment is not None else os.getenv(
        "MH_ENVIRONMENT", "development"
    )
    return selected.strip().lower() == "production"


def _runtime_ready() -> bool:
    service_key = os.getenv("MH_CORE_EJIXHOLE_KEY", "").strip()
    if len(service_key) < _MIN_SERVICE_KEY_LENGTH:
        return False

    try:
        bundle = knowledge_service.load_bundle()
    except KnowledgeUnavailableError:
        return False
    return all(bundle.get(document_id) is not None for document_id in _REQUIRED_DOCUMENT_IDS)


def create_marketing_app(environment: str | None = None) -> FastAPI:
    """Construye el runtime aislado; útil para producción y pruebas."""
    production = _production(environment)
    application = FastAPI(
        title="MindHigh Marketing",
        version="1.0.0",
        docs_url=None if production else "/docs",
        redoc_url=None if production else "/redoc",
        openapi_url=None if production else "/openapi.json",
    )

    @application.middleware("http")
    async def security_headers(request: Request, call_next: Callable[..., Awaitable]):
        response = await call_next(request)
        for name, value in _SECURITY_HEADERS.items():
            response.headers[name] = value
        return response

    application.add_middleware(CampaignBodyLimitMiddleware)

    @application.get("/health/live", include_in_schema=False)
    def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/ready", include_in_schema=False)
    def readiness():
        if not _runtime_ready():
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable"},
                headers=_SECURITY_HEADERS,
            )
        return {"status": "ready"}

    application.include_router(marketing_router)
    return application


app = create_marketing_app()
