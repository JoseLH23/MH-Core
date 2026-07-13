"""
GeminiContentGenerator — generación de contenido real con IA (Gemini),
la pieza que estaba bloqueada por presupuesto (ver Master Plan,
Sección 8 — José ya configuró GEMINI_API_KEY en .env).

SDK: `google-genai` (el nuevo, unificado — `google.generativeai` está
deprecado desde 2025, no se usa aquí a propósito).

FALLBACK HONESTO, mismo patrón que YouTubeResearchEngine/ResearchEngine
en mh_core: si no hay GEMINI_API_KEY, o la llamada a la API falla por
cualquier motivo (red, cuota agotada del nivel gratis, etc.), se cae
al ContentGenerator por plantillas — nunca se rompe el pipeline, y
siempre queda registrado en el log CUÁL de los dos generó el contenido.
"""
import os
from typing import Optional

from google import genai

from apps.mindhigh.models.content_piece import ContentPiece
from apps.mindhigh.services.content_generator import ContentGenerator
from mh_core.utils.logger import logger

MODELO_POR_DEFECTO = "gemini-3.5-flash"  # nivel gratis, buen balance velocidad/calidad (jul 2026)


class GeminiContentGenerator:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, cliente=None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model or os.environ.get("GEMINI_MODEL", MODELO_POR_DEFECTO)
        # `cliente` inyectable a propósito — los tests nunca llaman a
        # la API real de Gemini, ni siquiera con una key real.
        self._cliente = cliente
        self._fallback = ContentGenerator()

    def _obtener_cliente(self):
        if self._cliente is not None:
            return self._cliente
        return genai.Client(api_key=self.api_key)

    def generar(self, brain_report: dict) -> ContentPiece:
        if not self.api_key:
            logger.warning("GeminiContentGenerator: no hay GEMINI_API_KEY. Usando generador por plantillas.")
            return self._fallback.generar(brain_report)

        try:
            resumen = brain_report.get("executive_summary", {}) or {}
            topic = resumen.get("topic") or "tema sin especificar"
            prompt = self._construir_prompt(brain_report)

            cliente = self._obtener_cliente()
            respuesta = cliente.models.generate_content(model=self.model, contents=prompt)
            texto = (respuesta.text or "").strip()

            if not texto:
                logger.warning("GeminiContentGenerator: Gemini devolvió una respuesta vacía. Usando plantillas.")
                return self._fallback.generar(brain_report)

            titulo, guion = self._separar_titulo_y_guion(texto, topic)

            import uuid

            logger.info(f"GeminiContentGenerator: contenido generado con Gemini ({self.model}) para '{topic}'.")
            return ContentPiece(
                id=str(uuid.uuid4()),
                topic=topic,
                title=titulo,
                script=guion,
                source_recommendation=resumen.get("final_recommendation"),
            )

        except Exception as e:
            # Nunca silencioso: se registra el motivo real antes de
            # caer al fallback (cuota agotada del nivel gratis, red
            # caída, key inválida, lo que sea).
            logger.warning(f"GeminiContentGenerator: falló la llamada a Gemini ({e}). Usando plantillas.")
            return self._fallback.generar(brain_report)

    def _construir_prompt(self, brain_report: dict) -> str:
        resumen = brain_report.get("executive_summary", {}) or {}
        razones = brain_report.get("reasoning", []) or []
        acciones = brain_report.get("recommended_actions", []) or []

        return (
            "Eres un guionista experto en contenido de YouTube en español.\n"
            f"Tema recomendado: {resumen.get('topic', 'sin especificar')}\n"
            f"Razones de la recomendación: {'; '.join(razones) if razones else 'ninguna'}\n"
            f"Acciones sugeridas: {'; '.join(acciones) if acciones else 'ninguna'}\n\n"
            "Escribe:\n"
            "1) Una sola línea con el TÍTULO del video (sin comillas, sin la palabra 'Título:').\n"
            "2) Un guion base breve (gancho inicial, 2-3 puntos clave, cierre con llamado a la acción).\n\n"
            "Formato de tu respuesta, exacto:\n"
            "TITULO: <el título aquí>\n"
            "GUION:\n<el guion aquí>"
        )

    def _separar_titulo_y_guion(self, texto: str, topic: str) -> tuple[str, str]:
        """Parseo tolerante: si Gemini no siguió el formato exacto
        pedido, no se rompe — se usa todo el texto como guion y un
        título genérico basado en el tema real."""
        if "TITULO:" in texto and "GUION:" in texto:
            despues_de_titulo = texto.split("TITULO:", 1)[1]
            partes = despues_de_titulo.split("GUION:", 1)
            if len(partes) == 2:
                parte_titulo, parte_guion = partes[0].strip(), partes[1].strip()
                if parte_titulo and parte_guion:
                    return parte_titulo, parte_guion

        logger.info("GeminiContentGenerator: la respuesta no siguió el formato TITULO/GUION esperado; se usa tal cual.")
        return f"{topic.capitalize()} (generado por IA)", texto
