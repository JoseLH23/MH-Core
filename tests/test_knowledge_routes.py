from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from mh_core.app import app
from mh_core.knowledge.governed_bundle import git_blob_sha1
from mh_core.routes.knowledge_routes import service


client = TestClient(app)


def _headers(service_id: str, key: str) -> dict[str, str]:
    return {"X-Service-ID": service_id, "X-API-Key": key}


def _write_bundle(path) -> None:
    content = "Camping disponible según fechas, capacidad y reglas aprobadas."
    payload = {
        "schema_version": 1,
        "knowledge_version": "2026.07.3",
        "product": "EjiXhole",
        "governance": {
            "citation_required": True,
            "unknown_fact_behavior": "POR CONFIRMAR",
            "unapproved_behavior": "block",
            "expired_behavior": "block",
        },
        "documents": [
            {
                "id": "faq",
                "path": "04-sales-and-service/FAQ_Y_ATENCION_INICIAL.md",
                "category": "sales",
                "document_version": "1.0.0",
                "citation_id": "mhk://ejixhole/faq/2026.07.3",
                "sensitivity": "internal",
                "source_type": "owner_approved",
                "source_reference": "FAQ aprobada de prueba",
                "checksum": git_blob_sha1(content),
                "review_due_at": "2099-01-19",
                "content": content,
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture(autouse=True)
def reset_knowledge_service(monkeypatch):
    service.reset()
    monkeypatch.delenv("MH_KNOWLEDGE_BUNDLE_PATH", raising=False)
    monkeypatch.delenv("MH_CORE_MINDHIGH_KEY", raising=False)
    monkeypatch.delenv("MH_CORE_EJIXHOLE_KEY", raising=False)
    monkeypatch.delenv("MH_CORE_OPERATIONS_KEY", raising=False)
    monkeypatch.delenv("MH_CORE_API_KEY", raising=False)
    yield
    service.reset()


def test_status_informa_configuracion_faltante(monkeypatch):
    monkeypatch.setenv("MH_CORE_MINDHIGH_KEY", "mindhigh-test-key")

    response = client.get(
        "/knowledge/status",
        headers=_headers("mindhigh-worker", "mindhigh-test-key"),
    )

    assert response.status_code == 200
    assert response.json() == {
        "configured": False,
        "available": False,
        "knowledge_version": None,
        "product": None,
        "documents": 0,
        "error": "MH_KNOWLEDGE_BUNDLE_PATH no está configurada.",
    }


def test_search_falla_cerrado_sin_bundle(monkeypatch):
    monkeypatch.setenv("MH_CORE_MINDHIGH_KEY", "mindhigh-test-key")

    response = client.get(
        "/knowledge/search",
        params={"q": "camping"},
        headers=_headers("mindhigh-worker", "mindhigh-test-key"),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "El conocimiento aprobado no está disponible."


def test_mindhigh_consulta_contexto_citable(tmp_path, monkeypatch):
    bundle_path = tmp_path / "approved-bundle.json"
    _write_bundle(bundle_path)
    monkeypatch.setenv("MH_KNOWLEDGE_BUNDLE_PATH", str(bundle_path))
    monkeypatch.setenv("MH_CORE_MINDHIGH_KEY", "mindhigh-test-key")

    status = client.get(
        "/knowledge/status",
        headers=_headers("mindhigh-worker", "mindhigh-test-key"),
    )
    response = client.get(
        "/knowledge/search",
        params={"q": "camping capacidad", "category": "sales", "limit": 3},
        headers=_headers("mindhigh-worker", "mindhigh-test-key"),
    )

    assert status.status_code == 200
    assert status.json()["available"] is True
    assert status.json()["documents"] == 1
    assert response.status_code == 200
    body = response.json()
    assert body["knowledge_version"] == "2026.07.3"
    assert body["documents"][0]["id"] == "faq"
    assert body["documents"][0]["citation_id"] == "mhk://ejixhole/faq/2026.07.3"


def test_bundle_corrupto_devuelve_indisponibilidad_segura(tmp_path, monkeypatch):
    bundle_path = tmp_path / "approved-bundle.json"
    bundle_path.write_bytes(b"\xff\xfe")
    monkeypatch.setenv("MH_KNOWLEDGE_BUNDLE_PATH", str(bundle_path))
    monkeypatch.setenv("MH_CORE_MINDHIGH_KEY", "mindhigh-test-key")

    status = client.get(
        "/knowledge/status",
        headers=_headers("mindhigh-worker", "mindhigh-test-key"),
    )
    response = client.get(
        "/knowledge/search",
        params={"q": "camping"},
        headers=_headers("mindhigh-worker", "mindhigh-test-key"),
    )

    assert status.status_code == 200
    assert status.json()["configured"] is True
    assert status.json()["available"] is False
    assert response.status_code == 503
    assert response.json()["detail"] == "El conocimiento aprobado no está disponible."


def test_ejixhole_backend_no_recibe_scope_de_conocimiento(tmp_path, monkeypatch):
    bundle_path = tmp_path / "approved-bundle.json"
    _write_bundle(bundle_path)
    monkeypatch.setenv("MH_KNOWLEDGE_BUNDLE_PATH", str(bundle_path))
    monkeypatch.setenv("MH_CORE_EJIXHOLE_KEY", "ejixhole-test-key")

    response = client.get(
        "/knowledge/search",
        params={"q": "camping"},
        headers=_headers("ejixhole-backend", "ejixhole-test-key"),
    )

    assert response.status_code == 403


def test_api_requiere_identidad(monkeypatch):
    monkeypatch.setenv("MH_CORE_MINDHIGH_KEY", "mindhigh-test-key")

    response = client.get("/knowledge/status")

    assert response.status_code == 401
