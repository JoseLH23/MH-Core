"""
ContentAgent — agente especializado de MindHigh (vive en apps/, no en
mh_core/, a propósito: depende de ContentQualityPipeline, que es una
capa de aplicación de MindHigh, no del cerebro compartido).

No duplica lógica: reutiliza ContentQualityPipeline completo
(generación con Gemini/Groq/plantillas + evaluación + regeneración),
solo agrega la capa de "objetivo + acción tomada" del agente.
"""
from typing import Optional

from apps.mindhigh.services.content_quality_pipeline import ContentQualityPipeline
from mh_core.agents.base_agent import BaseAgent
from mh_core.utils.logger import logger


class ContentAgent(BaseAgent):
    def __init__(self, quality_pipeline: Optional[ContentQualityPipeline] = None):
        self.quality_pipeline = quality_pipeline or ContentQualityPipeline()

    def name(self) -> str:
        return "content"

    def run(self, brain_report: dict, duration_target: str = "short", style: str = "informativo", **kwargs) -> dict:
        logger.info("ContentAgent: generando contenido con control de calidad.")

        contenido, evaluacion, intentos = self.quality_pipeline.generar_con_calidad(
            brain_report, duration_target, style
        )

        return {
            "agent": self.name(),
            "goal": "Generar contenido de calidad a partir de una oportunidad investigada, regenerando si hace falta.",
            "action_taken": "APROBADO" if evaluacion.aprobado else "NO_APROBADO_TRAS_REINTENTOS",
            "content_id": contenido.id,
            "title": contenido.title,
            "score_total": evaluacion.score_total,
            "attempts": len(intentos),
            "content": contenido.model_dump(),
            "evaluation": evaluacion.model_dump(),
        }
