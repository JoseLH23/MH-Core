"""Resumen operativo construido desde eventos recibidos de EjiXhole."""
import os

from fastapi import APIRouter, Depends

from mh_core.core.auth import verificar_api_key
from mh_core.integrations.ejixhole_event_processor import EjixholeEventProcessor


router = APIRouter(prefix="/integrations/ejixhole", tags=["Integraciones"])


@router.get("/operations/summary", dependencies=[Depends(verificar_api_key)])
def processed_operations_summary():
    return EjixholeEventProcessor(
        os.getenv("EJIXHOLE_EVENT_INBOX_PATH")
    ).summary()
