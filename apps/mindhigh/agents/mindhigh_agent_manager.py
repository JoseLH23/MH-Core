"""
Composición de agentes de MindHigh — reutiliza AgentManager de mh_core
tal cual (mismo contrato register/get_agent/run_agent), solo le agrega
los agentes específicos de la app. La cadena real disponible hoy:

    ResearchAgent (mh_core, reutilizado) -> ContentAgent -> VideoAgent

Sigue sin ser la cadena completa de 10 agentes del roadmap (Script,
SEO, Thumbnail... — ver deuda técnica) — es la que hoy tiene motores
reales detrás, sin inventar agentes vacíos.
"""
from mh_core.agents.agent_manager import AgentManager

from apps.mindhigh.agents.content_agent import ContentAgent
from apps.mindhigh.agents.video_agent import VideoAgent


def crear_mindhigh_agent_manager() -> AgentManager:
    manager = AgentManager()  # ya registra ResearchAgent por defecto
    manager.register(ContentAgent())
    manager.register(VideoAgent())
    return manager
