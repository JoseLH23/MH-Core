"""
MindHighPipeline — conecta el flujo completo de MindHigh, reutilizando
MH-Core real en cada paso:

  1. Investigación real de oportunidades -> mh_core.agents.ResearchAgent.
  2. Generación de contenido CON CONTROL DE CALIDAD ->
     ContentQualityPipeline (Gemini/Groq/plantillas -> QualityEngine ->
     aprobado o regenerar, hasta max_intentos — ver su docstring).
  3. Publicación -> PublisherAdapter inyectable; por defecto
     SimulatedPublisher (modo simulación).
  4. Métricas -> MetricsEngine (honesto: métrica inicial en cero,
     marcada simulated=True cuando el publisher es simulado).

Todo inyectable — se puede testear sin red ni tocar archivos reales.
"""
from typing import Optional

from apps.mindhigh.engines.metrics_engine import MetricsEngine
from apps.mindhigh.publishing.publisher_adapter import PublisherAdapter
from apps.mindhigh.publishing.simulated_publisher import SimulatedPublisher
from apps.mindhigh.services.content_quality_pipeline import ContentQualityPipeline
from mh_core.agents.research_agent import ResearchAgent
from mh_core.utils.logger import logger


class MindHighPipeline:
    def __init__(
        self,
        research_agent: Optional[ResearchAgent] = None,
        quality_pipeline: Optional[ContentQualityPipeline] = None,
        publisher: Optional[PublisherAdapter] = None,
        metrics_engine: Optional[MetricsEngine] = None,
    ):
        self.research_agent = research_agent or ResearchAgent()
        self.quality_pipeline = quality_pipeline or ContentQualityPipeline()
        self.publisher = publisher or SimulatedPublisher()
        self.metrics_engine = metrics_engine or MetricsEngine()

    def run(self, remember: bool = True, duration_target: str = "short", style: str = "informativo") -> dict:
        logger.info("MindHighPipeline: iniciando flujo completo.")

        investigacion = self.research_agent.run(remember=remember)
        brain_report = investigacion.get("report") or {}

        contenido, evaluacion, todas_las_evaluaciones = self.quality_pipeline.generar_con_calidad(
            brain_report, duration_target, style
        )

        # Solo se publica si de verdad quedó aprobado — publicar
        # contenido que no superó el umbral de calidad, aunque sea en
        # modo simulación, iría en contra de todo el propósito de esta
        # fase. Se deja disponible (no se pierde) para revisión manual.
        if evaluacion.aprobado:
            publicacion = self.publisher.publicar(contenido)
            metrica = self.metrics_engine.record_initial(contenido.id, simulated=publicacion.simulated)
        else:
            publicacion = None
            metrica = None
            logger.warning(
                f"MindHighPipeline: contenido NO publicado — no superó el umbral de calidad "
                f"(score_total={evaluacion.score_total})."
            )

        logger.info(
            f"MindHighPipeline: flujo completo — contenido='{contenido.title}' "
            f"(aprobado={evaluacion.aprobado}, score={evaluacion.score_total})."
        )

        return {
            "research": investigacion,
            "content": contenido.model_dump(),
            "quality_evaluation": evaluacion.model_dump(),
            "quality_attempts": [e.model_dump() for e in todas_las_evaluaciones],
            "publish_result": publicacion.model_dump() if publicacion else None,
            "initial_metric": metrica.model_dump() if metrica else None,
        }
