import pytest

from mh_core.agents.agent_manager import AgentManager
from mh_core.agents.base_agent import BaseAgent
from mh_core.agents.research_agent import ResearchAgent


class _AutomationEngineFalso:
    """Doble de AutomationEngine — no toca red ni archivo real."""

    def __init__(self, brain_report):
        self.brain_report = brain_report
        self.llamadas = []

    def run_once(self, remember=True):
        self.llamadas.append(remember)
        return {"brain_report": self.brain_report}


class _AutomationEngineQueFalla:
    def run_once(self, remember=True):
        raise RuntimeError("pipeline falló (simulado)")


BRAIN_REPORT_EJEMPLO = {
    "executive_summary": {
        "topic": "inteligencia artificial",
        "final_recommendation": "PRODUCIR",
        "confidence": "HIGH",
        "success_probability": 82.5,
    }
}


# --- ResearchAgent ------------------------------------------------------


def test_research_agent_devuelve_reporte_estructurado():
    motor_falso = _AutomationEngineFalso(BRAIN_REPORT_EJEMPLO)
    agente = ResearchAgent(automation_engine=motor_falso)

    reporte = agente.run()

    assert reporte["agent"] == "research"
    assert reporte["action_taken"] == "PRODUCIR"
    assert reporte["topic"] == "inteligencia artificial"
    assert reporte["confidence"] == "HIGH"
    assert reporte["report"] == BRAIN_REPORT_EJEMPLO


def test_research_agent_propaga_remember_al_motor():
    motor_falso = _AutomationEngineFalso(BRAIN_REPORT_EJEMPLO)
    agente = ResearchAgent(automation_engine=motor_falso)

    agente.run(remember=False)

    assert motor_falso.llamadas == [False]


def test_research_agent_sin_datos_no_truena():
    motor_falso = _AutomationEngineFalso({})
    agente = ResearchAgent(automation_engine=motor_falso)

    reporte = agente.run()

    assert reporte["action_taken"] == "SIN_DATOS"


def test_research_agent_propaga_error_real_del_motor():
    agente = ResearchAgent(automation_engine=_AutomationEngineQueFalla())

    with pytest.raises(RuntimeError):
        agente.run()


# --- AgentManager ---------------------------------------------------------


def test_agent_manager_registra_research_agent_por_defecto():
    manager = AgentManager()
    assert "research" in manager.list_agents()


def test_agent_manager_run_agent_ejecuta_el_correcto():
    manager = AgentManager()
    manager.register(_AgenteDePrueba())

    reporte = manager.run_agent("prueba")

    assert reporte["agent"] == "prueba"


def test_agent_manager_agente_inexistente_lanza_value_error():
    manager = AgentManager()

    with pytest.raises(ValueError):
        manager.run_agent("no-existe")


def test_agent_manager_nombre_no_distingue_mayusculas():
    manager = AgentManager()
    manager.register(_AgenteDePrueba())

    assert manager.get_agent("PRUEBA") is not None


class _AgenteDePrueba(BaseAgent):
    def name(self) -> str:
        return "prueba"

    def run(self, **kwargs) -> dict:
        return {"agent": "prueba", "action_taken": "NINGUNA"}
