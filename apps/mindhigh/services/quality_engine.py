"""
QualityEngine — evalúa claridad, gancho, retención, utilidad y
originalidad de una pieza de contenido.

DECISIÓN REAL (no técnica): se implementa como reglas heurísticas, NO
como una llamada extra a Gemini/Groq pidiendo que se autoevalúen. Con
presupuesto real en cero y niveles gratis con cuota limitada, evaluar
con una segunda llamada de IA duplicaría el gasto de cuota por cada
pieza generada — un evaluador determinista, gratis y rápido es la
opción responsable para esta fase. Si más adelante se decide que vale
la pena el costo de una evaluación con IA, este archivo es el único
que habría que reemplazar (MindHighPipeline no sabe cómo se evalúa).
"""
import re

from apps.mindhigh.models.content_piece import ContentPiece
from apps.mindhigh.models.quality_evaluation import QualityEvaluation

RANGOS_LONGITUD_GUION = {
    "short": (50, 500),
    "medio": (400, 2000),
    "largo": (1000, 6000),
}

PALABRAS_DE_CURIOSIDAD = (
    "qué", "que", "cómo", "como", "por qué", "porque", "nunca", "secreto",
    "verdad", "realmente", "en serio", "sabías", "sorprendente",
)


class QualityEngine:
    def evaluar(self, contenido: ContentPiece, video_original_titulo: str | None = None) -> QualityEvaluation:
        razones: list[str] = []

        claridad = self._evaluar_claridad(contenido, razones)
        gancho = self._evaluar_gancho(contenido, razones)
        retencion = self._evaluar_retencion(contenido, razones)
        utilidad = self._evaluar_utilidad(contenido, razones)
        originalidad = self._evaluar_originalidad(contenido, video_original_titulo, razones)

        return QualityEvaluation(
            content_id=contenido.id,
            claridad=claridad,
            gancho=gancho,
            retencion=retencion,
            utilidad=utilidad,
            originalidad=originalidad,
            razones=razones,
        )

    def _evaluar_claridad(self, contenido: ContentPiece, razones: list[str]) -> float:
        puntos = 100.0
        minimo, maximo = RANGOS_LONGITUD_GUION.get(contenido.duration_target, RANGOS_LONGITUD_GUION["short"])
        largo = len(contenido.script)

        if largo < minimo:
            puntos -= 30
            razones.append(f"claridad: guion corto para '{contenido.duration_target}' ({largo} caracteres)")
        elif largo > maximo:
            puntos -= 15
            razones.append(f"claridad: guion largo para '{contenido.duration_target}' ({largo} caracteres)")

        if not contenido.title or len(contenido.title) < 5:
            puntos -= 20
            razones.append("claridad: título ausente o demasiado corto")

        return max(0.0, puntos)

    def _evaluar_gancho(self, contenido: ContentPiece, razones: list[str]) -> float:
        if not contenido.hook:
            razones.append("gancho: no se generó ningún gancho inicial")
            return 20.0  # no es cero — el guion podría empezar bien igual, pero sin gancho explícito es un riesgo real

        puntos = 60.0
        texto = contenido.hook.lower()

        if 10 <= len(contenido.hook) <= 220:
            puntos += 15
        else:
            razones.append("gancho: longitud fuera del rango recomendado (muy corto o muy largo)")

        if "?" in contenido.hook:
            puntos += 10
        if any(palabra in texto for palabra in PALABRAS_DE_CURIOSIDAD):
            puntos += 15

        return min(100.0, puntos)

    def _evaluar_retencion(self, contenido: ContentPiece, razones: list[str]) -> float:
        lineas_con_contenido = [l for l in contenido.script.splitlines() if l.strip()]
        puntos = 40.0 + min(len(lineas_con_contenido), 6) * 10  # hasta 6 bloques cuentan

        if len(lineas_con_contenido) < 3:
            razones.append("retención: el guion tiene muy poca estructura (menos de 3 bloques)")

        if not contenido.cta:
            puntos -= 15
            razones.append("retención: sin CTA de cierre, se pierde la última oportunidad de retener")

        return max(0.0, min(100.0, puntos))

    def _evaluar_utilidad(self, contenido: ContentPiece, razones: list[str]) -> float:
        puntos = 100.0

        if not contenido.description:
            puntos -= 25
            razones.append("utilidad: sin descripción")
        if not contenido.cta:
            puntos -= 20
            razones.append("utilidad: sin llamado a la acción")
        if len(contenido.hashtags) < 2:
            puntos -= 15
            razones.append(f"utilidad: pocos hashtags ({len(contenido.hashtags)})")

        return max(0.0, puntos)

    def _evaluar_originalidad(self, contenido: ContentPiece, video_original_titulo: str | None, razones: list[str]) -> float:
        if not video_original_titulo:
            # Sin un video de referencia real, no se puede medir
            # originalidad — no se penaliza por algo que no se puede
            # verificar (eso sería inventar un dato, no medirlo).
            return 100.0

        palabras_original = set(re.findall(r"\w+", video_original_titulo.lower()))
        palabras_generado = set(re.findall(r"\w+", contenido.title.lower()))

        if not palabras_original or not palabras_generado:
            return 100.0

        interseccion = palabras_original & palabras_generado
        proporcion_copiada = len(interseccion) / len(palabras_generado)
        originalidad = round((1 - proporcion_copiada) * 100, 1)

        if proporcion_copiada > 0.5:
            razones.append(
                f"originalidad: el título comparte {proporcion_copiada:.0%} de palabras con el video investigado"
            )

        return max(0.0, originalidad)
