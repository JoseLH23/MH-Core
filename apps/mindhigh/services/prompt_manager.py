"""
PromptManager — punto único de gobierno de todos los prompts del
proyecto, con plantillas registradas por nombre en vez de que cada
generador arme su propio texto de forma dispersa.

Reutiliza construir_prompt() de llm_prompt.py tal cual (no se duplica
esa lógica ya probada) — este manager es la CAPA de gobierno encima,
no un reemplazo. Nuevas plantillas (ej. un prompt de evaluación con
IA, cuando se decida esa fase) se registran aquí sin tocar a los
generadores que ya las consumen por nombre.
"""
from typing import Callable

from apps.mindhigh.services.llm_prompt import construir_prompt


class PromptManager:
    def __init__(self):
        self._plantillas: dict[str, Callable[..., str]] = {}
        self.registrar("content_generation", self._plantilla_generacion_contenido)

    def registrar(self, nombre: str, funcion: Callable[..., str]) -> None:
        self._plantillas[nombre] = funcion

    def render(self, nombre: str, **kwargs) -> str:
        if nombre not in self._plantillas:
            raise ValueError(f"Plantilla de prompt '{nombre}' no registrada. Disponibles: {list(self._plantillas)}")
        return self._plantillas[nombre](**kwargs)

    def listar_plantillas(self) -> list[str]:
        return list(self._plantillas.keys())

    @staticmethod
    def _plantilla_generacion_contenido(brain_report: dict, duration_target: str = "short", style: str = "informativo") -> str:
        return construir_prompt(brain_report, duration_target, style)


# Instancia compartida — mismo patrón que otros singletons de módulo
# del proyecto (ej. AgentManager en las rutas).
prompt_manager = PromptManager()
