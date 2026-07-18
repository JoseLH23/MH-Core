import os
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from mh_core.core.auth import verificar_api_key
from mh_core.integrations.ejixhole_calibrated_predictions import EjixholeCalibratedPredictionsService
from mh_core.integrations.ejixhole_intelligence_center import EjixholeIntelligenceCenterService
from mh_core.integrations.ejixhole_predictions import EjixholePredictionsService
from mh_core.integrations.ejixhole_profitability import EjixholeProfitabilityService

router = APIRouter(prefix="/integrations/ejixhole", tags=["Integraciones"])


def _service() -> EjixholePredictionsService:
    return EjixholePredictionsService(os.getenv("EJIXHOLE_EVENT_INBOX_PATH"))


def _calibrated_service() -> EjixholeCalibratedPredictionsService:
    return EjixholeCalibratedPredictionsService(os.getenv("EJIXHOLE_EVENT_INBOX_PATH"))


def _center() -> EjixholeIntelligenceCenterService:
    return EjixholeIntelligenceCenterService(os.getenv("EJIXHOLE_EVENT_INBOX_PATH"))


@router.get("/predictions", dependencies=[Depends(verificar_api_key)])
def predictions(business_date: date | None = Query(default=None)):
    return _center().build(business_date)


@router.get("/predictions/evaluation", dependencies=[Depends(verificar_api_key)])
def prediction_evaluation(
    as_of: date | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=52),
):
    return _service().evaluation(as_of=as_of, limit=limit)


@router.get("/decisions", dependencies=[Depends(verificar_api_key)])
def decision_center(limit: int = Query(default=50, ge=1, le=200)):
    return _center().history(limit=limit)


@router.get("/profitability", dependencies=[Depends(verificar_api_key)])
def service_profitability(
    business_date: date | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
):
    center = _center()
    target = business_date or datetime.now(timezone.utc).date()
    return EjixholeProfitabilityService(center.inbox).build(target, days=days)


@router.post("/predictions/recommendations/{code}/decision", dependencies=[Depends(verificar_api_key)])
def recommendation_decision(
    code: str,
    business_date: str = Query(...),
    decision: str = Query(...),
):
    try:
        return _center().decide(business_date, code, decision)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/predictions/recommendations/{code}/outcome", dependencies=[Depends(verificar_api_key)])
def recommendation_outcome(
    code: str,
    business_date: str = Query(...),
    outcome: str = Query(...),
    note: str | None = Query(default=None, max_length=500),
):
    try:
        return _center().record_outcome(business_date, code, outcome, note)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
