"""
Contrato abstracto de publicación — mismo patrón que MemoryRepository
(mh_core/database/memory_repository.py), a propósito. Cuando exista un
adaptador real (YouTube Studio API, etc.), implementa este mismo
contrato — MindHighPipeline no cambia.
"""
from abc import ABC, abstractmethod

from apps.mindhigh.models.content_piece import ContentPiece
from apps.mindhigh.models.publish_result import PublishResult


class PublisherAdapter(ABC):
    @abstractmethod
    def publicar(self, contenido: ContentPiece) -> PublishResult:
        """Publica (o simula publicar) una pieza de contenido y devuelve el resultado."""
