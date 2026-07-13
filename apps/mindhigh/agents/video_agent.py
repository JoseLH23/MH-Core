"""
VideoAgent — agente especializado de MindHigh. Reutiliza
VideoProductionEngine completo — solo produce video de contenido YA
aprobado (la restricción real ya vive en VideoProductionEngine.iniciar_render,
no se duplica aquí).
"""
from typing import Optional

from apps.mindhigh.database.json_content_version_repository import JsonContentVersionRepository
from apps.mindhigh.database.content_version_repository import ContentVersionRepository
from apps.mindhigh.video.video_production_engine import VideoProductionEngine
from mh_core.agents.base_agent import BaseAgent
from mh_core.core.config import DATABASE_DIR
from mh_core.utils.logger import logger


class VideoAgent(BaseAgent):
    def __init__(
        self,
        video_engine: Optional[VideoProductionEngine] = None,
        content_repository: Optional[ContentVersionRepository] = None,
    ):
        self.video_engine = video_engine or VideoProductionEngine()
        self.content_repository = content_repository or JsonContentVersionRepository(
            DATABASE_DIR / "mindhigh" / "content_versions.json"
        )

    def name(self) -> str:
        return "video"

    def run(self, content_id: str, **kwargs) -> dict:
        logger.info(f"VideoAgent: iniciando producción de video para content_id={content_id}.")

        contenido = self.content_repository.obtener_por_id(content_id)
        if contenido is None:
            return {"agent": self.name(), "action_taken": "CONTENIDO_NO_ENCONTRADO", "content_id": content_id}

        if contenido.status != "aprobado":
            return {
                "agent": self.name(),
                "goal": "Producir video real solo de contenido ya aprobado por Quality Engine.",
                "action_taken": "RECHAZADO_NO_APROBADO",
                "content_id": content_id,
            }

        render = self.video_engine.iniciar_render(content_id, contenido.title, contenido.script)
        return {
            "agent": self.name(),
            "goal": "Producir video real solo de contenido ya aprobado por Quality Engine.",
            "action_taken": "RENDER_INICIADO",
            "render_id": render.id,
            "render_status": render.status,
        }
