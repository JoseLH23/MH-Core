from fastapi import APIRouter

from mh_core.routes.observability_routes import router as observability_router
from mh_core.services.health_service import get_health_status

router = APIRouter()
router.include_router(observability_router)

# El único "/" público vive en app.py. Este router se registra con API key.


@router.get("/health")
def health():
    return get_health_status()


@router.get("/info")
def info():
    return {
        "name": "MH Core",
        "version": "1.0.0",
        "description": "Core API for the MindHigh ecosystem",
    }
