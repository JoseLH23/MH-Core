"""
AIContentGenerator — la cadena real pedida: Gemini primero (proveedor
principal), Groq como respaldo si Gemini falla o no hay key, y el
generador por plantillas como última red de seguridad (nunca se cae
el pipeline por completo).

Todo registrado en el log: siempre queda claro cuál de los tres
proveedores generó cada pieza de contenido.
"""
from typing import Optional

from apps.mindhigh.models.content_piece import ContentPiece
from apps.mindhigh.services.content_generator import ContentGenerator
from apps.mindhigh.services.gemini_content_generator import GeminiContentGenerator
from apps.mindhigh.services.groq_content_generator import GroqContentGenerator
from mh_core.utils.logger import logger


class AIContentGenerator:
    def __init__(
        self,
        gemini: Optional[GeminiContentGenerator] = None,
        groq: Optional[GroqContentGenerator] = None,
        fallback: Optional[ContentGenerator] = None,
    ):
        self.gemini = gemini or GeminiContentGenerator()
        self.groq = groq or GroqContentGenerator()
        self.fallback = fallback or ContentGenerator()

    def generar(self, brain_report: dict, duration_target: str = "short", style: str = "informativo") -> ContentPiece:
        resultado = self.gemini.intentar(brain_report, duration_target, style)
        if resultado is not None:
            return resultado

        logger.info("AIContentGenerator: Gemini no disponible — probando Groq como respaldo.")
        resultado = self.groq.intentar(brain_report, duration_target, style)
        if resultado is not None:
            return resultado

        logger.warning("AIContentGenerator: ni Gemini ni Groq disponibles — usando generador por plantillas.")
        return self.fallback.generar(brain_report, duration_target, style)
