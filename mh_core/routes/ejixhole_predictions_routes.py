import os
from datetime import date

from fastapi import APIRouter, Depends, Query

from mh_core.core.auth import verificar_api_key
from mh_core.integrations.ejixhole_predictions import EjixholePredictionsService

router = APIRouter(prefix="/integrations/ejixhole", tags=["Integraciones"])


def _service() -> EjixholePredictionsService:
    return EjixholePredictionsService(os.getenv("EJIXHOLE_EVENT_INBOX_PATH"))


@router.get("/predictions", dependencies=[Depends(verificar_api_key)])
def predictions(business_date: date | None = Query(default=None)):
    return _service().build(business_date)


@router.get("/predictions/evaluation", dependencies=[Depends(verificar_api_key)])
def prediction_evaluation(
    as_of: date | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=52),
):
    """Compara predicciones maduras contra los eventos reales observados."""
    return _service().evaluation(as_of=as_of, limit=limit)
