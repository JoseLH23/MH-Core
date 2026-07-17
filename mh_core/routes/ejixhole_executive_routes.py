"""Ruta privada del dashboard ejecutivo de EjiXhole."""
import os
from datetime import date

from fastapi import APIRouter, Depends, Query

from mh_core.core.auth import verificar_api_key
from mh_core.integrations.ejixhole_executive_dashboard import EjixholeExecutiveDashboardService


router = APIRouter(prefix="/integrations/ejixhole", tags=["Integraciones"])


@router.get("/executive-dashboard", dependencies=[Depends(verificar_api_key)])
def executive_dashboard(
    business_date: date | None = Query(default=None),
    days: int = Query(default=7, ge=1, le=31),
):
    return EjixholeExecutiveDashboardService(
        os.getenv("EJIXHOLE_EVENT_INBOX_PATH")
    ).build(business_date=business_date, days=days)
