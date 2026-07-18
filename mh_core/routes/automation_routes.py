from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from mh_core.engines.automation_engine import AutomationEngine
from mh_core.jobs.durable_queue import DurableJobQueue
from mh_core.utils.logger import logger
from mh_core.utils.rate_limit_dependency import limitar_generacion_ia

router = APIRouter(prefix="/automation", tags=["Automation"])
_motor = AutomationEngine()


class AutomationJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: str | None = Field(default=None, min_length=3, max_length=180)
    priority: int = Field(default=0, ge=-100, le=100)
    max_attempts: int = Field(default=5, ge=1, le=20)


@router.get("/status")
def automation_status():
    return _motor.status()


@router.post("/run", dependencies=[Depends(limitar_generacion_ia)])
def run_once():
    try:
        resultado = _motor.run_once(remember=True)
    except Exception as exc:
        logger.warning("automation/run falló: %s", type(exc).__name__)
        raise HTTPException(
            status_code=502,
            detail="Falló la ejecución automática. Revisa el log del servidor.",
        ) from exc
    return {"status": "success", "brain_report": resultado.get("brain_report")}


@router.post("/enqueue", status_code=status.HTTP_202_ACCEPTED)
def enqueue(data: AutomationJobRequest):
    result = DurableJobQueue().enqueue(
        "automation.run_once",
        {},
        idempotency_key=data.idempotency_key,
        priority=data.priority,
        max_attempts=data.max_attempts,
    )
    return {
        "job_id": result.job.id,
        "status": result.job.status,
        "duplicate": result.duplicate,
    }


@router.post("/start")
def start(interval_seconds: int = Query(3600, ge=60, le=86400)):
    if _motor.esta_activo():
        return {
            "detail": "Automation ya está activo — no se inició un segundo scheduler.",
            **_motor.status(),
        }
    _motor.start(interval_seconds=interval_seconds)
    return _motor.status()


@router.post("/stop")
def stop():
    _motor.stop()
    return _motor.status()
