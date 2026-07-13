"""
MindHighPipeline — conecta el flujo completo de MindHigh, reutilizando
MH-Core real en cada paso (no una copia ni una simulación de MH-Core):

  1. Investigación real de oportunidades -> mh_core.agents.ResearchAgent
     (que ya reutiliza AutomationEngine -> Orchestrator -> todos los
     engines reales, incluido MemoryEngine para "aprendizaje continuo"
     — no se duplica un segundo sistema de memoria aquí).
  2. Generación de contenido -> ContentGenerator (plantillas v1, ver
     su docstring sobre por qué no es IA todavía).
  3. Publicación -> PublisherAdapter inyectable; por defecto
     SimulatedPublisher (modo simulación pedido explícitamente).
  4. Métricas -> MetricsEngine (honesto: métrica inicial en cero,
     marcada simulated=True cuando el publisher es simulado).

Todo inyectable — ningún componente depende de una instancia global
oculta, se puede testear sin red ni tocar archivos reales.
"""
from typing import Optional

from apps.mindhigh.engines.metrics_engine import MetricsEngine
from apps.mindhigh.publishing.publisher_adapter import PublisherAdapter
from apps.mindhigh.publishing.simulated_publisher import SimulatedPublisher
from apps.mindhigh.services.ai_content_generator import AIContentGenerator
from mh_core.agents.research_agent import ResearchAgent
from mh_core.utils.logger import logger


class MindHighPipeline:
    def __init__(
        self,
        research_agent: Optional[ResearchAgent] = None,
        content_generator=None,
        publisher: Optional[PublisherAdapter] = None,
        metrics_engine: Optional[MetricsEngine] = None,
    ):
        self.research_agent = research_agent or ResearchAgent()
        # AIContentGenerator ya trae su propia cadena de respaldo
        # (Gemini -> Groq -> plantillas) — no hace falta duplicar esa
        # lógica aquí.
        self.content_generator = content_generator or AIContentGenerator()
        self.publisher = publisher or SimulatedPublisher()
        self.metrics_engine = metrics_engine or MetricsEngine()

    def run(self, remember: bool = True) -> dict:
        logger.info("MindHighPipeline: iniciando flujo completo.")

        investigacion = self.research_agent.run(remember=remember)
        brain_report = investigacion.get("report") or {}

        contenido = self.content_generator.generar(brain_report)
        publicacion = self.publisher.publicar(contenido)
        metrica = self.metrics_engine.record_initial(contenido.id, simulated=publicacion.simulated)

        logger.info(
            f"MindHighPipeline: flujo completo — contenido='{contenido.title}' "
            f"publicado en {publicacion.platform} (simulado={publicacion.simulated})."
        )

        return {
            "research": investigacion,
            "content": contenido.model_dump(),
            "publish_result": publicacion.model_dump(),
            "initial_metric": metrica.model_dump(),
        }
