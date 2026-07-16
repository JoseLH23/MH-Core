from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import hmac
import json
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from mh_core.app import app
from mh_core.integrations.ejixhole_events import (
    EjixholeEventConflictError,
    EjixholeEventEnvelope,
    SqliteEjixholeEventInbox,
)


SECRET = "event-signing-secret-for-tests-with-more-than-32-characters"
ROUTE = "/integrations/ejixhole/events"


def event_payload(*, event_id: str | None = None, people: int = 2) -> dict:
    identifier = event_id or str(uuid4())
    return {
        "event_id": identifier,
        "event_key": "reservation.created:101",
        "event_type": "reservation.created",
        "schema_version": 1,
        "source": "ejixhole",
        "occurred_at": "2026-07-16T14:00:00Z",
        "aggregate": {"type": "reservation", "id": "101"},
        "payload": {
            "reservation_id": 101,
            "service_id": 1,
            "unit_id": None,
            "reservation_type": "entrada",
            "arrival_date": "2026-08-20",
            "departure_date": "2026-08-20",
            "people": people,
            "origin": "portal",
            "total": "200.00",
            "status": "pendiente",
        },
    }


def encode(payload: dict) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def signed_headers(body: bytes, event_id: str, timestamp: int | None = None) -> dict:
    event_timestamp = timestamp if timestamp is not None else int(time.time())
    message = str(event_timestamp).encode("ascii") + b"." + body
    signature = hmac.new(SECRET.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-MH-Event-Id": event_id,
        "X-MH-Event-Timestamp": str(event_timestamp),
        "X-MH-Event-Signature": f"sha256={signature}",
    }


@pytest.fixture()
def configured_consumer(monkeypatch, tmp_path):
    inbox_path = tmp_path / "events.sqlite3"
    monkeypatch.setenv("EJIXHOLE_EVENT_SIGNING_SECRET", SECRET)
    monkeypatch.setenv("EJIXHOLE_EVENT_MAX_AGE_SECONDS", "300")
    monkeypatch.setenv("EJIXHOLE_EVENT_INBOX_PATH", str(inbox_path))
    return TestClient(app), inbox_path


def test_webhook_requiere_firma_aunque_no_usa_api_key_humana(configured_consumer):
    client, _ = configured_consumer
    payload = event_payload()

    response = client.post(ROUTE, json=payload)

    assert response.status_code == 401
    assert "cabeceras" in response.json()["detail"].lower()


def test_evento_valido_se_guarda_y_reintento_es_duplicado(configured_consumer):
    client, inbox_path = configured_consumer
    payload = event_payload()
    body = encode(payload)
    headers = signed_headers(body, payload["event_id"])

    first = client.post(ROUTE, content=body, headers=headers)
    second = client.post(ROUTE, content=body, headers=headers)

    assert first.status_code == 202
    assert first.json() == {
        "event_id": payload["event_id"],
        "accepted": True,
        "duplicate": False,
    }
    assert first.headers["X-MH-Event-Contract"] == "v1"
    assert first.headers["Cache-Control"] == "no-store"
    assert second.status_code == 202
    assert second.json()["duplicate"] is True
    assert SqliteEjixholeEventInbox(inbox_path).count() == 1


def test_rechaza_evento_firmado_fuera_de_ventana(configured_consumer):
    client, _ = configured_consumer
    payload = event_payload()
    body = encode(payload)
    headers = signed_headers(body, payload["event_id"], int(time.time()) - 301)

    response = client.post(ROUTE, content=body, headers=headers)

    assert response.status_code == 401
    assert "ventana" in response.json()["detail"].lower()


def test_rechaza_payload_con_dato_personal_no_definido(configured_consumer):
    client, _ = configured_consumer
    payload = event_payload()
    payload["payload"]["email"] = "privado@example.com"
    body = encode(payload)

    response = client.post(
        ROUTE,
        content=body,
        headers=signed_headers(body, payload["event_id"]),
    )

    assert response.status_code == 422


def test_mismo_event_id_con_otro_contenido_es_conflicto(configured_consumer):
    client, inbox_path = configured_consumer
    payload = event_payload()
    original = encode(payload)
    headers = signed_headers(original, payload["event_id"])
    assert client.post(ROUTE, content=original, headers=headers).status_code == 202

    modified_payload = event_payload(event_id=payload["event_id"], people=3)
    modified = encode(modified_payload)
    modified_headers = signed_headers(modified, payload["event_id"])
    response = client.post(ROUTE, content=modified, headers=modified_headers)

    assert response.status_code == 409
    assert SqliteEjixholeEventInbox(inbox_path).count() == 1


def test_deduplicacion_es_segura_con_varios_hilos(tmp_path):
    inbox = SqliteEjixholeEventInbox(tmp_path / "concurrent.sqlite3")
    payload = event_payload()
    body = encode(payload)
    envelope = EjixholeEventEnvelope.model_validate(payload)

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: inbox.store(envelope, body), range(16)))

    assert sum(not result.duplicate for result in results) == 1
    assert sum(result.duplicate for result in results) == 15
    assert inbox.count() == 1


def test_repositorio_detecta_mismo_event_key_con_otro_event_id(tmp_path):
    inbox = SqliteEjixholeEventInbox(tmp_path / "conflict.sqlite3")
    first_payload = event_payload()
    first_body = encode(first_payload)
    inbox.store(EjixholeEventEnvelope.model_validate(first_payload), first_body)

    second_payload = event_payload(event_id=str(uuid4()))
    second_body = encode(second_payload)

    with pytest.raises(EjixholeEventConflictError):
        inbox.store(EjixholeEventEnvelope.model_validate(second_payload), second_body)
