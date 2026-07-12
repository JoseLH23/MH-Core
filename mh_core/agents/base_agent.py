"""
Clase base para todos los agentes de MH Core — mismo patrón que
BasePlugin (mh_core/plugins/base_plugin.py), a propósito, para que el
proyecto tenga una sola forma de definir "algo registrable y ejecutable"
en vez de dos convenciones distintas.
"""
from abc import ABC, abstractmethod


class BaseAgent(ABC):
    @abstractmethod
    def name(self) -> str:
        """Nombre único del agente, usado por AgentManager para registrarlo."""

    @abstractmethod
    def run(self, **kwargs) -> dict:
        """Ejecuta el objetivo del agente y devuelve un reporte estructurado."""
