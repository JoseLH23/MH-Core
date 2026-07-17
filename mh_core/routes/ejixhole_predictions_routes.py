import os
from datetime import date

from fastapi import APIRouter, Depends, Query

from mh_core.core.auth import verificar_api_key
from mh_core.integrations.ejixhole_predictions import EjixholePredictionsService

router = APIRouter(prefix="/integrations/ejixhole", tags=["Integraciones"])


@router.get("/predictions", dependencies=[Depends(verificar_api_key)])
def predictions(business_date: date | None = Query(default=None)):
    return EjixholePredictionsService(
        os.getenv("EJIXHOLE_EVENT_INBOX_PATH")
    ).build(business_date)
