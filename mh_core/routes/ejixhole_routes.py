from fastapi import APIRouter, HTTPException

from mh_core.integrations.ejixhole_client import EjixholeClient, EjixholeConfigurationError, EjixholeOperationalSummary, EjixholeUpstreamError

router = APIRouter(prefix="/integrations/ejixhole", tags=["Integraciones"])


@router.get("/summary", response_model=EjixholeOperationalSummary)
def ejixhole_summary():
    try:
        return EjixholeClient().operational_summary()
    except EjixholeConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except EjixholeUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
