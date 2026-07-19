import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from mh_core.app import app
from mh_core.core.auth import ServiceIdentity, requerir_scopes, verificar_api_key


_ENV_KEYS = (
    "MH_CORE_API_KEY",
    "MH_CORE_ALLOW_LEGACY_API_KEY",
    "MH_CORE_EJIXHOLE_KEY",
    "MH_CORE_MINDHIGH_KEY",
    "MH_CORE_OPERATIONS_KEY",
    "MH_CORE_REVOKED_SERVICES",
)


@pytest.fixture(autouse=True)
def clean_identity_env(monkeypatch):
    for name in _ENV_KEYS:
        monkeypatch.delenv(name, raising=False)


def test_legacy_key_remains_available_without_service_registry(monkeypatch):
    monkeypatch.setenv("MH_CORE_API_KEY", "legacy-value-for-transition")

    identity = verificar_api_key(request=None, x_api_key="legacy-value-for-transition", x_service_id=None)

    assert identity.name == "legacy"
    assert identity.legacy is True
    assert identity.scopes == frozenset({"*"})


def test_registry_authenticates_named_service(monkeypatch):
    value = "e" * 48
    monkeypatch.setenv("MH_CORE_EJIXHOLE_KEY", value)

    identity = verificar_api_key(request=None, x_api_key=value, x_service_id="ejixhole-backend")

    assert identity.name == "ejixhole-backend"
    assert "ejixhole.read" in identity.scopes
    assert identity.legacy is False


def test_configured_registry_disables_legacy_by_default(monkeypatch):
    monkeypatch.setenv("MH_CORE_EJIXHOLE_KEY", "e" * 48)
    monkeypatch.setenv("MH_CORE_API_KEY", "legacy-value-for-transition")

    with pytest.raises(HTTPException) as error:
        verificar_api_key(request=None, x_api_key="legacy-value-for-transition", x_service_id=None)

    assert error.value.status_code == 401


def test_revoked_service_is_rejected(monkeypatch):
    value = "e" * 48
    monkeypatch.setenv("MH_CORE_EJIXHOLE_KEY", value)
    monkeypatch.setenv("MH_CORE_REVOKED_SERVICES", "ejixhole-backend")

    with pytest.raises(HTTPException) as error:
        verificar_api_key(request=None, x_api_key=value, x_service_id="ejixhole-backend")

    assert error.value.status_code == 401


def test_scope_dependency_rejects_missing_permission():
    dependency = requerir_scopes("core.admin")
    identity = ServiceIdentity(name="ejixhole-backend", scopes=frozenset({"core.read"}))

    with pytest.raises(HTTPException) as error:
        dependency(identity)

    assert error.value.status_code == 403


def test_status_accepts_named_service(monkeypatch):
    value = "m" * 48
    monkeypatch.setenv("MH_CORE_MINDHIGH_KEY", value)

    response = TestClient(app).get(
        "/status",
        headers={"X-Service-ID": "mindhigh-worker", "X-API-Key": value},
    )

    assert response.status_code == 200


def test_mindhigh_service_cannot_read_ejixhole_analytics(monkeypatch):
    value = "m" * 48
    monkeypatch.setenv("MH_CORE_MINDHIGH_KEY", value)

    response = TestClient(app).get(
        "/integrations/ejixhole/operations/summary",
        headers={"X-Service-ID": "mindhigh-worker", "X-API-Key": value},
    )

    assert response.status_code == 403
