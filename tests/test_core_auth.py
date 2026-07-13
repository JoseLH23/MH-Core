import pytest
from fastapi import HTTPException

from mh_core.core.auth import verificar_api_key


def test_falla_cerrado_si_no_hay_key_configurada(monkeypatch):
    monkeypatch.delenv("MH_CORE_API_KEY", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        verificar_api_key(x_api_key="cualquier-cosa")

    assert exc_info.value.status_code == 503


def test_rechaza_sin_key_en_el_header(monkeypatch):
    monkeypatch.setenv("MH_CORE_API_KEY", "la-clave-real")

    with pytest.raises(HTTPException) as exc_info:
        verificar_api_key(x_api_key=None)

    assert exc_info.value.status_code == 401


def test_rechaza_key_incorrecta(monkeypatch):
    monkeypatch.setenv("MH_CORE_API_KEY", "la-clave-real")

    with pytest.raises(HTTPException) as exc_info:
        verificar_api_key(x_api_key="clave-equivocada")

    assert exc_info.value.status_code == 401


def test_acepta_la_key_correcta(monkeypatch):
    monkeypatch.setenv("MH_CORE_API_KEY", "la-clave-real")

    verificar_api_key(x_api_key="la-clave-real")  # no debe lanzar nada


def test_endpoint_real_sin_key_devuelve_401():
    """Confirma deny-by-default en la app real, no solo en la función aislada."""
    from fastapi.testclient import TestClient

    from mh_core.app import app

    client = TestClient(app)
    respuesta = client.get("/agents")

    assert respuesta.status_code == 401


def test_raiz_sigue_siendo_publica():
    """'/' es el liveness check para monitoreo/infra — a propósito
    sin auth, no revela nada sensible."""
    from fastapi.testclient import TestClient

    from mh_core.app import app

    client = TestClient(app)
    respuesta = client.get("/")

    assert respuesta.status_code == 200
