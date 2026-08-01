from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from apps.mindhigh.routes.marketing_routes import knowledge_service
from mh_core.app import app
from mh_core.knowledge.governed_bundle import git_blob_sha1


client = TestClient(app)


def _headers() -> dict[str, str]:
    return {
        "X-Service-ID": "mindhigh-worker",
        "X-API-Key": "mindhigh-marketing-test-key",
    }


def _brief(**changes) -> dict:
    payload = {
        "name": "Escapada familiar",
        "objective": "impulsar_reservas",
        "audience": "familias que buscan convivir en la naturaleza",
        "main_emotion": "tranquilidad y conexión",
        "offer_focus": "experiencia_general",
        "season": "verano",
        "channels": ["facebook", "instagram_story"],
        "call_to_action": "Consulta la información vigente y solicita tu reservación en el portal oficial.",
    }
    payload.update(changes)
    return payload


def _write_bundle(path, *, include_offer: bool = True) -> None:
    ids = ["brand", "marketing_strategy", "agent_rules"]
    if include_offer:
        ids.append("offer")
    documents = []
    for document_id in ids:
        content = f"Contenido aprobado para campañas: {document_id}."
        documents.append(
            {
                "id": document_id,
                "path": f"03-marketing/{document_id}.md",
                "category": "marketing",
                "document_version": "1.0.0",
                "citation_id": f"mhk://ejixhole/{document_id}/2026.07.3",
                "sensitivity": "internal",
                "source_type": "owner_approved",
                "source_reference": "fuente aprobada de prueba",
                "checksum": git_blob_sha1(content),
                "review_due_at": "2099-01-19",
                "content": content,
            }
        )
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
        "documents": documents,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture(autouse=True)
def reset_service(monkeypatch):
    knowledge_service.reset()
    monkeypatch.delenv("MH_KNOWLEDGE_BUNDLE_PATH", raising=False)
    monkeypatch.delenv("MH_CORE_MINDHIGH_KEY", raising=False)
    monkeypatch.delenv("MH_CORE_EJIXHOLE_KEY", raising=False)
    monkeypatch.delenv("MH_CORE_OPERATIONS_KEY", raising=False)
    monkeypatch.delenv("MH_CORE_API_KEY", raising=False)
    yield
    knowledge_service.reset()


def test_genera_borrador_con_citas_y_aprobacion_humana(tmp_path, monkeypatch):
    bundle_path = tmp_path / "approved-bundle.json"
    _write_bundle(bundle_path)
    monkeypatch.setenv("MH_KNOWLEDGE_BUNDLE_PATH", str(bundle_path))
    monkeypatch.setenv("MH_CORE_MINDHIGH_KEY", "mindhigh-marketing-test-key")

    response = client.post(
        "/mindhigh/marketing/campaigns/draft",
        json=_brief(),
        headers=_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["knowledge_version"] == "2026.07.3"
    assert body["requires_human_approval"] is True
    assert body["dynamic_facts_used"] == []
    assert body["knowledge_document_ids"] == [
        "brand",
        "marketing_strategy",
        "offer",
        "agent_rules",
    ]
    assert len(body["knowledge_citations"]) == 4
    assert all(citation.startswith("mhk://ejixhole/") for citation in body["knowledge_citations"])
    assert len(body["contents"]) == 2


def test_falla_cerrado_sin_bundle(monkeypatch):
    monkeypatch.setenv("MH_CORE_MINDHIGH_KEY", "mindhigh-marketing-test-key")

    response = client.post(
        "/mindhigh/marketing/campaigns/draft",
        json=_brief(),
        headers=_headers(),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "El conocimiento aprobado necesario para la campaña no está disponible."
    )


def test_falla_cerrado_si_falta_documento_esencial(tmp_path, monkeypatch):
    bundle_path = tmp_path / "approved-bundle.json"
    _write_bundle(bundle_path, include_offer=False)
    monkeypatch.setenv("MH_KNOWLEDGE_BUNDLE_PATH", str(bundle_path))
    monkeypatch.setenv("MH_CORE_MINDHIGH_KEY", "mindhigh-marketing-test-key")

    response = client.post(
        "/mindhigh/marketing/campaigns/draft",
        json=_brief(),
        headers=_headers(),
    )

    assert response.status_code == 503


def test_rechaza_hechos_dinamicos_declarados_manualmente(tmp_path, monkeypatch):
    bundle_path = tmp_path / "approved-bundle.json"
    _write_bundle(bundle_path)
    monkeypatch.setenv("MH_KNOWLEDGE_BUNDLE_PATH", str(bundle_path))
    monkeypatch.setenv("MH_CORE_MINDHIGH_KEY", "mindhigh-marketing-test-key")

    response = client.post(
        "/mindhigh/marketing/campaigns/draft",
        json=_brief(
            call_to_action="Reserva por $100.",
            approved_dynamic_facts=["Precio $100 confirmado"],
        ),
        headers=_headers(),
    )

    assert response.status_code == 422
    assert "fuente operacional autorizada" in response.json()["detail"]


def test_rechaza_precio_sin_fuente_operacional(tmp_path, monkeypatch):
    bundle_path = tmp_path / "approved-bundle.json"
    _write_bundle(bundle_path)
    monkeypatch.setenv("MH_KNOWLEDGE_BUNDLE_PATH", str(bundle_path))
    monkeypatch.setenv("MH_CORE_MINDHIGH_KEY", "mindhigh-marketing-test-key")

    response = client.post(
        "/mindhigh/marketing/campaigns/draft",
        json=_brief(call_to_action="Reserva por $100."),
        headers=_headers(),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "La campaña contiene un dato dinámico no autorizado."


def test_ruta_requiere_identidad_mindhigh(tmp_path, monkeypatch):
    bundle_path = tmp_path / "approved-bundle.json"
    _write_bundle(bundle_path)
    monkeypatch.setenv("MH_KNOWLEDGE_BUNDLE_PATH", str(bundle_path))
    monkeypatch.setenv("MH_CORE_MINDHIGH_KEY", "mindhigh-marketing-test-key")

    response = client.post(
        "/mindhigh/marketing/campaigns/draft",
        json=_brief(),
    )

    assert response.status_code == 401
