from fastapi import APIRouter
from mh_core.services.health_service import get_health_status

router = APIRouter()

@router.get("/")
def root():
    return {
        "message": "MH Core API v1.0 - Running"
    }

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