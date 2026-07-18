from __future__ import annotations

from contextlib import contextmanager
from datetime import date
import json
import os
import sqlite3
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy.engine import make_url

from mh_core.integrations.ejixhole_configured_processor import ConfiguredEjixholeEventProcessor
from mh_core.integrations.ejixhole_events import (
    EjixholeEventConflictError,
    EjixholeEventEnvelope,
    SqliteEjixholeEventInbox,
)
from mh_core.integrations.ejixhole_executive_dashboard import EjixholeExecutiveDashboardService
from mh_core.integrations.ejixhole_state_store import ConfiguredEjixholeEventInbox
from scripts.migrate_ejixhole_state import migrate


BASE_URL = os.getenv("MH_TEST_EJIXHOLE_POSTGRES_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="PostgreSQL desechable no configurado")


@contextmanager
def fresh_database():
    base = make_url(BASE_URL)
    database = f"mh_state_{uuid4().hex[:12]}"
    admin = base.set(database="postgres").render_as_string(hide_password=False)
    with psycopg.connect(admin, autocommit=True) as connection:
        connection.execute(f'CREATE DATABASE "{database}"')
    target = base.set(database=database).render_as_string(hide_password=False)
    try:
        yield target
    finally:
        with psycopg.connect(admin, autocommit=True) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s",
                (database,),
            )
            connection.execute(f'DROP DATABASE IF EXISTS "{database}"')


def reservation_event(reservation_id: int = 101, *, people: int = 2) -> tuple[EjixholeEventEnvelope, bytes]:
    payload = {
        "event_id": str(uuid4()),
        "event_key": f"reservation.created:{reservation_id}",
        "event_type": "reservation.created",
        "schema_version": 1,
        "source": "ejixhole",
        "occurred_at": "2026-07-18T12:00:00Z",
        "aggregate": {"type": "reservation", "id": str(reservation_id)},
        "payload": {
            "reservation_id": reservation_id,
            "service_id": 1,
            "unit_id": None,
            "reservation_type": "entrada",
            "arrival_date": "2026-07-20",
            "departure_date": "2026-07-20",
            "people": people,
            "origin": "portal",
            "total": "200.00",
            "status": "pendiente",
        },
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return EjixholeEventEnvelope.model_validate(payload), body


def test_postgres_deduplica_procesa_y_alimenta_dashboard(monkeypatch):
    with fresh_database() as url:
        monkeypatch.delenv("EJIXHOLE_EVENT_INBOX_PATH", raising=False)
        monkeypatch.setenv("EJIXHOLE_STATE_DATABASE_URL", url)
        inbox = ConfiguredEjixholeEventInbox(database_url=url)
        envelope, body = reservation_event()

        assert inbox.store(envelope, body).duplicate is False
        assert inbox.store(envelope, body).duplicate is True
        processor = ConfiguredEjixholeEventProcessor(database_url=url)
        result = processor.process_pending()

        assert result.processed == 1
        assert processor.summary()["reservations"] == 1
        dashboard = EjixholeExecutiveDashboardService().build(date(2026, 7, 18), days=7)
        assert dashboard["processed_events"] == 1
        assert dashboard["kpis"]["reservations_created"] == 1


def test_postgres_rechaza_identificador_con_otro_contenido():
    with fresh_database() as url:
        inbox = ConfiguredEjixholeEventInbox(database_url=url)
        envelope, body = reservation_event(202, people=2)
        inbox.store(envelope, body)
        changed_payload = envelope.model_dump(mode="json")
        changed_payload["payload"]["people"] = 3
        changed = EjixholeEventEnvelope.model_validate(changed_payload)
        changed_body = json.dumps(changed_payload, sort_keys=True, separators=(",", ":")).encode()
        with pytest.raises(EjixholeEventConflictError):
            inbox.store(changed, changed_body)


def test_migracion_sqlite_postgres_es_verificada_e_idempotente(tmp_path, monkeypatch):
    source = tmp_path / "events.sqlite3"
    inbox = SqliteEjixholeEventInbox(source)
    envelope, body = reservation_event(303)
    inbox.store(envelope, body)
    from mh_core.integrations.ejixhole_event_processor import EjixholeEventProcessor

    EjixholeEventProcessor(source).process_pending()
    with sqlite3.connect(source) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS ejixhole_weather_cache (cache_key TEXT PRIMARY KEY, payload_json TEXT NOT NULL, fetched_at TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO ejixhole_weather_cache VALUES (?,?,?)",
            ("weather-test", '{"status":"available"}', "2026-07-18T12:00:00Z"),
        )

    with fresh_database() as url:
        monkeypatch.setenv("EJIXHOLE_STATE_DATABASE_URL", url)
        preview = migrate(source, apply=False)
        first = migrate(source, apply=True)
        second = migrate(source, apply=True)

        assert preview["applied"] is False
        assert first["verified"] is True
        assert second["verified"] is True
        assert first["tables"]["ejixhole_event_inbox"]["match"] is True
        assert source.exists()
