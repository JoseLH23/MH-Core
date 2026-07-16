"""Estado operativo seguro de la bandeja de eventos recibidos de EjiXhole."""
from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from mh_core.integrations.ejixhole_events import SqliteEjixholeEventInbox


class EjixholeInboxStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configured: bool
    custom_storage_path_configured: bool
    journal_mode: str
    total_events: int
    by_event_type: dict[str, int]
    latest_event_id: UUID | None
    latest_event_type: str | None
    latest_received_at: datetime | None


class EjixholeInboxEventStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_key: str
    event_type: str
    schema_version: Literal[1]
    aggregate_type: Literal["reservation", "payment"]
    aggregate_id: str
    occurred_at: datetime
    received_at: datetime
    unique_record: Literal[True] = True


class EjixholeEventInboxInspector:
    """Consulta metadatos de entrega sin devolver el payload del negocio."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.inbox = SqliteEjixholeEventInbox(path)

    def status(self) -> EjixholeInboxStatus:
        with self.inbox._connect() as connection:
            journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
            rows = connection.execute(
                """
                SELECT event_type, COUNT(*) AS total
                FROM ejixhole_event_inbox
                GROUP BY event_type
                ORDER BY event_type
                """
            ).fetchall()
            latest = connection.execute(
                """
                SELECT event_id, event_type, received_at
                FROM ejixhole_event_inbox
                ORDER BY received_at DESC, event_id DESC
                LIMIT 1
                """
            ).fetchone()

        configured_secret = os.getenv("EJIXHOLE_EVENT_SIGNING_SECRET", "").strip()
        configured_path = os.getenv("EJIXHOLE_EVENT_INBOX_PATH", "").strip()
        return EjixholeInboxStatus(
            configured=len(configured_secret) >= 32,
            custom_storage_path_configured=bool(configured_path),
            journal_mode=journal_mode.lower(),
            total_events=sum(int(row["total"]) for row in rows),
            by_event_type={row["event_type"]: int(row["total"]) for row in rows},
            latest_event_id=UUID(latest["event_id"]) if latest else None,
            latest_event_type=latest["event_type"] if latest else None,
            latest_received_at=datetime.fromisoformat(latest["received_at"]) if latest else None,
        )

    def event(self, event_id: UUID) -> EjixholeInboxEventStatus | None:
        with self.inbox._connect() as connection:
            row = connection.execute(
                """
                SELECT event_id, event_key, event_type, schema_version,
                       aggregate_type, aggregate_id, occurred_at, received_at
                FROM ejixhole_event_inbox
                WHERE event_id = ?
                LIMIT 1
                """,
                (str(event_id),),
            ).fetchone()
        if row is None:
            return None
        return EjixholeInboxEventStatus(
            event_id=UUID(row["event_id"]),
            event_key=row["event_key"],
            event_type=row["event_type"],
            schema_version=row["schema_version"],
            aggregate_type=row["aggregate_type"],
            aggregate_id=row["aggregate_id"],
            occurred_at=datetime.fromisoformat(row["occurred_at"]),
            received_at=datetime.fromisoformat(row["received_at"]),
        )
