"""
Autenticación mínima real para MH-Core — CR-04 (auditoría de
seguridad 13/jul/2026): antes, ningún router tenía ninguna
dependencia de auth; cualquiera con acceso de red podía disparar
Automation Engine, agentes, el orquestador de MindHigh o leer
notificaciones internas, gastando cuota real de Gemini/Groq/YouTube.

Diseño: API key compartida por header (`X-API-Key`), deny-by-default.
No es OAuth/JWT completo (esto no tiene usuarios individuales, es un
solo proceso interno) — es la protección real mínima que pide la
auditoría: "no exponer MH-Core públicamente; autenticación
deny-by-default". Si más adelante hace falta identidad por usuario
real, esto es lo único que habría que reemplazar.

FALLA CERRADO: si MH_CORE_API_KEY no está configurada, TODAS las
rutas protegidas rechazan — nunca "si no hay key configurada, dejar
pasar todo".
"""
import hmac
import os

from fastapi import Header, HTTPException


def verificar_api_key(x_api_key: str | None = Header(default=None)) -> None:
    clave_real = os.environ.get("MH_CORE_API_KEY", "")

    if not clave_real:
        raise HTTPException(
            status_code=503,
            detail="MH_CORE_API_KEY no está configurada en el servidor — el acceso está cerrado por defecto.",
        )

    if not x_api_key or not hmac.compare_digest(x_api_key, clave_real):
        raise HTTPException(status_code=401, detail="X-API-Key inválida o faltante.")
