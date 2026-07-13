"""Dependencia de FastAPI reutilizable sobre mh_core.core.rate_limiter
— un solo lugar, aplicado a cualquier ruta que gaste cuota real de
IA/YouTube o recursos de render."""
from fastapi import HTTPException

from mh_core.core.rate_limiter import RateLimiter

# 10 llamadas por 5 minutos — generoso para uso real/pruebas manuales,
# suficiente para frenar un bucle accidental o un abuso del panel.
limitador_generacion_ia = RateLimiter(max_llamadas=10, ventana_segundos=300)


def limitar_generacion_ia() -> None:
    if not limitador_generacion_ia.permitido("global"):
        espera = limitador_generacion_ia.segundos_para_reintentar("global")
        raise HTTPException(
            status_code=429,
            detail=(
                "Límite de solicitudes alcanzado para proteger tu cuota gratis de Gemini/Groq/YouTube. "
                f"Intenta de nuevo en ~{espera:.0f} segundos."
            ),
        )
