"""
Rutas de MindHigh. "Panel funcional" a nivel de API — datos reales
listos para que un frontend los consuma; no incluye UI todavía (fuera
de alcance de este proyecto backend).
"""
from fastapi import APIRouter, HTTPException

from apps.mindhigh.engines.metrics_engine import MetricsEngine
from apps.mindhigh.mindhigh_pipeline import MindHighPipeline

router = APIRouter(prefix="/mindhigh", tags=["MindHigh"])

_pipeline = MindHighPipeline()
_metrics_engine = MetricsEngine()


@router.post("/run")
def run(remember: bool = True):
    try:
        return _pipeline.run(remember=remember)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"El flujo de MindHigh falló: {e}")


@router.get("/metrics")
def metrics():
    return {"metrics": [m.model_dump() for m in _metrics_engine.all()]}


@router.get("/metrics/{content_id}")
def metrics_for_content(content_id: str):
    return {"content_id": content_id, "metrics": [m.model_dump() for m in _metrics_engine.for_content(content_id)]}
