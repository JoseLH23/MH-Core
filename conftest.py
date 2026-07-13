"""
conftest.py — corre antes de que pytest importe cualquier módulo de
`mh_core`/`apps`, así que es el lugar correcto para fijar variables de
entorno que la app necesita al arrancar.

CR-04 (auditoría de seguridad 13/jul/2026): mh_core/core/auth.py exige
MH_CORE_API_KEY real y falla cerrado si no está configurada — los
tests que usan TestClient (HTTP real) necesitan una key de pruebas.
"""
import os

os.environ.setdefault("MH_CORE_API_KEY", "clave-de-pruebas-nunca-usar-en-produccion")

# Cabecera lista para usar en cualquier test que haga peticiones HTTP reales.
HEADERS_API_KEY = {"X-API-Key": os.environ["MH_CORE_API_KEY"]}
