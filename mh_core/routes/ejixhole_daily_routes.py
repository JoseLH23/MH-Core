"""Rutas privadas del resumen ejecutivo diario de EjiXhole."""
import os
from datetime import date

from fastapi import APIRouter, Depends, Query

from mh_core.core.auth import verificar_api_key
from mh_core.integrations.ejixhole_daily_summary import EjixholeDailySummaryService


router = APIRouter(prefix="/integrations/ejixhole", tags=["Integraciones"])


@router.get("/daily-summary", dependencies=[Depends(verificar_api_key)])
def daily_summary(
    business_date: date | None = Query(default=None),
):
    return EjixholeDailySummaryService(
        os.getenv("EJIXHOLE_EVENT_INBOX_PATH")
    ).build(business_date)
