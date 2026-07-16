from datetime import datetime, timezone
import json
from uuid import uuid4

from mh_core.integrations.ejixhole_event_processor import EjixholeEventProcessor
from mh_core.integrations.ejixhole_events import EjixholeEventEnvelope, SqliteEjixholeEventInbox


def envelope(event_type: str, payload: dict, event_key: str) -> dict:
    aggregate_type = "payment" if event_type == "payment.recorded" else "reservation"
    aggregate_id = payload.get("payment_id") or payload["reservation_id"]
    return {
        "event_id": str(uuid4()),
        "event_key": event_key,
        "event_type": event_type,
        "schema_version": 1,
        "source": "ejixhole",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "aggregate": {"type": aggregate_type, "id": str(aggregate_id)},
        "payload": payload,
    }


def store(inbox, data):
    body = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    inbox.store(EjixholeEventEnvelope.model_validate(data), body)


def test_procesa_historial_una_sola_vez(tmp_path):
    path = tmp_path / "events.sqlite3"
    inbox = SqliteEjixholeEventInbox(path)
    created = envelope("reservation.created", {
        "reservation_id": 10, "service_id": 1, "unit_id": None,
        "reservation_type": "entrada", "arrival_date": "2026-08-20",
        "departure_date": "2026-08-20", "people": 2, "origin": "portal",
        "total": "200.00", "status": "pendiente",
    }, "reservation.created:10")
    payment = envelope("payment.recorded", {
        "payment_id": 50, "reservation_id": 10, "amount": "200.00",
        "payment_type": "pago_completo", "payment_method": "efectivo",
        "paid_amount": "200.00", "pending_balance": "0.00",
        "reservation_status": "confirmada",
    }, "payment.recorded:50")
    store(inbox, created)
    store(inbox, payment)

    processor = EjixholeEventProcessor(path)
    first = processor.process_pending()
    second = processor.process_pending()
    summary = processor.summary()

    assert first.processed == 2
    assert second.processed == 0
    assert second.skipped == 2
    assert summary == {
        "processed_events": 2,
        "reservations": 1,
        "by_status": {"confirmada": 1},
    }


def test_fallo_revierte_estado_y_marca_de_procesado(tmp_path, monkeypatch):
    path = tmp_path / "events.sqlite3"
    inbox = SqliteEjixholeEventInbox(path)
    data = envelope("reservation.created", {
        "reservation_id": 20, "service_id": 1, "unit_id": None,
        "reservation_type": "entrada", "arrival_date": "2026-08-21",
        "departure_date": "2026-08-21", "people": 1, "origin": "portal",
        "total": "100.00", "status": "pendiente",
    }, "reservation.created:20")
    store(inbox, data)
    processor = EjixholeEventProcessor(path)

    monkeypatch.setattr(processor, "_apply", lambda *_: (_ for _ in ()).throw(RuntimeError("fallo")))
    try:
        processor.process_pending()
    except RuntimeError:
        pass

    with inbox._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM ejixhole_processed_events").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM ejixhole_operational_reservations").fetchone()[0] == 0
