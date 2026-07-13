"""
Rutas de MindHigh. "Panel funcional" a nivel de API — datos reales
listos para que un frontend los consuma; no incluye UI todavía (fuera
de alcance de este proyecto backend).
"""
from fastapi import APIRouter, HTTPException

from apps.mindhigh.models.content_piece import DURACIONES_VALIDAS
from apps.mindhigh.engines.metrics_engine import MetricsEngine
from apps.mindhigh.mindhigh_pipeline import MindHighPipeline

router = APIRouter(prefix="/mindhigh", tags=["MindHigh"])

_pipeline = MindHighPipeline()
_metrics_engine = MetricsEngine()


@router.post("/run")
def run(remember: bool = True, duration_target: str = "short", style: str = "informativo"):
    if duration_target not in DURACIONES_VALIDAS:
        raise HTTPException(status_code=400, detail=f"duration_target debe ser uno de: {DURACIONES_VALIDAS}")
    try:
        return _pipeline.run(remember=remember, duration_target=duration_target, style=style)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"El flujo de MindHigh falló: {e}")


@router.get("/metrics")
def metrics():
    return {"metrics": [m.model_dump() for m in _metrics_engine.all()]}


@router.get("/metrics/{content_id}")
def metrics_for_content(content_id: str):
    return {"content_id": content_id, "metrics": [m.model_dump() for m in _metrics_engine.for_content(content_id)]}
