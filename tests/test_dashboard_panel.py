from fastapi.testclient import TestClient

from conftest import HEADERS_API_KEY
from mh_core.app import app

client = TestClient(app)


def test_panel_responde_html_real():
    # El HTML del panel es público a propósito (CR-04) — sin header.
    response = client.get("/dashboard/panel")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "MindHigh" in response.text
    assert "fetch(" in response.text  # confirma que consume la API real, no datos incrustados


def test_panel_sin_prefijo_dashboard_sigue_protegido():
    """Los DATOS del dashboard (a diferencia del HTML del panel) sí
    deben exigir X-API-Key."""
    response = client.get("/dashboard")
    assert response.status_code == 401


def test_providers_status_no_expone_las_keys_reales(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "una-clave-secreta-real")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)

    response = client.get("/mindhigh/providers/status", headers=HEADERS_API_KEY)
    data = response.json()

    assert data["gemini"] == "configured"
    assert data["groq"] == "not_configured"
    assert data["template_fallback"] == "always_available"
    assert "una-clave-secreta-real" not in response.text  # nunca se expone el valor, solo si existe
