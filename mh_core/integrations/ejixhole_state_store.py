"""Selecciona almacenamiento durable para el estado analítico de EjiXhole."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from threading import Lock

from sqlalchemy.engine import Engine

from mh_core.integrations.ejixhole_events import (
    EjixholeEventConflictError,
    EjixholeEventEnvelope,
    InboxStoreResult,
    SqliteEjixholeEventInbox,
)
from mh_core.integrations.ejixhole_sql_connection import PostgresCompatConnection
from mh_core.persistence.database import create_engine_for_url, normalize_database_url

_ENGINES: dict[str, Engine] = {}
_ENGINE_LOCK = Lock()


def _engine_for(url: str) -> Engine:
    normalized = normalize_database_url(url)
    with _ENGINE_LOCK:
        engine = _ENGINES.get(normalized)
        if engine is None:
            engine = create_engine_for_url(normalized)
            _ENGINES[normalized] = engine
        return engine


class ConfiguredEjixholeEventInbox:
    """Mantiene SQLite por defecto y usa PostgreSQL solo con configuración explícita."""

    def __init__(
        self,
        path: str | Path | None = None,
        *,
        database_url: str | None = None,
    ) -> None:
        configured_path = path or os.getenv("EJIXHOLE_EVENT_INBOX_PATH", "").strip()
        configured_url = database_url or os.getenv("EJIXHOLE_STATE_DATABASE_URL", "").strip()
        if configured_path or not configured_url:
            self.backend = "sqlite"
            self._delegate = SqliteEjixholeEventInbox(configured_path or None)
            self.path = self._delegate.path
            self.engine = None
            return

        self.backend = "postgresql"
        self._delegate = None
        self.path = None
        self.engine = _engine_for(configured_url)
        self._initialize_postgres()

    def _connect(self):
        if self._delegate is not None:
            return self._delegate._connect()
        return PostgresCompatConnection(self.engine)

    def _initialize_postgres(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ejixhole_event_inbox (
                    event_id TEXT PRIMARY KEY,
                    event_key TEXT NOT NULL UNIQUE,
                    event_type TEXT NOT NULL,
                    schema_version INTEGER NOT NULL,
                    aggregate_type TEXT NOT NULL,
                    aggregate_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    envelope_sha256 TEXT NOT NULL,
                    received_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS ix_ejixhole_event_type "
                "ON ejixhole_event_inbox(event_type, received_at)"
            )

    def store(self, envelope: EjixholeEventEnvelope, raw_body: bytes) -> InboxStoreResult:
        if self._delegate is not None:
            return self._delegate.store(envelope, raw_body)

        envelope_hash = hashlib.sha256(raw_body).hexdigest()
        event_id = str(envelope.event_id)
        payload_json = json.dumps(
            envelope.payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        values = (
            event_id,
            envelope.event_key,
            envelope.event_type,
            envelope.schema_version,
            envelope.aggregate.type,
            envelope.aggregate.id,
            envelope.occurred_at.isoformat(),
            payload_json,
            envelope_hash,
            datetime.now(timezone.utc).isoformat(),
        )
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO ejixhole_event_inbox (
                    event_id, event_key, event_type, schema_version,
                    aggregate_type, aggregate_id, occurred_at,
                    payload_json, envelope_sha256, received_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING
                """,
                values,
            )
            if cursor.rowcount == 1:
                return InboxStoreResult(duplicate=False)
            existing = connection.execute(
                """
                SELECT event_id, event_key, envelope_sha256
                FROM ejixhole_event_inbox
                WHERE event_id = ? OR event_key = ?
                LIMIT 1
                """,
                (event_id, envelope.event_key),
            ).fetchone()
            if existing is None or existing["envelope_sha256"] != envelope_hash:
                raise EjixholeEventConflictError(
                    "El event_id o event_key ya existe con otro contenido."
                )
            return InboxStoreResult(duplicate=True)

    def count(self) -> int:
        if self._delegate is not None:
            return self._delegate.count()
        with self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM ejixhole_event_inbox").fetchone()[0])
