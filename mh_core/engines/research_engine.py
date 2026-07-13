import random
from pathlib import Path

from mh_core.engines.youtube_research_engine import YouTubeResearchEngine
from mh_core.utils.logger import logger


class ResearchEngine:
    """
    Fuente de temas para investigar.

    HALLAZGOS REALES DE LA AUDITORÍA (antes de esta fase):
    - Esta clase no tenía NINGÚN caller en todo el proyecto — estaba
      desconectada. El pipeline real (ResearchService -> PluginManager
      -> YouTubePlugin -> mh_core/research.py) ya usa YouTube por su
      propio camino, sin pasar por aquí.
    - Intentaba `from trends import obtener_tema_viral`, un módulo que
      nunca existió, envuelto en un `except Exception: pass` que se
      tragaba el error en silencio. Ya se quitó (fase anterior).

    ESTA FASE: se conecta de verdad con YouTubeResearchEngine (el
    motor real, ya con datos genuinos de la API de YouTube) — se
    reutiliza tal cual, no se duplica su lógica. El fallback fijo
    SOLO se usa si no hay YOUTUBE_API_KEY configurada o si la llamada
    falla — nunca por defecto. Todo queda registrado en el logger
    real del proyecto (mh_core.utils.logger), no en un logger nuevo,
    y no hay ningún `except: pass` silencioso.
    """

    def __init__(self, youtube_engine: YouTubeResearchEngine | None = None, project_dir: str | Path = "temp"):
        # `youtube_engine` es inyectable a propósito — así los tests
        # pueden pasar un doble sin depender de la red ni de una
        # YOUTUBE_API_KEY real.
        self.youtube_engine = youtube_engine or YouTubeResearchEngine()
        self.project_dir = Path(project_dir)
        self.topics = [
            "cómo funciona realmente la memoria humana",
            "por qué tu cerebro inventa recuerdos falsos",
            "el planeta más extraño descubierto",
            "la inteligencia artificial que está cambiando la ciencia",
            "el misterio de los sueños lúcidos",
            "por qué el tiempo parece acelerarse con la edad",
            "el océano oculto bajo la Tierra",
            "la señal espacial que todavía desconcierta a los científicos",
            "el experimento mental que cambió la física moderna",
            "el error del cerebro que usan los magos",
            "la paradoja que podría explicar el universo",
            "por qué algunas personas sienten que ya vivieron algo",
        ]

    def _fallback(self, motivo: str) -> str:
        logger.info(f"ResearchEngine: usando fallback fijo ({motivo}).")
        return random.choice(self.topics)

    def get_topic(self) -> str:
        try:
            self.project_dir.mkdir(exist_ok=True)
            resultado = self.youtube_engine.research(self.project_dir)
        except Exception as e:
            # Nunca silencioso: se registra la excepción real antes
            # de caer al fallback.
            logger.warning(f"ResearchEngine: YouTubeResearchEngine falló ({e}).")
            return self._fallback("error en YouTubeResearchEngine")

        if resultado and resultado.get("topic"):
            logger.info("ResearchEngine: tema obtenido de YouTube (datos reales).")
            return resultado["topic"]

        # research() devuelve None cuando no hay YOUTUBE_API_KEY o
        # cuando la API no regresó resultados útiles — ambos casos
        # honestos, no un error.
        return self._fallback("sin YOUTUBE_API_KEY o sin resultados de YouTube")
