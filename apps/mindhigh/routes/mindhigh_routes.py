"""
Rutas de MindHigh. "Panel funcional" a nivel de API — datos reales
listos para que un frontend los consuma; no incluye UI todavía (fuera
de alcance de este proyecto backend).
"""
from fastapi import APIRouter, Depends, HTTPException

import os

from apps.mindhigh.models.content_piece import DURACIONES_VALIDAS
from apps.mindhigh.engines.metrics_engine import MetricsEngine
from apps.mindhigh.engines.performance_engine import PerformanceEngine
from apps.mindhigh.mindhigh_pipeline import MindHighPipeline

router = APIRouter(prefix="/mindhigh", tags=["MindHigh"])

_pipeline = MindHighPipeline()
_metrics_engine = MetricsEngine()
_performance_engine = PerformanceEngine()


@router.get("/providers/status")
def estado_proveedores():
    """Solo verifica si cada proveedor TIENE una key configurada — no
    hace ninguna llamada real (no gasta cuota gratis solo por
    consultar el estado)."""
    return {
        "youtube": "configured" if os.environ.get("YOUTUBE_API_KEY") else "not_configured",
        "gemini": "configured" if os.environ.get("GEMINI_API_KEY") else "not_configured",
        "groq": "configured" if os.environ.get("GROQ_API_KEY") else "not_configured",
        "template_fallback": "always_available",
    }


from mh_core.core.rate_limiter import RateLimiter
from mh_core.utils.rate_limit_dependency import limitar_generacion_ia

_limiter_run = RateLimiter(max_llamadas=10, ventana_segundos=300)  # 10 cada 5 min — protege la cuota gratis


@router.post("/run", dependencies=[Depends(limitar_generacion_ia)])
def run(remember: bool = True, duration_target: str = "short", style: str = "informativo"):
    if not _limiter_run.permitido("global"):
        espera = _limiter_run.segundos_para_reintentar("global")
        raise HTTPException(status_code=429, detail=f"Demasiadas ejecuciones seguidas. Reintenta en {espera:.0f}s.")
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


@router.post("/metrics/{content_id}/real")
def registrar_metrica_real(
    content_id: str,
    views: int = 0,
    likes: int = 0,
    comments: int = 0,
    impressions: int = 0,
    retention_percent: float | None = None,
    avg_view_duration_seconds: float | None = None,
    conversions: int | None = None,
):
    """Registra una métrica REAL (no simulada) cuando exista
    publicación real y datos verdaderos que reportar."""
    try:
        metrica = _performance_engine.registrar_metrica_real(
            content_id, views, likes, comments, impressions, retention_percent, avg_view_duration_seconds, conversions
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return metrica.model_dump()


@router.get("/performance/summary")
def resumen_rendimiento():
    return _performance_engine.resumen_para_aprendizaje()


@router.get("/performance/compare")
def comparar_rendimiento(content_id_a: str, content_id_b: str):
    return _performance_engine.comparar_rendimiento(content_id_a, content_id_b)
