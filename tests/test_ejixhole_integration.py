import requests
from fastapi.testclient import TestClient
import pytest

from mh_core.app import app
from mh_core.integrations.ejixhole_client import EjixholeClient, EjixholeConfigurationError, EjixholeOperationalSummary, EjixholeUpstreamError

MH_KEY = "m" * 48
SERVICE_KEY = "s" * 48


def payload_valido():
    return {
        "generated_at": "2026-07-16T12:00:00Z",
        "business_date": "2026-07-16",
        "source": "ejixhole",
        "api_version": "v1",
        "access": "read_only",
        "scope": "ejixhole:read:operations",
        "metrics": {
            "ingresos_hoy": 1500.0,
            "ingresos_mes": 12000.0,
            "reservaciones_activas": 4,
            "proximas_7_dias": 3,
            "saldo_pendiente_total": 500.0,
            "tasa_cancelacion_mes": 2.5,
            "ocupacion_promedio_mes": 64.0,
            "diferencia_caja_hoy": 0.0,
        },
    }


class FakeResponse:
    def __init__(self, status_code=200, payload=None, api_version="v1"):
        self.status_code = status_code
        self._payload = payload if payload is not None else payload_valido()
        self.headers = {"X-API-Version": api_version}

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response = response or FakeResponse()
        self.error = error
        self.calls = []

    def get(self, url, *, headers, timeout):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        if self.error:
            raise self.error
        return self.response


def test_cliente_requiere_configuracion(monkeypatch):
    monkeypatch.delenv("EJIXHOLE_API_BASE_URL", raising=False)
    monkeypatch.delenv("EJIXHOLE_SERVICE_KEY", raising=False)
    with pytest.raises(EjixholeConfigurationError):
        EjixholeClient()


def test_cliente_usa_api_v1_y_credencial_exclusiva():
    session = FakeSession()
    client = EjixholeClient(
        base_url="https://backend.ejixhole.test/",
        service_key=SERVICE_KEY,
        timeout_seconds=8,
        session=session,
    )

    summary = client.operational_summary()

    assert summary.access == "read_only"
    assert summary.metrics.reservaciones_activas == 4
    call = session.calls[0]
    assert call["url"].endswith("/api/v1/integrations/mh-core/operational-summary")
    assert call["headers"]["X-MH-Service-Key"] == SERVICE_KEY
    assert call["timeout"] == 8


def test_cliente_falla_si_no_se_confirma_api_v1():
    client = EjixholeClient(
        base_url="https://backend.ejixhole.test",
        service_key=SERVICE_KEY,
        session=FakeSession(FakeResponse(api_version="legacy")),
    )
    with pytest.raises(EjixholeUpstreamError, match="API v1"):
        client.operational_summary()


def test_cliente_traduce_error_de_red_sin_filtrar_clave():
    client = EjixholeClient(
        base_url="https://backend.ejixhole.test",
        service_key=SERVICE_KEY,
        session=FakeSession(error=requests.Timeout("detalle interno")),
    )
    with pytest.raises(EjixholeUpstreamError) as exc:
        client.operational_summary()
    assert SERVICE_KEY not in str(exc.value)
    assert "detalle interno" not in str(exc.value)


def test_ruta_mh_core_sigue_protegida_por_su_api_key(monkeypatch):
    monkeypatch.setenv("MH_CORE_API_KEY", MH_KEY)
    client = TestClient(app)
    response = client.get("/integrations/ejixhole/summary")
    assert response.status_code == 401


def test_ruta_devuelve_resumen_sin_exponer_escrituras(monkeypatch):
    monkeypatch.setenv("MH_CORE_API_KEY", MH_KEY)
    monkeypatch.setenv("EJIXHOLE_API_BASE_URL", "https://backend.ejixhole.test")
    monkeypatch.setenv("EJIXHOLE_SERVICE_KEY", SERVICE_KEY)
    monkeypatch.setattr(
        EjixholeClient,
        "operational_summary",
        lambda _self: EjixholeOperationalSummary.model_validate(payload_valido()),
    )
    client = TestClient(app)

    response = client.get(
        "/integrations/ejixhole/summary",
        headers={"X-API-Key": MH_KEY},
    )

    assert response.status_code == 200
    assert response.json()["access"] == "read_only"
    assert response.json()["scope"] == "ejixhole:read:operations"
    assert client.post(
        "/integrations/ejixhole/summary",
        headers={"X-API-Key": MH_KEY},
        json={},
    ).status_code == 405
