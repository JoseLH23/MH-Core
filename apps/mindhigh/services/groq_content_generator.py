"""
GroqContentGenerator — respaldo real cuando Gemini falla o se agota
su cuota del nivel gratis.

No se agregó el SDK oficial `groq` como dependencia nueva: la API de
Groq es compatible con el formato de OpenAI sobre HTTP normal, y
`requests` ya es una dependencia real del proyecto — se reutiliza en
vez de sumar un paquete más.

Mismo patrón que GeminiContentGenerator: `intentar()` (sin fallback,
usado por la cadena) y `generar()` (standalone, cae a plantillas).
"""
import os
import uuid
from typing import Optional

import requests

from apps.mindhigh.models.content_piece import ContentPiece
from apps.mindhigh.services.content_generator import ContentGenerator
from apps.mindhigh.services.llm_prompt import construir_prompt, separar_titulo_y_guion
from mh_core.utils.logger import logger

MODELO_POR_DEFECTO = "llama-3.3-70b-versatile"  # modelo insignia del nivel gratis de Groq (jul 2026)
URL_GROQ = "https://api.groq.com/openai/v1/chat/completions"


class GroqContentGenerator:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, sesion_http=None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.model = model or os.environ.get("GROQ_MODEL", MODELO_POR_DEFECTO)
        # `sesion_http` inyectable — los tests nunca llaman a la API real.
        self._sesion_http = sesion_http or requests
        self._fallback = ContentGenerator()

    def intentar(self, brain_report: dict) -> Optional[ContentPiece]:
        """Solo Groq. None si no hay key o la llamada falla — nunca
        lanza, nunca silencioso."""
        if not self.api_key:
            logger.warning("GroqContentGenerator: no hay GROQ_API_KEY.")
            return None

        resumen = brain_report.get("executive_summary", {}) or {}
        topic = resumen.get("topic") or "tema sin especificar"

        try:
            respuesta = self._sesion_http.post(
                URL_GROQ,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": construir_prompt(brain_report)}],
                },
                timeout=30,
            )
            respuesta.raise_for_status()
            datos = respuesta.json()
            texto = (datos["choices"][0]["message"]["content"] or "").strip()

            if not texto:
                logger.warning("GroqContentGenerator: Groq devolvió una respuesta vacía.")
                return None

            titulo, guion = separar_titulo_y_guion(texto, topic, "GroqContentGenerator")

            logger.info(f"GroqContentGenerator: contenido generado con Groq ({self.model}) para '{topic}'.")
            return ContentPiece(
                id=str(uuid.uuid4()),
                topic=topic,
                title=titulo,
                script=guion,
                source_recommendation=resumen.get("final_recommendation"),
            )

        except Exception as e:
            # Nunca silencioso: se registra el motivo real (429 por
            # cuota agotada, red caída, key inválida, respuesta con
            # forma inesperada, etc.)
            logger.warning(f"GroqContentGenerator: falló la llamada a Groq ({e}).")
            return None

    def generar(self, brain_report: dict) -> ContentPiece:
        resultado = self.intentar(brain_report)
        if resultado is not None:
            return resultado
        logger.warning("GroqContentGenerator: usando generador por plantillas.")
        return self._fallback.generar(brain_report)
