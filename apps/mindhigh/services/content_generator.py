"""
ContentGenerator — v1 honesto: genera título y guion base a partir del
`brain_report` REAL de MH-Core (razones, acciones recomendadas,
patrones detectados), usando plantillas — NO usa ningún modelo de
lenguaje todavía (no hay ninguna API key de LLM configurada en el
proyecto). No se inventa una integración de IA falsa.

Cuando se decida qué proveedor de LLM usar, este archivo es el único
que hay que reemplazar — MindHighPipeline no sabe ni le importa cómo
se genera el contenido, solo que recibe un ContentPiece.
"""
import uuid

from apps.mindhigh.models.content_piece import ContentPiece


class ContentGenerator:
    def generar(self, brain_report: dict) -> ContentPiece:
        resumen = brain_report.get("executive_summary", {}) or {}
        razones = brain_report.get("reasoning", []) or []
        acciones = brain_report.get("recommended_actions", []) or []

        topic = resumen.get("topic") or "tema sin especificar"
        titulo = self._generar_titulo(topic, resumen)
        guion = self._generar_guion(topic, resumen, razones, acciones)

        return ContentPiece(
            id=str(uuid.uuid4()),
            topic=topic,
            title=titulo,
            script=guion,
            source_recommendation=resumen.get("final_recommendation"),
        )

    def _generar_titulo(self, topic: str, resumen: dict) -> str:
        canal_recomendado = resumen.get("recommended_channel")
        base = topic.split(":")[0].strip().capitalize()
        if canal_recomendado:
            return f"{base}: lo que nadie te explicó (inspirado en el estilo de {canal_recomendado})"
        return f"{base}: lo que nadie te explicó"

    def _generar_guion(self, topic: str, resumen: dict, razones: list, acciones: list) -> str:
        partes = [
            f"GUION BASE — tema: {topic}",
            "",
            "Gancho inicial (primeros 3 segundos):",
            f"  Plantea la pregunta central detrás de '{topic}' de forma directa y curiosa.",
            "",
            "Por qué MH Core recomienda este tema ahora:",
        ]
        for razon in razones:
            partes.append(f"  - {razon}")

        partes += ["", "Acciones sugeridas para la producción:"]
        for accion in acciones:
            partes.append(f"  - {accion}")

        partes += [
            "",
            "Cierre sugerido:",
            "  Resume la idea principal y da un llamado a la acción claro (comentar, seguir, ver el siguiente video).",
            "",
            "NOTA: guion generado por plantilla (v1), no por un modelo de lenguaje todavía.",
        ]
        return "\n".join(partes)
