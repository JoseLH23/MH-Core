"""
Reglas configurables para decidir si una oportunidad es lo bastante
fuerte como para notificar. Con valores por defecto razonables, pero
inyectables/configurables — no hardcodeadas sin forma de ajustarlas.
"""
from dataclasses import dataclass


@dataclass
class NotificationRules:
    umbral_probabilidad: float = 70.0  # success_probability mínima (0-100)
    confidence_requerida: tuple[str, ...] = ("HIGH",)
    prioridad_requerida: tuple[str, ...] = ("HIGH",)
    # Basta con que UNA de las 3 condiciones se cumpla, no las 3 a
    # la vez — una oportunidad con confianza HIGH pero probabilidad
    # 65% sigue siendo genuinamente fuerte.
    modo: str = "cualquiera"  # "cualquiera" | "todas"

    def cumple(self, success_probability: float, confidence: str | None, priority: str | None) -> bool:
        cumple_probabilidad = success_probability >= self.umbral_probabilidad
        cumple_confianza = (confidence or "").upper() in self.confidence_requerida
        cumple_prioridad = (priority or "").upper() in self.prioridad_requerida

        condiciones = [cumple_probabilidad, cumple_confianza, cumple_prioridad]
        if self.modo == "todas":
            return all(condiciones)
        return any(condiciones)
