"""
MetricsEngine — capa de servicio sobre MetricsRepository (mismo patrón
que MemoryEngine sobre MemoryRepository).

HONESTIDAD IMPORTANTE: como la publicación hoy es SIMULADA (no hay
adaptador real conectado a ninguna red social todavía), no existen
vistas/likes/comentarios reales que recolectar. `record_initial()`
guarda una métrica en cero, marcada `simulated=True` — representa
"se publicó, todavía no hay datos reales", no un número inventado.
Cuando exista un PublisherAdapter real, un adaptador de métricas real
reemplaza esto sin tocar MindHighPipeline.
"""
from pathlib import Path
from typing import Optional

from apps.mindhigh.database.json_metrics_repository import JsonMetricsRepository
from apps.mindhigh.database.metrics_repository import MetricsRepository
from apps.mindhigh.models.metric import Metric
from mh_core.core.config import DATABASE_DIR
from mh_core.utils.logger import logger

METRICS_FILE = DATABASE_DIR / "mindhigh" / "metrics.json"


class MetricsEngine:
    def __init__(self, repository: Optional[MetricsRepository] = None):
        self.repository = repository or JsonMetricsRepository(METRICS_FILE)

    def record_initial(self, content_id: str, simulated: bool = True) -> Metric:
        metrica = Metric(content_id=content_id, views=0, likes=0, comments=0, simulated=simulated)
        guardada = self.repository.guardar(metrica)
        logger.info(f"MetricsEngine: métrica inicial registrada para content_id={content_id} (simulated={simulated}).")
        return guardada

    def for_content(self, content_id: str) -> list[Metric]:
        return self.repository.por_contenido(content_id)

    def all(self) -> list[Metric]:
        return self.repository.listar()
