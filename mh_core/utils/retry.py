"""
Reintentos con backoff exponencial — solo librería estándar (`time`),
sin agregar `tenacity`/`backoff` como dependencia nueva.

Motivo real: los 3 puntos que llaman a APIs externas del ecosistema
(YouTube Data API, Gemini, Groq) corren sobre niveles gratis con
límites de cuota (429 / Too Many Requests). Antes de esta fase, un 429
momentáneo hacía caer directo al siguiente proveedor de la cadena (o a
plantillas) sin darle una segunda oportunidad — desperdiciando el
respaldo por algo que normalmente se resuelve solo en un par de
segundos.
"""
import time
from typing import Callable, TypeVar

from mh_core.utils.logger import logger

T = TypeVar("T")


def reintentar_con_backoff(
    func: Callable[[], T],
    intentos: int = 3,
    espera_inicial: float = 1.0,
    factor: float = 2.0,
    nombre: str = "llamada",
) -> T:
    """
    Ejecuta `func()` hasta `intentos` veces, con espera creciente entre
    cada una (1s, 2s, 4s... con los valores por defecto). Si el último
    intento también falla, se relanza la excepción real — nunca se
    traga el error, quien llama decide qué hacer (ej. pasar al
    siguiente proveedor de la cadena).
    """
    espera = espera_inicial
    ultimo_error: Exception | None = None

    for intento in range(1, intentos + 1):
        try:
            return func()
        except Exception as e:
            ultimo_error = e
            if intento == intentos:
                logger.warning(
                    f"{nombre}: falló tras {intentos} intentos ({e}). No se reintenta más."
                )
                raise
            logger.info(
                f"{nombre}: intento {intento}/{intentos} falló ({e}). "
                f"Reintentando en {espera:.0f}s..."
            )
            time.sleep(espera)
            espera *= factor

    # Inalcanzable en la práctica (el for siempre retorna o relanza),
    # pero deja contento al type checker y evita un "implicit return None".
    raise ultimo_error  # type: ignore[misc]
