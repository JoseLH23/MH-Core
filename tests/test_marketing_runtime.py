from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from apps.mindhigh.marketing_app import create_marketing_app
from apps.mindhigh.routes.marketing_routes import campaign_limiter, knowledge_service
from mh_core.knowledge.governed_bundle import git_blob_sha1


SERVICE_KEY = "e" * 48
CAMPAIGN_PATH = "/mindhigh/marketing/campaigns/draft"
REQUIRED_IDS = ("brand", "marketing_strategy", "offer", "agent_rules")


def _headers() -> dict[str, str]:
    return {
        "X-Service-ID": "ejixhole-backend",
        "X-API-Key": SERVICE_KEY,
    }


def _brief() -> dict:
    return {
        "name": "Escapada familiar",
        "objective": "impulsar_reservas",
        "audience": "familias que desean convivir en la naturaleza",
        "main_emotion": "tranquilidad y conexión",
        "offer_focus": "experiencia_general",
        "season": "temporada actual",
        "channels": ["facebook", "instagram_story"],
        "call_to_action": (
            "Consulta la información vigente y solicita tu reservación en el portal oficial."
        ),
    }


def _write_bundle(path, document_ids=REQUIRED_IDS) -> None:
    documents = []
    for document_id in document_ids:
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
    path.write_text(
        json.dumps(
            {
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
        ),
        encoding="utf-8",
    )


@pytest.fixture(autouse=True)
def clean_runtime(monkeypatch):
    for name in (
        "MH_CORE_API_KEY",
        "MH_CORE_ALLOW_LEGACY_API_KEY",
        "MH_CORE_EJIXHOLE_KEY",
        "MH_CORE_MINDHIGH_KEY",
        "MH_CORE_OPERATIONS_KEY",
        "MH_CORE_REVOKED_SERVICES",
        "MH_KNOWLEDGE_BUNDLE_PATH",
    ):
        monkeypatch.delenv(name, raising=False)
    knowledge_service.reset()
    campaign_limiter.reset()
    yield
    knowledge_service.reset()
    campaign_limiter.reset()


def test_produccion_expone_solo_salud_y_marketing():
    application = create_marketing_app("production")
    documented_paths = set(application.openapi()["paths"])

    assert documented_paths == {
        "/mindhigh/marketing/status",
        CAMPAIGN_PATH,
    }
    client = TestClient(application)
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 503
    assert client.get("/mindhigh/marketing/status").status_code == 401
    assert client.post(CAMPAIGN_PATH, json=_brief()).status_code == 401
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/mindhigh/run").status_code == 404
    assert client.get("/knowledge/search").status_code == 404
    assert client.get("/automation/status").status_code == 404


def test_liveness_no_revela_configuracion():
    response = TestClient(create_marketing_app("production")).get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_readiness_falla_cerrado_sin_clave_ni_bundle():
    response = TestClient(create_marketing_app("production")).get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_readiness_rechaza_credencial_debil(tmp_path, monkeypatch):
    bundle = tmp_path / "approved-bundle.json"
    _write_bundle(bundle)
    monkeypatch.setenv("MH_KNOWLEDGE_BUNDLE_PATH", str(bundle))
    monkeypatch.setenv("MH_CORE_EJIXHOLE_KEY", "corta")
    knowledge_service.reset()

    response = TestClient(create_marketing_app("production")).get("/health/ready")

    assert response.status_code == 503


def test_readiness_exige_documentos_esenciales_exactos(tmp_path, monkeypatch):
    bundle = tmp_path / "approved-bundle.json"
    _write_bundle(bundle, ("brand", "marketing_strategy", "offer", "faq"))
    monkeypatch.setenv("MH_KNOWLEDGE_BUNDLE_PATH", str(bundle))
    monkeypatch.setenv("MH_CORE_EJIXHOLE_KEY", SERVICE_KEY)
    knowledge_service.reset()

    response = TestClient(create_marketing_app("production")).get("/health/ready")

    assert response.status_code == 503


def test_rechaza_cuerpo_de_campana_mayor_a_64_kib():
    client = TestClient(create_marketing_app("production"))

    response = client.post(
        CAMPAIGN_PATH,
        content=b"{}",
        headers={"Content-Length": str(64 * 1024 + 1)},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "Solicitud demasiado grande."


def test_rechaza_cuerpo_fragmentado_sin_content_length():
    application = create_marketing_app("production")
    sent: list[dict] = []
    chunks = iter(
        [
            {"type": "http.request", "body": b"a" * 40_000, "more_body": True},
            {"type": "http.request", "body": b"b" * 30_000, "more_body": False},
        ]
    )

    async def receive():
        return next(chunks)

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": CAMPAIGN_PATH,
        "raw_path": CAMPAIGN_PATH.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 443),
    }

    asyncio.run(application(scope, receive, send))

    start = next(message for message in sent if message["type"] == "http.response.start")
    assert start["status"] == 413


def test_identidades_no_autenticadas_no_crean_buckets(monkeypatch):
    monkeypatch.setenv("MH_CORE_EJIXHOLE_KEY", SERVICE_KEY)
    client = TestClient(create_marketing_app("production"))

    responses = [
        client.post(
            CAMPAIGN_PATH,
            json=_brief(),
            headers={"X-Service-ID": f"inventada-{index}", "X-API-Key": "incorrecta"},
        )
        for index in range(50)
    ]

    assert all(response.status_code == 401 for response in responses)
    assert not campaign_limiter._llamadas


def test_limita_bucle_de_identidad_autenticada(monkeypatch):
    monkeypatch.setenv("MH_CORE_EJIXHOLE_KEY", SERVICE_KEY)
    client = TestClient(create_marketing_app("production"))

    responses = [
        client.post(CAMPAIGN_PATH, json=_brief(), headers=_headers())
        for _ in range(31)
    ]

    assert all(response.status_code != 429 for response in responses[:30])
    assert responses[30].status_code == 429
    assert int(responses[30].headers["retry-after"]) >= 1
    assert set(campaign_limiter._llamadas) == {"ejixhole-backend"}


def test_runtime_listo_genera_campana_citable(tmp_path, monkeypatch):
    bundle = tmp_path / "approved-bundle.json"
    _write_bundle(bundle)
    monkeypatch.setenv("MH_KNOWLEDGE_BUNDLE_PATH", str(bundle))
    monkeypatch.setenv("MH_CORE_EJIXHOLE_KEY", SERVICE_KEY)
    knowledge_service.reset()
    client = TestClient(create_marketing_app("production"))

    readiness = client.get("/health/ready")
    unauthorized = client.get("/mindhigh/marketing/status")
    status = client.get("/mindhigh/marketing/status", headers=_headers())
    campaign = client.post(
        CAMPAIGN_PATH,
        json=_brief(),
        headers=_headers(),
    )

    assert readiness.status_code == 200
    assert readiness.json() == {"status": "ready"}
    assert unauthorized.status_code == 401
    assert status.status_code == 200
    assert status.json()["available"] is True
    assert campaign.status_code == 200
    body = campaign.json()
    assert body["requires_human_approval"] is True
    assert body["knowledge_version"] == "2026.07.3"
    assert len(body["knowledge_citations"]) == 4
