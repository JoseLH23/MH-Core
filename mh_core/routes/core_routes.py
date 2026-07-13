from fastapi import APIRouter
from mh_core.services.health_service import get_health_status

router = APIRouter()

# NOTA (BA-01, auditoría de seguridad 13/jul/2026): antes había un "/"
# aquí también, duplicado con el de mh_core/app.py — competían por el
# mismo path y, dependiendo del orden de registro, uno podía ganar
# silenciosamente sobre el otro (pasó de verdad al proteger core_router
# con X-API-Key: este "/" protegido empezó a tapar el público). Se
# quita — el único "/" real vive en app.py, sin auth, como liveness check.

@router.get("/health")
def health():
    return get_health_status()

@router.get("/info")
def info():
    return {
        "name": "MH Core",
        "version": "1.0.0",
        "description": "Core API for the MindHigh ecosystem"
    }