from fastapi.testclient import TestClient

from mh_core.app import app
from mh_core.services.observability_service import OperationalHealthService


client = TestClient(app)


def healthy_service(monkeypatch, clock):
    service = OperationalHealthService(
        sample_limit=10,
        monotonic=lambda: clock[0],
        expected_interval_seconds=60,
        max_gap_seconds=120,
    )
    monkeypatch.setattr(service, "_persistence", lambda: {"backend": "sqlite"})
    monkeypatch.setattr(service, "_ejixhole_state", lambda: {"backend": "sqlite"})
    monkeypatch.setattr(
        service,
        "_durable_jobs",
        lambda: {"pending": 0, "running": 0, "dead_letter": 0},
    )
    return service


def test_resumen_saludable_cumple_slo_despues_de_intervalo(monkeypatch):
    clock = [0.0]
    service = healthy_service(monkeypatch, clock)

    first = service.summary()
    clock[0] = 60.0
    second = service.summary()

    assert first["status"] == "healthy"
    assert first["slo"]["status"] == "unknown"
    assert second["slo"]["availability_percent"] == 100.0
    assert second["slo"]["status"] == "healthy"
    assert second["slo"]["checks"]["dead_letter"] is True


def test_refrescar_no_diluye_un_intervalo_caido(monkeypatch):
    clock = [0.0]
    service = healthy_service(monkeypatch, clock)
    state = {"up": False}

    def persistence():
        if not state["up"]:
            raise RuntimeError("down")
        return {"backend": "sqlite"}

    monkeypatch.setattr(service, "_persistence", persistence)
    service.summary()
    state["up"] = True
    clock[0] = 60.0
    after_outage = service.summary()

    for _ in range(20):
        refreshed = service.summary()

    assert after_outage["slo"]["availability_percent"] == 0.0
    assert refreshed["slo"]["availability_percent"] == 0.0
    assert refreshed["slo"]["segments"] == 1

    clock[0] = 120.0
    recovered = service.summary()
    assert recovered["slo"]["availability_percent"] == 50.0


def test_dead_letter_degrada_sin_marcar_dependencia_caida(monkeypatch):
    clock = [0.0]
    service = healthy_service(monkeypatch, clock)
    monkeypatch.setattr(
        service,
        "_durable_jobs",
        lambda: {"pending": 0, "running": 0, "dead_letter": 2},
    )

    summary = service.summary()

    assert summary["current"]["healthy"] is True
    assert summary["status"] == "degraded"
    assert summary["slo"]["checks"]["dead_letter"] is False


def test_dead_letter_es_desconocido_si_falla_la_consulta(monkeypatch):
    clock = [0.0]
    service = healthy_service(monkeypatch, clock)

    def unavailable():
        raise RuntimeError("queue unavailable")

    monkeypatch.setattr(service, "_durable_jobs", unavailable)
    summary = service.summary()

    assert summary["current"]["checks"]["durable_jobs"]["status"] == "down"
    assert summary["slo"]["checks"]["dead_letter"] is None
    assert summary["status"] == "degraded"


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
