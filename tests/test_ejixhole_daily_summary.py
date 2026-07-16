from datetime import date, datetime, timezone
import json
from uuid import uuid4

from fastapi.testclient import TestClient

from mh_core.app import app
from mh_core.integrations.ejixhole_daily_summary import EjixholeDailySummaryService
from mh_core.integrations.ejixhole_events import EjixholeEventEnvelope, SqliteEjixholeEventInbox


DAY = date(2026, 7, 16)
API_KEY = "daily-summary-test-api-key"


def store(path, event_type, event_key, aggregate_type, aggregate_id, payload):
    envelope = EjixholeEventEnvelope.model_validate({
        "event_id": str(uuid4()),
        "event_key": event_key,
        "event_type": event_type,
        "schema_version": 1,
        "source": "ejixhole",
        "occurred_at": datetime(2026, 7, 16, 15, 0, tzinfo=timezone.utc).isoformat(),
        "aggregate": {"type": aggregate_type, "id": str(aggregate_id)},
        "payload": payload,
    })
    raw = json.dumps(envelope.model_dump(mode="json"), sort_keys=True).encode()
    SqliteEjixholeEventInbox(path).store(envelope, raw)


def seed(path):
    store(path, "reservation.created", "reservation.created:101", "reservation", 101, {
        "reservation_id": 101, "service_id": 1, "unit_id": None,
        "reservation_type": "entrada", "arrival_date": "2026-07-16",
        "departure_date": "2026-07-16", "people": 2, "origin": "portal",
        "total": "200.00", "status": "pendiente",
    })
    store(path, "payment.recorded", "payment.recorded:501", "payment", 501, {
        "payment_id": 501, "reservation_id": 101, "amount": "150.00",
        "payment_type": "anticipo", "payment_method": "transferencia",
        "paid_amount": "150.00", "pending_balance": "50.00",
        "reservation_status": "confirmada",
    })
    store(path, "visit.completed", "visit.completed:101", "reservation", 101, {
        "reservation_id": 101, "reservation_type": "entrada",
        "arrival_date": "2026-07-16", "departure_date": "2026-07-16",
        "people": 2, "total": "200.00", "paid_amount": "200.00",
        "checkin_at": "2026-07-16T14:00:00Z", "checkout_at": "2026-07-16T18:00:00Z",
        "status": "completada",
    })


def test_resumen_diario_calcula_metricas_sin_datos_personales(tmp_path):
    path = tmp_path / "events.sqlite3"
    seed(path)

    result = EjixholeDailySummaryService(path).build(DAY)

    assert result["metrics"]["reservations_created"] == 1
    assert result["metrics"]["payments_recorded"] == 1
    assert result["metrics"]["gross_payments"] == "150.00"
    assert result["metrics"]["net_revenue"] == "150.00"
    assert result["metrics"]["visits_completed"] == 1
    assert result["metrics"]["pending_balance"] == "0.00"
    assert result["processed_events"] == 3
    serialized = json.dumps(result).lower()
    assert "email" not in serialized
    assert "telefono" not in serialized
    assert "nombre" not in serialized


def test_resumen_diario_es_idempotente(tmp_path):
    path = tmp_path / "events.sqlite3"
    seed(path)
    service = EjixholeDailySummaryService(path)

    first = service.build(DAY)
    second = service.build(DAY)

    assert first["processed_events"] == 3
    assert second["processed_events"] == 3
    assert second["metrics"] == first["metrics"]


def test_ruta_requiere_api_key_y_acepta_fecha(monkeypatch, tmp_path):
    path = tmp_path / "events.sqlite3"
    seed(path)
    monkeypatch.setenv("MH_CORE_API_KEY", API_KEY)
    monkeypatch.setenv("EJIXHOLE_EVENT_INBOX_PATH", str(path))
    client = TestClient(app)

    assert client.get("/integrations/ejixhole/daily-summary").status_code == 401

    response = client.get(
        "/integrations/ejixhole/daily-summary?business_date=2026-07-16",
        headers={"X-API-Key": API_KEY},
    )
    assert response.status_code == 200
    assert response.json()["business_date"] == "2026-07-16"
    assert response.json()["metrics"]["reservations_created"] == 1
