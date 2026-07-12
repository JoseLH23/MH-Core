"""
ResearchAgent — el primer agente real de MH Core.

No duplica nada: reutiliza AutomationEngine.run_once() (que a su vez
reutiliza el Orchestrator, que reutiliza los engines de Ranking/
Pattern/Decision/Learning/Prediction/Brain). Este agente solo agrega
la capa de "objetivo + acción tomada" — la interpretación de que
correr el pipeline completo ES la forma en que este agente persigue
su objetivo (investigar y decidir la mejor oportunidad de contenido).
"""
from typing import Optional

from mh_core.agents.base_agent import BaseAgent
from mh_core.engines.automation_engine import AutomationEngine
from mh_core.utils.logger import logger


class ResearchAgent(BaseAgent):
    def __init__(self, automation_engine: Optional[AutomationEngine] = None):
        self.automation_engine = automation_engine or AutomationEngine()

    def name(self) -> str:
        return "research"

    def run(self, remember: bool = True, **kwargs) -> dict:
        logger.info("ResearchAgent: iniciando investigación autónoma.")

        resultado = self.automation_engine.run_once(remember=remember)
        brain_report = resultado.get("brain_report", {}) or {}
        resumen_ejecutivo = brain_report.get("executive_summary", {}) or {}

        reporte = {
            "agent": self.name(),
            "goal": "Investigar tendencias reales y decidir la mejor oportunidad de contenido.",
            "action_taken": resumen_ejecutivo.get("final_recommendation", "SIN_DATOS"),
            "topic": resumen_ejecutivo.get("topic"),
            "confidence": resumen_ejecutivo.get("confidence"),
            "success_probability": resumen_ejecutivo.get("success_probability"),
            "report": brain_report,
        }

        logger.info(f"ResearchAgent: acción tomada = {reporte['action_taken']}.")
        return reporte
