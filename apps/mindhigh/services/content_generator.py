"""
ContentGenerator — v1 honesto: genera contenido estructurado a partir
del `brain_report` REAL de MH-Core, usando plantillas — NO usa ningún
modelo de lenguaje (es la red de seguridad final si Gemini y Groq
fallan/no hay key, ver AIContentGenerator).

Fase "calidad del contenido": ahora produce la misma salida
estructurada completa que Gemini/Groq (gancho, descripción, hashtags,
CTA), para que QualityEngine pueda evaluar cualquier fuente por igual
sin tratar el fallback como un caso especial.
"""
import uuid

from apps.mindhigh.models.content_piece import ContentPiece


class ContentGenerator:
    def generar(self, brain_report: dict, duration_target: str = "short", style: str = "informativo") -> ContentPiece:
        resumen = brain_report.get("executive_summary", {}) or {}
        razones = brain_report.get("reasoning", []) or []
        acciones = brain_report.get("recommended_actions", []) or []

        topic = resumen.get("topic") or "tema sin especificar"
        base = topic.split(":")[0].strip().capitalize()
        stopwords = {"en", "el", "la", "los", "las", "de", "del", "y", "a", "con", "para", "un", "una"}
        palabras_hashtag = [p.strip(".,") for p in base.split() if p.strip(".,").lower() not in stopwords]

        return ContentPiece(
            id=str(uuid.uuid4()),
            topic=topic,
            title=self._generar_titulo(topic, resumen),
            hook=f"¿Sabías que {topic} podría cambiar lo que creías saber? Te lo explico.",
            script=self._generar_guion(topic, resumen, razones, acciones),
            description=f"En este video hablamos de {topic}. {'; '.join(razones[:2]) if razones else ''}".strip(),
            hashtags=[f"#{palabra}" for palabra in palabras_hashtag[:3]] or ["#contenido"],
            cta="Si te sirvió, coméntalo y sigue el canal para más videos como este.",
            source_recommendation=resumen.get("final_recommendation"),
            duration_target=duration_target,
            style=style,
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
