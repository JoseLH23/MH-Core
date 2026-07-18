"""Procesador EjiXhole que conserva SQLite y habilita PostgreSQL explícito."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from mh_core.integrations.ejixhole_event_processor import EjixholeEventProcessor, ProcessResult
from mh_core.integrations.ejixhole_state_store import ConfiguredEjixholeEventInbox


class ConfiguredEjixholeEventProcessor(EjixholeEventProcessor):
    def __init__(
        self,
        path: str | Path | None = None,
        *,
        database_url: str | None = None,
    ) -> None:
        self.inbox = ConfiguredEjixholeEventInbox(path, database_url=database_url)
        self._initialize()

    def process_pending(self, limit: int = 100) -> ProcessResult:
        if not 1 <= limit <= 1000:
            raise ValueError("limit debe estar entre 1 y 1000")
        if self.inbox.backend == "sqlite":
            return super().process_pending(limit)
        return self._process_postgres(limit)

    def _process_postgres(self, limit: int) -> ProcessResult:
        connection = self.inbox._connect()
        try:
            connection.execute("BEGIN")
            acquired = connection.execute(
                "SELECT pg_try_advisory_xact_lock(?)",
                (73124519,),
            ).fetchone()[0]
            if not acquired:
                connection.execute("ROLLBACK")
                return ProcessResult(scanned=0, processed=0, skipped=0)

            rows = connection.execute(
                """
                SELECT i.event_id, i.event_key, i.event_type, i.payload_json, i.received_at
                FROM ejixhole_event_inbox i
                WHERE NOT EXISTS (
                    SELECT 1 FROM ejixhole_processed_events p
                    WHERE p.event_id = i.event_id OR p.event_key = i.event_key
                )
                ORDER BY i.received_at, i.event_id
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            for row in rows:
                self._apply(connection, row["event_type"], json.loads(row["payload_json"]))
                connection.execute(
                    "INSERT INTO ejixhole_processed_events(event_id,event_key,processed_at) VALUES(?,?,?)",
                    (row["event_id"], row["event_key"], datetime.now(timezone.utc).isoformat()),
                )
            connection.execute("COMMIT")
            return ProcessResult(scanned=len(rows), processed=len(rows), skipped=0)
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
