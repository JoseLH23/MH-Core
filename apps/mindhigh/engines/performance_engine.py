"""
PerformanceEngine — aprendizaje a partir del rendimiento real (o
simulado, claramente separado) de contenido publicado.

Reutiliza MetricsRepository/JsonMetricsRepository (mismo almacenamiento
que ya usaba MetricsEngine) — no se crea un repositorio paralelo, solo
un servicio con capacidades nuevas encima de los mismos datos.
"""
from pathlib import Path
from typing import Optional

from apps.mindhigh.database.metrics_repository import MetricsRepository
from apps.mindhigh.database.json_metrics_repository import JsonMetricsRepository
from apps.mindhigh.models.metric import Metric
from mh_core.core.config import DATABASE_DIR
from mh_core.utils.logger import logger

METRICS_FILE = DATABASE_DIR / "mindhigh" / "metrics.json"


class PerformanceEngine:
    def __init__(self, repository: Optional[MetricsRepository] = None):
        self.repository = repository or JsonMetricsRepository(METRICS_FILE)

    def registrar_metrica_real(
        self,
        content_id: str,
        views: int = 0,
        likes: int = 0,
        comments: int = 0,
        impressions: int = 0,
        retention_percent: Optional[float] = None,
        avg_view_duration_seconds: Optional[float] = None,
        conversions: Optional[int] = None,
    ) -> Metric:
        """Registra una métrica REAL (simulated=False) — se usará
        cuando exista publicación real conectada. Las validaciones del
        modelo Metric ya rechazan valores imposibles (negativos,
        retención fuera de 0-100)."""
        metrica = Metric(
            content_id=content_id,
            views=views,
            likes=likes,
            comments=comments,
            impressions=impressions,
            retention_percent=retention_percent,
            avg_view_duration_seconds=avg_view_duration_seconds,
            conversions=conversions,
            simulated=False,
        )
        guardada = self.repository.guardar(metrica)
        logger.info(f"PerformanceEngine: métrica REAL registrada para content_id={content_id}.")
        return guardada

    def ultima_metrica(self, content_id: str) -> Optional[Metric]:
        metricas = self.repository.por_contenido(content_id)
        return metricas[-1] if metricas else None

    def comparar_rendimiento(self, content_id_a: str, content_id_b: str) -> dict:
        """Compara la métrica más reciente de dos piezas de contenido
        — típicamente dos versiones distintas del mismo linaje. None
        en cualquier campo que no se pueda comparar (ej. sin datos)."""
        a = self.ultima_metrica(content_id_a)
        b = self.ultima_metrica(content_id_b)

        def _extraer(m: Optional[Metric]) -> dict:
            if m is None:
                return {"disponible": False}
            return {
                "disponible": True,
                "views": m.views,
                "engagement_rate_percent": m.engagement_rate_percent,
                "ctr_percent": m.ctr_percent,
                "retention_percent": m.retention_percent,
                "simulated": m.simulated,
            }

        return {"content_id_a": content_id_a, "content_id_b": content_id_b, "a": _extraer(a), "b": _extraer(b)}

    def resumen_para_aprendizaje(self, content_ids: Optional[list[str]] = None) -> dict:
        """
        Resumen agregado para Learning Engine/Quality Engine — separa
        SIEMPRE reales de simuladas, nunca las mezcla en un mismo
        promedio (mezclarlas haría ver "aprendizaje real" donde solo
        hay datos de prueba).
        """
        todas = self.repository.listar()
        if content_ids is not None:
            todas = [m for m in todas if m.content_id in content_ids]

        reales = [m for m in todas if not m.simulated]
        simuladas = [m for m in todas if m.simulated]

        def _promedios(metricas: list[Metric]) -> dict:
            if not metricas:
                return {"total": 0, "message": "Sin datos todavía."}
            ctrs = [m.ctr_percent for m in metricas if m.ctr_percent is not None]
            retenciones = [m.retention_percent for m in metricas if m.retention_percent is not None]
            engagements = [m.engagement_rate_percent for m in metricas if m.engagement_rate_percent is not None]

            return {
                "total": len(metricas),
                "total_views": sum(m.views for m in metricas),
                "avg_ctr_percent": round(sum(ctrs) / len(ctrs), 2) if ctrs else None,
                "avg_retention_percent": round(sum(retenciones) / len(retenciones), 2) if retenciones else None,
                "avg_engagement_rate_percent": round(sum(engagements) / len(engagements), 2) if engagements else None,
            }

        return {
            "real": _promedios(reales),
            "simulated": _promedios(simuladas),
            "nota": "Los promedios reales y simulados nunca se combinan entre sí.",
        }
