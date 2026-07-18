"""Diagnóstico privado de dependencias y objetivos de disponibilidad."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from mh_core.services.observability_service import operational_health

router = APIRouter(tags=["Observability"])


@router.get("/health/ready")
def readiness():
    sample = operational_health.sample()
    content = {
        "status": "ready" if sample["healthy"] else "unavailable",
        "service": "MH-Core",
        "version": "1.0",
        "checks": sample["checks"],
    }
    return content if sample["healthy"] else JSONResponse(status_code=503, content=content)


@router.get("/observability/summary")
def observability_summary():
    return operational_health.summary()
