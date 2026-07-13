from fastapi import APIRouter, Depends, HTTPException, Query

from mh_core.engines.automation_engine import AutomationEngine
from mh_core.utils.logger import logger
from mh_core.utils.rate_limit_dependency import limitar_generacion_ia

router = APIRouter(prefix="/automation", tags=["Automation"])

# Instancia única a nivel de proceso — así start/stop/status hablan
# del mismo motor entre requests distintos (igual que un scheduler real).
_motor = AutomationEngine()


@router.get("/status")
def status():
    return _motor.status()


@router.post("/run", dependencies=[Depends(limitar_generacion_ia)])
def run_once():
    try:
        resultado = _motor.run_once(remember=True)
    except Exception as e:
        # AL-07 (auditoría de seguridad): antes se devolvía str(e) tal
        # cual al cliente — podía revelar rutas locales, nombres de
        # proveedor, config interna. El detalle real solo va al log.
        logger.warning(f"automation/run: falló la ejecución ({e}).")
        raise HTTPException(status_code=502, detail="Falló la ejecución automática. Revisa el log del servidor.")
    return {"status": "success", "brain_report": resultado.get("brain_report")}


@router.post("/start")
def start(
    # CR-05 (auditoría de seguridad): antes aceptaba cualquier entero,
    # incluido 0 o negativo — un intervalo así corre el pipeline casi
    # sin pausa, agotando cuota gratis de Gemini/Groq/YouTube en
    # minutos. Rango real: entre 1 minuto y 24 horas.
    interval_seconds: int = Query(3600, ge=60, le=86400),
):
    if _motor.esta_activo():
        # CR-05 / AL-12 (parcial): evita que "start" duplique el
        # scheduler si ya hay uno corriendo — un segundo scheduler
        # sobre el mismo proceso duplicaría ejecuciones y gasto real.
        return {"detail": "Automation ya está activo — no se inició un segundo scheduler.", **_motor.status()}
    _motor.start(interval_seconds=interval_seconds)
    return _motor.status()


@router.post("/stop")
def stop():
    _motor.stop()
    return _motor.status()
