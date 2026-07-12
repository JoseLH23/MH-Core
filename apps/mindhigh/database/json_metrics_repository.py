"""
Implementación JSON de MetricsRepository — mismo manejo real de
corrupción/backup que JsonMemoryRepository (mh_core/database/), no se
duplica la lógica: se reutiliza el patrón, adaptado a Metric.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

from apps.mindhigh.database.metrics_repository import MetricsRepository
from apps.mindhigh.models.metric import Metric
from mh_core.utils.logger import logger


class JsonMetricsRepository(MetricsRepository):
    def __init__(self, path: Path):
        self.path = Path(path)

    def _cargar_crudo(self) -> list[dict]:
        if not self.path.exists():
            return []
        contenido = self.path.read_text(encoding="utf-8").strip()
        if not contenido:
            return []
        try:
            datos = json.loads(contenido)
        except json.JSONDecodeError as e:
            respaldo = self.path.with_name(
                f"{self.path.stem}.corrupto-{datetime.now().strftime('%Y%m%dT%H%M%S')}{self.path.suffix}.bak"
            )
            shutil.copy2(self.path, respaldo)
            logger.warning(
                f"JsonMetricsRepository: {self.path} tiene JSON inválido ({e}). "
                f"Respaldado en {respaldo}, se continúa con métricas vacías."
            )
            return []
        return datos if isinstance(datos, list) else []

    def _guardar_crudo(self, registros: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(registros, ensure_ascii=False, indent=4), encoding="utf-8")

    def guardar(self, metrica: Metric) -> Metric:
        registros = self._cargar_crudo()
        registros.append(metrica.model_dump())
        self._guardar_crudo(registros)
        return metrica

    def listar(self) -> list[Metric]:
        return [Metric(**r) for r in self._cargar_crudo()]

    def por_contenido(self, content_id: str) -> list[Metric]:
        return [m for m in self.listar() if m.content_id == content_id]
