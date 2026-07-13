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
from apps.mindhigh.services.llm_prompt import parsear_respuesta_estructurada
from apps.mindhigh.services.prompt_manager import prompt_manager
from mh_core.utils.logger import logger
from mh_core.utils.retry import reintentar_con_backoff

MODELO_POR_DEFECTO = "llama-3.3-70b-versatile"  # modelo insignia del nivel gratis de Groq (jul 2026)
URL_GROQ = "https://api.groq.com/openai/v1/chat/completions"


class GroqContentGenerator:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        sesion_http=None,
        reintentos: int = 3,
        espera_inicial: float = 1.0,
    ):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.model = model or os.environ.get("GROQ_MODEL", MODELO_POR_DEFECTO)
        # `sesion_http` inyectable — los tests nunca llaman a la API real.
        self._sesion_http = sesion_http or requests
        self._fallback = ContentGenerator()
        # Inyectables para que los tests no tengan que dormir segundos
        # reales esperando reintentos que saben que van a fallar.
        self.reintentos = reintentos
        self.espera_inicial = espera_inicial

    def intentar(self, brain_report: dict, duration_target: str = "short", style: str = "informativo") -> Optional[ContentPiece]:
        """Solo Groq. None si no hay key o la llamada falla — nunca
        lanza, nunca silencioso."""
        if not self.api_key:
            logger.warning("GroqContentGenerator: no hay GROQ_API_KEY.")
            return None

        resumen = brain_report.get("executive_summary", {}) or {}
        topic = resumen.get("topic") or "tema sin especificar"

        try:
            def _pedir():
                resp = self._sesion_http.post(
                    URL_GROQ,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "user", "content": prompt_manager.render("content_generation", brain_report=brain_report, duration_target=duration_target, style=style)}
                        ],
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                return resp

            respuesta = reintentar_con_backoff(
                _pedir, intentos=self.reintentos, espera_inicial=self.espera_inicial, nombre="Groq chat.completions"
            )
            datos = respuesta.json()
            texto = (datos["choices"][0]["message"]["content"] or "").strip()

            if not texto:
                logger.warning("GroqContentGenerator: Groq devolvió una respuesta vacía.")
                return None

            campos = parsear_respuesta_estructurada(texto, topic, "GroqContentGenerator")

            logger.info(f"GroqContentGenerator: contenido generado con Groq ({self.model}) para '{topic}'.")
            return ContentPiece(
                id=str(uuid.uuid4()),
                topic=topic,
                source_recommendation=resumen.get("final_recommendation"),
                duration_target=duration_target,
                style=style,
                **campos,
            )

        except Exception as e:
            # Nunca silencioso: se registra el motivo real (429 por
            # cuota agotada, red caída, key inválida, respuesta con
            # forma inesperada, etc.)
            logger.warning(f"GroqContentGenerator: falló la llamada a Groq ({e}).")
            return None

    def generar(self, brain_report: dict, duration_target: str = "short", style: str = "informativo") -> ContentPiece:
        resultado = self.intentar(brain_report, duration_target, style)
        if resultado is not None:
            return resultado
        logger.warning("GroqContentGenerator: usando generador por plantillas.")
        return self._fallback.generar(brain_report)
