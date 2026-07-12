from fastapi import APIRouter, HTTPException

from mh_core.engines.automation_engine import AutomationEngine

router = APIRouter(prefix="/automation", tags=["Automation"])

# Instancia única a nivel de proceso — así start/stop/status hablan
# del mismo motor entre requests distintos (igual que un scheduler real).
_motor = AutomationEngine()


@router.get("/status")
def status():
    return _motor.status()


@router.post("/run")
def run_once():
    try:
        resultado = _motor.run_once(remember=True)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Falló la ejecución: {e}")
    return {"status": "success", "brain_report": resultado.get("brain_report")}


@router.post("/start")
def start(interval_seconds: int = 3600):
    _motor.start(interval_seconds=interval_seconds)
    return _motor.status()


@router.post("/stop")
def stop():
    _motor.stop()
    return _motor.status()
