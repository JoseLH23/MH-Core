"""
Lógica compartida entre generadores de contenido basados en LLM
(Gemini, Groq) — el prompt y el parseo de la respuesta son
IDÉNTICOS entre proveedores, así que viven en un solo lugar.

Fase "calidad del contenido": el prompt ahora pide salida ESTRUCTURADA
completa en JSON (título, gancho, guion, descripción, hashtags, CTA) en
vez de solo título+guion en texto libre — y acepta duración objetivo y
estilo como parámetros reales, no fijos.
"""
import json
import re

from mh_core.utils.logger import logger

DURACION_INSTRUCCIONES = {
    "short": "un Short/Reel de menos de 60 segundos — guion muy breve, un solo punto clave, ritmo rápido",
    "medio": "un video de 3 a 5 minutos — 2 a 3 puntos clave desarrollados con ejemplos",
    "largo": "un video largo de más de 5 minutos — desarrollo completo con varias secciones",
}


def construir_prompt(brain_report: dict, duration_target: str = "short", style: str = "informativo") -> str:
    resumen = brain_report.get("executive_summary", {}) or {}
    razones = brain_report.get("reasoning", []) or []
    acciones = brain_report.get("recommended_actions", []) or []
    instruccion_duracion = DURACION_INSTRUCCIONES.get(duration_target, DURACION_INSTRUCCIONES["short"])

    return (
        "Eres un guionista experto en contenido de YouTube en español.\n"
        f"Tema recomendado: {resumen.get('topic', 'sin especificar')}\n"
        f"Razones de la recomendación: {'; '.join(razones) if razones else 'ninguna'}\n"
        f"Acciones sugeridas: {'; '.join(acciones) if acciones else 'ninguna'}\n"
        f"Formato objetivo: {instruccion_duracion}\n"
        f"Estilo/tono: {style}\n\n"
        "IMPORTANTE: el contenido debe ser ORIGINAL — no copies ni parafrasees "
        "de cerca el título o guion de ningún video existente; usa el tema como "
        "inspiración, no como fuente a repetir.\n\n"
        "Responde ÚNICAMENTE con un objeto JSON válido, sin texto antes ni "
        "después, con exactamente estas claves:\n"
        "{\n"
        '  "titulo": "...",\n'
        '  "gancho": "primeros 3 segundos, lo que se dice para enganchar",\n'
        '  "guion": "guion completo, con saltos de línea \\n donde correspondan",\n'
        '  "descripcion": "descripción para la plataforma, 2-3 líneas",\n'
        '  "hashtags": ["#tag1", "#tag2", "#tag3"],\n'
        '  "cta": "llamado a la acción del cierre"\n'
        "}"
    )


def _extraer_bloque_json(texto: str) -> str:
    """Los LLM a veces envuelven el JSON en ```json ... ``` pese a que
    se les pidió que no lo hicieran — se tolera ese caso también."""
    coincidencia = re.search(r"\{.*\}", texto, re.DOTALL)
    return coincidencia.group(0) if coincidencia else texto


def parsear_respuesta_estructurada(texto: str, topic: str, proveedor: str) -> dict:
    """
    Parseo tolerante: intenta JSON primero (lo pedido); si el LLM no
    lo siguió bien, cae a un parseo de texto libre básico (título =
    primera línea, resto = guion) — nunca se rompe, nunca se pierde
    el contenido generado solo porque el formato no fue perfecto.

    Devuelve siempre las mismas claves, con "" o [] si algo faltó.
    """
    bloque = _extraer_bloque_json(texto.strip())

    try:
        datos = json.loads(bloque)
        return {
            "title": str(datos.get("titulo") or f"{topic.capitalize()} (generado por IA)").strip(),
            "hook": str(datos.get("gancho") or "").strip(),
            "script": str(datos.get("guion") or "").strip(),
            "description": str(datos.get("descripcion") or "").strip(),
            "hashtags": [str(h).strip() for h in (datos.get("hashtags") or []) if str(h).strip()],
            "cta": str(datos.get("cta") or "").strip(),
        }
    except (json.JSONDecodeError, AttributeError, TypeError) as e:
        logger.info(f"{proveedor}: la respuesta no fue JSON válido ({e}); se usa como texto libre.")
        lineas = [l for l in texto.strip().splitlines() if l.strip()]
        titulo = lineas[0].strip() if lineas else f"{topic.capitalize()} (generado por IA)"
        guion = "\n".join(lineas[1:]).strip() or texto.strip()
        return {
            "title": titulo,
            "hook": "",
            "script": guion,
            "description": "",
            "hashtags": [],
            "cta": "",
        }
