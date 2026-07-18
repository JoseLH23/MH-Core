from fastapi.testclient import TestClient

from mh_core.app import app
from mh_core.services.observability_service import OperationalHealthService


client = TestClient(app)


def test_resumen_saludable_cumple_slo(monkeypatch):
    service = OperationalHealthService(sample_limit=10)
    monkeypatch.setattr(service, "_persistence", lambda: {"backend": "sqlite"})
    monkeypatch.setattr(service, "_ejixhole_state", lambda: {"backend": "sqlite"})
    monkeypatch.setattr(service, "_durable_jobs", lambda: {"pending": 0, "running": 0, "dead_letter": 0})

    summary = service.summary()

    assert summary["status"] == "healthy"
    assert summary["slo"]["availability_percent"] == 100.0
    assert summary["slo"]["checks"]["dead_letter"] is True


def test_dead_letter_degrada_sin_marcar_dependencia_caida(monkeypatch):
    service = OperationalHealthService(sample_limit=10)
    monkeypatch.setattr(service, "_persistence", lambda: {"backend": "postgresql"})
    monkeypatch.setattr(service, "_ejixhole_state", lambda: {"backend": "postgresql"})
    monkeypatch.setattr(service, "_durable_jobs", lambda: {"pending": 0, "running": 0, "dead_letter": 2})

    summary = service.summary()

    assert summary["current"]["healthy"] is True
    assert summary["status"] == "degraded"
    assert summary["slo"]["checks"]["dead_letter"] is False


def test_diagnostico_operativo_esta_protegido(monkeypatch):
    monkeypatch.setenv("MH_CORE_API_KEY", "observability-test-key")

    unauthorized = client.get("/observability/summary")
    authorized = client.get(
        "/observability/summary",
        headers={"X-API-Key": "observability-test-key"},
    )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200
    assert "slo" in authorized.json()


def test_readiness_usa_el_mismo_contrato_privado(monkeypatch):
    monkeypatch.setenv("MH_CORE_API_KEY", "ready-test-key")
    response = client.get("/health/ready", headers={"X-API-Key": "ready-test-key"})
    assert response.status_code in {200, 503}
    assert response.json()["status"] in {"ready", "unavailable"}
    assert set(response.json()["checks"]) == {"persistence", "ejixhole_state", "durable_jobs"}
