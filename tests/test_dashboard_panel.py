from fastapi.testclient import TestClient

from mh_core.app import app

client = TestClient(app)


def test_panel_responde_html_real():
    response = client.get("/dashboard/panel")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "MindHigh" in response.text
    assert "fetch(" in response.text  # confirma que consume la API real, no datos incrustados


def test_providers_status_no_expone_las_keys_reales(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "una-clave-secreta-real")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)

    response = client.get("/mindhigh/providers/status")
    data = response.json()

    assert data["gemini"] == "configured"
    assert data["groq"] == "not_configured"
    assert data["template_fallback"] == "always_available"
    assert "una-clave-secreta-real" not in response.text  # nunca se expone el valor, solo si existe
