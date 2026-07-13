"""
Lógica compartida entre generadores de contenido basados en LLM
(Gemini, Groq) — el prompt y el parseo de la respuesta son
IDÉNTICOS entre proveedores (ambos hablan "texto plano" con el mismo
formato pedido), así que viven en un solo lugar en vez de duplicarse
en cada generador.
"""
from mh_core.utils.logger import logger


def construir_prompt(brain_report: dict) -> str:
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


def separar_titulo_y_guion(texto: str, topic: str, proveedor: str) -> tuple[str, str]:
    """Parseo tolerante: si el LLM no siguió el formato exacto pedido,
    no se rompe — se usa todo el texto como guion y un título genérico
    basado en el tema real."""
    if "TITULO:" in texto and "GUION:" in texto:
        despues_de_titulo = texto.split("TITULO:", 1)[1]
        partes = despues_de_titulo.split("GUION:", 1)
        if len(partes) == 2:
            parte_titulo, parte_guion = partes[0].strip(), partes[1].strip()
            if parte_titulo and parte_guion:
                return parte_titulo, parte_guion

    logger.info(f"{proveedor}: la respuesta no siguió el formato TITULO/GUION esperado; se usa tal cual.")
    return f"{topic.capitalize()} (generado por IA)", texto
