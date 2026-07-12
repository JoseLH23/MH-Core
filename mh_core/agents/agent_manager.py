"""
AgentManager — mismo patrón que PluginManager
(mh_core/plugins/plugin_manager.py), a propósito.
"""
from mh_core.agents.base_agent import BaseAgent
from mh_core.agents.research_agent import ResearchAgent


class AgentManager:
    def __init__(self):
        self.agents: dict[str, BaseAgent] = {}
        self.register(ResearchAgent())

    def register(self, agent: BaseAgent) -> None:
        self.agents[agent.name().lower()] = agent

    def get_agent(self, name: str) -> BaseAgent | None:
        return self.agents.get(name.lower())

    def list_agents(self) -> list[str]:
        return list(self.agents.keys())

    def run_agent(self, name: str, **kwargs) -> dict:
        agent = self.get_agent(name)
        if agent is None:
            raise ValueError(f"Agente '{name}' no encontrado. Disponibles: {self.list_agents()}")
        return agent.run(**kwargs)
