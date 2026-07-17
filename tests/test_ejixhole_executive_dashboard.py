from datetime import date, datetime, timezone
import json
from uuid import uuid4

from fastapi.testclient import TestClient

from mh_core.app import app
from mh_core.integrations.ejixhole_events import EjixholeEventEnvelope, SqliteEjixholeEventInbox
from mh_core.integrations.ejixhole_executive_dashboard import EjixholeExecutiveDashboardService


def _store(path, event_type, event_key, aggregate_type, aggregate_id, payload, occurred_at):
    envelope = EjixholeEventEnvelope.model_validate({
        "event_id": str(uuid4()), "event_key": event_key, "event_type": event_type,
        "schema_version": 1, "source": "ejixhole", "occurred_at": occurred_at,
        "aggregate": {"type": aggregate_type, "id": str(aggregate_id)}, "payload": payload,
    })
    SqliteEjixholeEventInbox(path).store(
        envelope,
        json.dumps(envelope.model_dump(mode="json"), sort_keys=True).encode(),
    )


def _seed(path):
    current = datetime(2026, 7, 16, 15, 0, tzinfo=timezone.utc).isoformat()
    previous = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc).isoformat()
    _store(path, "reservation.created", "reservation.created:101", "reservation", 101, {
        "reservation_id": 101, "service_id": 1, "unit_id": None, "reservation_type": "entrada",
        "arrival_date": "2026-07-18", "departure_date": "2026-07-18", "people": 2,
        "origin": "portal", "total": "200.00", "status": "pendiente",
    }, current)
    _store(path, "payment.recorded", "payment.recorded:501", "payment", 501, {
        "payment_id": 501, "reservation_id": 101, "amount": "150.00", "payment_type": "anticipo",
        "payment_method": "transferencia", "paid_amount": "150.00", "pending_balance": "50.00",
        "reservation_status": "confirmada",
    }, current)
    _store(path, "reservation.created", "reservation.created:99", "reservation", 99, {
        "reservation_id": 99, "service_id": 1, "unit_id": None, "reservation_type": "camping",
        "arrival_date": "2026-07-08", "departure_date": "2026-07-09", "people": 1,
        "origin": "recepcion", "total": "100.00", "status": "pendiente",
    }, previous)
    _store(path, "payment.recorded", "payment.recorded:499", "payment", 499, {
        "payment_id": 499, "reservation_id": 99, "amount": "100.00", "payment_type": "pago_saldo",
        "payment_method": "efectivo", "paid_amount": "100.00", "pending_balance": "0.00",
        "reservation_status": "confirmada",
    }, previous)


def test_dashboard_calcula_kpis_y_tendencias(tmp_path):
    path = tmp_path / "events.sqlite3"
    _seed(path)
    result = EjixholeExecutiveDashboardService(path).build(date(2026, 7, 16), days=7)
    assert result["access"] == "read_only"
    assert result["kpis"]["net_revenue"] == "150.00"
    assert result["kpis"]["pending_balance"] == "50.00"
    assert result["kpis"]["upcoming_reservations_7_days"] == 1
    assert result["trends"]["net_revenue_percent"] == 50.0
    assert len(result["timeline"]) == 7
    assert result["recommendations"]
    serialized = json.dumps(result).lower()
    assert "email" not in serialized and "telefono" not in serialized and "nombre" not in serialized


def test_dashboard_es_idempotente(tmp_path):
    path = tmp_path / "events.sqlite3"
    _seed(path)
    service = EjixholeExecutiveDashboardService(path)
    first = service.build(date(2026, 7, 16), days=7)
    second = service.build(date(2026, 7, 16), days=7)
    assert first["processed_events"] == second["processed_events"] == 4
    assert first["kpis"] == second["kpis"]


def test_ruta_requiere_clave_y_valida_periodo(monkeypatch, tmp_path):
    path = tmp_path / "events.sqlite3"
    _seed(path)
    monkeypatch.setenv("MH_CORE_API_KEY", "executive-dashboard-test-key")
    monkeypatch.setenv("EJIXHOLE_EVENT_INBOX_PATH", str(path))
    client = TestClient(app)
    assert client.get("/integrations/ejixhole/executive-dashboard").status_code == 401
    response = client.get(
        "/integrations/ejixhole/executive-dashboard?business_date=2026-07-16&days=7",
        headers={"X-API-Key": "executive-dashboard-test-key"},
    )
    assert response.status_code == 200
    assert response.json()["period"]["days"] == 7
    assert client.get(
        "/integrations/ejixhole/executive-dashboard?days=32",
        headers={"X-API-Key": "executive-dashboard-test-key"},
    ).status_code == 422
