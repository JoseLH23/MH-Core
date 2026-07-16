from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import uuid4

from fastapi.testclient import TestClient

from mh_core.app import app
from mh_core.integrations.ejixhole_events import (
    EjixholeEventEnvelope,
    SqliteEjixholeEventInbox,
)


API_KEY = "mh-core-api-key-for-event-status-tests"


def payload(event_id: str) -> dict:
    return {
        "event_id": event_id,
        "event_key": "reservation.created:501",
        "event_type": "reservation.created",
        "schema_version": 1,
        "source": "ejixhole",
        "occurred_at": datetime(2026, 7, 16, 15, 0, tzinfo=timezone.utc).isoformat(),
        "aggregate": {"type": "reservation", "id": "501"},
        "payload": {
            "reservation_id": 501,
            "service_id": 1,
            "unit_id": None,
            "reservation_type": "entrada",
            "arrival_date": "2026-08-20",
            "departure_date": "2026-08-20",
            "people": 2,
            "origin": "portal",
            "total": "200.00",
            "status": "pendiente",
        },
    }


def test_status_requiere_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv("MH_CORE_API_KEY", API_KEY)
    monkeypatch.setenv("EJIXHOLE_EVENT_INBOX_PATH", str(tmp_path / "events.sqlite3"))

    response = TestClient(app).get("/integrations/ejixhole/events/status")

    assert response.status_code == 401


def test_status_y_busqueda_confirman_un_solo_evento(monkeypatch, tmp_path):
    inbox_path = tmp_path / "events.sqlite3"
    event_id = str(uuid4())
    raw = json.dumps(payload(event_id), sort_keys=True, separators=(",", ":")).encode()
    inbox = SqliteEjixholeEventInbox(inbox_path)
    inbox.store(EjixholeEventEnvelope.model_validate(payload(event_id)), raw)

    monkeypatch.setenv("MH_CORE_API_KEY", API_KEY)
    monkeypatch.setenv("EJIXHOLE_EVENT_SIGNING_SECRET", "s" * 48)
    monkeypatch.setenv("EJIXHOLE_EVENT_INBOX_PATH", str(inbox_path))
    client = TestClient(app, headers={"X-API-Key": API_KEY})

    status = client.get("/integrations/ejixhole/events/status")
    event = client.get(f"/integrations/ejixhole/events/{event_id}")

    assert status.status_code == 200
    assert status.json()["configured"] is True
    assert status.json()["custom_storage_path_configured"] is True
    assert status.json()["journal_mode"] == "wal"
    assert status.json()["total_events"] == 1
    assert status.json()["by_event_type"] == {"reservation.created": 1}
    assert status.json()["latest_event_id"] == event_id

    assert event.status_code == 200
    assert event.json()["event_id"] == event_id
    assert event.json()["unique_record"] is True
    assert "payload" not in event.json()


def test_evento_inexistente_responde_404(monkeypatch, tmp_path):
    monkeypatch.setenv("MH_CORE_API_KEY", API_KEY)
    monkeypatch.setenv("EJIXHOLE_EVENT_INBOX_PATH", str(tmp_path / "events.sqlite3"))
    client = TestClient(app, headers={"X-API-Key": API_KEY})

    response = client.get(f"/integrations/ejixhole/events/{uuid4()}")

    assert response.status_code == 404
