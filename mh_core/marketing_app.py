"""Aplicación mínima y privada para operar Marketing de MindHigh.

Este runtime no registra investigación, automatización, video, agentes ni las
integraciones analíticas completas de MH-Core. Expone únicamente salud y el
router gobernado de campañas.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

load_dotenv()

from apps.mindhigh.routes.marketing_routes import (  # noqa: E402
    knowledge_service,
    router as marketing_router,
)
from mh_core.core.auth import requerir_scopes  # noqa: E402

_MIN_SERVICE_KEY_LENGTH = 32
_REQUIRED_MARKETING_DOCUMENTS = 4


def _production(environment: str | None = None) -> bool:
    selected = environment if environment is not None else os.getenv("MH_ENVIRONMENT", "development")
    return selected.strip().lower() == "production"


def _runtime_ready() -> bool:
    service_key = os.getenv("MH_CORE_EJIXHOLE_KEY", "").strip()
    if len(service_key) < _MIN_SERVICE_KEY_LENGTH:
        return False

    status = knowledge_service.status()
    return bool(
        status.get("available") is True
        and int(status.get("documents") or 0) >= _REQUIRED_MARKETING_DOCUMENTS
    )


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
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @application.get("/health/live", include_in_schema=False)
    def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/ready", include_in_schema=False)
    def readiness():
        if not _runtime_ready():
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable"},
                headers={"Cache-Control": "no-store"},
            )
        return {"status": "ready"}

    application.include_router(
        marketing_router,
        dependencies=[Depends(requerir_scopes("mindhigh.campaigns"))],
    )
    return application


app = create_marketing_app()
