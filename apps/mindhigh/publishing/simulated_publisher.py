"""
SimulatedPublisher — el modo pedido explícitamente ("adaptadores
seguros o modo simulación"): NUNCA llama a ninguna red social real.
Genera una URL falsa reconocible como simulada y registra la
publicación en el log real, para poder probar el flujo completo de
MindHigh sin riesgo de publicar algo de verdad por accidente.
"""
import uuid

from apps.mindhigh.models.content_piece import ContentPiece
from apps.mindhigh.models.publish_result import PublishResult
from apps.mindhigh.publishing.publisher_adapter import PublisherAdapter
from mh_core.utils.logger import logger


class SimulatedPublisher(PublisherAdapter):
    def __init__(self, platform: str = "youtube"):
        self.platform = platform

    def publicar(self, contenido: ContentPiece) -> PublishResult:
        url_simulada = f"https://simulado.mindhigh.local/{self.platform}/{uuid.uuid4()}"

        logger.info(
            f"SimulatedPublisher: publicación SIMULADA de '{contenido.title}' "
            f"en {self.platform} — {url_simulada}"
        )

        return PublishResult(
            content_id=contenido.id,
            platform=self.platform,
            simulated=True,
            url=url_simulada,
        )
