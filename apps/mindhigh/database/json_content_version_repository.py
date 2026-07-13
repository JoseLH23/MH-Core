"""
Implementación JSON de ContentVersionRepository — cada versión
generada (aprobada o no) se guarda junto con su evaluación, para
auditoría y para poder comparar qué mejoró entre regeneraciones.
Mismo manejo real de archivo corrupto/vacío que el resto del proyecto.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

from apps.mindhigh.database.content_version_repository import ContentVersionRepository
from apps.mindhigh.models.content_piece import ContentPiece
from apps.mindhigh.models.quality_evaluation import QualityEvaluation
from mh_core.utils.logger import logger


class JsonContentVersionRepository(ContentVersionRepository):
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
                f"JsonContentVersionRepository: {self.path} tiene JSON inválido ({e}). "
                f"Respaldado en {respaldo}, se continúa con historial vacío."
            )
            return []
        return datos if isinstance(datos, list) else []

    def _guardar_crudo(self, registros: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(registros, ensure_ascii=False, indent=4), encoding="utf-8")

    def guardar(self, contenido: ContentPiece, evaluacion: QualityEvaluation) -> None:
        registros = self._cargar_crudo()
        registros.append({"content": contenido.model_dump(), "evaluation": evaluacion.model_dump()})
        self._guardar_crudo(registros)

    def historial(self, content_base_id: str) -> list[tuple[ContentPiece, QualityEvaluation]]:
        resultado = []
        for registro in self._cargar_crudo():
            pieza = ContentPiece(**registro["content"])
            base_id = pieza.parent_id or pieza.id
            if base_id == content_base_id or pieza.id == content_base_id:
                resultado.append((pieza, QualityEvaluation(**registro["evaluation"])))
        return resultado

    def obtener_por_id(self, content_id: str) -> ContentPiece | None:
        for registro in self._cargar_crudo():
            if registro["content"].get("id") == content_id:
                return ContentPiece(**registro["content"])
        return None
