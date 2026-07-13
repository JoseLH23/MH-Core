"""
SubtitleBuilder — genera un .srt real, sincronizado con la duración
REAL del audio de narración (no un tiempo inventado). Reparte el
tiempo entre líneas proporcionalmente al número de palabras de cada
una — una línea con el doble de palabras que otra recibe el doble de
tiempo en pantalla, en vez de dividir el tiempo en partes iguales.
"""
import re


def _formatear_tiempo_srt(segundos: float) -> str:
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segs = int(segundos % 60)
    milisegundos = int(round((segundos - int(segundos)) * 1000))
    return f"{horas:02d}:{minutos:02d}:{segs:02d},{milisegundos:03d}"


def _dividir_en_lineas(texto: str, max_palabras_por_linea: int = 8) -> list[str]:
    palabras = [p for p in re.split(r"\s+", texto.strip()) if p]
    if not palabras:
        return []
    return [
        " ".join(palabras[i : i + max_palabras_por_linea])
        for i in range(0, len(palabras), max_palabras_por_linea)
    ]


def construir_srt(texto: str, duracion_total_segundos: float) -> str:
    """Devuelve el contenido de un archivo .srt real, con timestamps
    calculados a partir de la duración real del audio (no un valor fijo)."""
    lineas = _dividir_en_lineas(texto)
    if not lineas or duracion_total_segundos <= 0:
        return ""

    total_palabras = sum(len(l.split()) for l in lineas)
    bloques = []
    tiempo_actual = 0.0

    for i, linea in enumerate(lineas, start=1):
        palabras_linea = len(linea.split())
        proporcion = palabras_linea / total_palabras if total_palabras else 1 / len(lineas)
        duracion_linea = duracion_total_segundos * proporcion
        inicio = tiempo_actual
        fin = min(tiempo_actual + duracion_linea, duracion_total_segundos)

        bloques.append(f"{i}\n{_formatear_tiempo_srt(inicio)} --> {_formatear_tiempo_srt(fin)}\n{linea}\n")
        tiempo_actual = fin

    return "\n".join(bloques)
