from abc import ABC, abstractmethod

from apps.mindhigh.models.content_piece import ContentPiece
from apps.mindhigh.models.quality_evaluation import QualityEvaluation


class ContentVersionRepository(ABC):
    @abstractmethod
    def guardar(self, contenido: ContentPiece, evaluacion: QualityEvaluation) -> None: ...

    @abstractmethod
    def historial(self, content_base_id: str) -> list[tuple[ContentPiece, QualityEvaluation]]:
        """Todas las versiones generadas para un mismo `content_base_id`
        (el id de la primera versión — las regeneraciones comparten ese
        linaje via `parent_id`), en orden de creación."""

    @abstractmethod
    def obtener_por_id(self, content_id: str) -> ContentPiece | None:
        """La pieza de contenido exacta con ese id (cualquier versión)."""
