"""
GeminiContentGenerator — generación real con Gemini.

SDK: `google-genai` (el nuevo, unificado — `google.generativeai` está
deprecado desde 2025, no se usa aquí a propósito).

Expone dos formas de uso:
  - `intentar()`: SOLO Gemini, sin fallback — devuelve None si no hay
    key o si falla. La usa AIContentGenerator para encadenar a Groq
    antes de caer a plantillas.
  - `generar()`: uso standalone — si `intentar()` devuelve None, cae
    directo a plantillas (mismo comportamiento que antes de esta fase).
"""
import os
import uuid
from typing import Optional

from google import genai

from apps.mindhigh.models.content_piece import ContentPiece
from apps.mindhigh.services.content_generator import ContentGenerator
from apps.mindhigh.services.llm_prompt import construir_prompt, separar_titulo_y_guion
from mh_core.utils.logger import logger
from mh_core.utils.retry import reintentar_con_backoff

MODELO_POR_DEFECTO = "gemini-3.5-flash"  # nivel gratis, buen balance velocidad/calidad (jul 2026)


class GeminiContentGenerator:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        cliente=None,
        reintentos: int = 3,
        espera_inicial: float = 1.0,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model or os.environ.get("GEMINI_MODEL", MODELO_POR_DEFECTO)
        # `cliente` inyectable a propósito — los tests nunca llaman a
        # la API real de Gemini, ni siquiera con una key real.
        self._cliente = cliente
        self._fallback = ContentGenerator()
        self.reintentos = reintentos
        self.espera_inicial = espera_inicial

    def _obtener_cliente(self):
        if self._cliente is not None:
            return self._cliente
        return genai.Client(api_key=self.api_key)

    def intentar(self, brain_report: dict) -> Optional[ContentPiece]:
        """Solo Gemini. None si no hay key, la respuesta viene vacía,
        o la llamada falla — nunca lanza, nunca silencioso (todo se
        registra en el log antes de devolver None)."""
        if not self.api_key:
            logger.warning("GeminiContentGenerator: no hay GEMINI_API_KEY.")
            return None

        resumen = brain_report.get("executive_summary", {}) or {}
        topic = resumen.get("topic") or "tema sin especificar"

        try:
            cliente = self._obtener_cliente()
            respuesta = reintentar_con_backoff(
                lambda: cliente.models.generate_content(model=self.model, contents=construir_prompt(brain_report)),
                intentos=self.reintentos,
                espera_inicial=self.espera_inicial,
                nombre="Gemini generate_content",
            )
            texto = (respuesta.text or "").strip()

            if not texto:
                logger.warning("GeminiContentGenerator: Gemini devolvió una respuesta vacía.")
                return None

            titulo, guion = separar_titulo_y_guion(texto, topic, "GeminiContentGenerator")

            logger.info(f"GeminiContentGenerator: contenido generado con Gemini ({self.model}) para '{topic}'.")
            return ContentPiece(
                id=str(uuid.uuid4()),
                topic=topic,
                title=titulo,
                script=guion,
                source_recommendation=resumen.get("final_recommendation"),
            )

        except Exception as e:
            # Nunca silencioso: se registra el motivo real (cuota
            # agotada del nivel gratis, red caída, key inválida, etc.)
            logger.warning(f"GeminiContentGenerator: falló la llamada a Gemini ({e}).")
            return None

    def generar(self, brain_report: dict) -> ContentPiece:
        resultado = self.intentar(brain_report)
        if resultado is not None:
            return resultado
        logger.warning("GeminiContentGenerator: usando generador por plantillas.")
        return self._fallback.generar(brain_report)
