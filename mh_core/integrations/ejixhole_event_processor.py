"""Procesa una sola vez los eventos recibidos de EjiXhole y construye estado operativo."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3

from mh_core.integrations.ejixhole_events import SqliteEjixholeEventInbox


@dataclass(frozen=True)
class ProcessResult:
    scanned: int
    processed: int
    skipped: int


class EjixholeEventProcessor:
    def __init__(self, path: str | Path | None = None) -> None:
        self.inbox = SqliteEjixholeEventInbox(path)
        self._initialize()

    def _initialize(self) -> None:
        with self.inbox._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ejixhole_processed_events (
                    event_id TEXT PRIMARY KEY,
                    event_key TEXT NOT NULL UNIQUE,
                    processed_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ejixhole_operational_reservations (
                    reservation_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    reservation_type TEXT,
                    people INTEGER,
                    total TEXT,
                    paid_amount TEXT NOT NULL DEFAULT '0',
                    pending_balance TEXT,
                    arrival_date TEXT,
                    departure_date TEXT,
                    last_event_type TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def process_pending(self, limit: int = 100) -> ProcessResult:
        connection = self.inbox._connect()
        scanned = processed = skipped = 0
        try:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT event_id, event_key, event_type, payload_json, received_at
                FROM ejixhole_event_inbox
                ORDER BY received_at, event_id
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            for row in rows:
                scanned += 1
                exists = connection.execute(
                    "SELECT 1 FROM ejixhole_processed_events WHERE event_id = ? OR event_key = ?",
                    (row["event_id"], row["event_key"]),
                ).fetchone()
                if exists:
                    skipped += 1
                    continue
                payload = json.loads(row["payload_json"])
                self._apply(connection, row["event_type"], payload)
                connection.execute(
                    "INSERT INTO ejixhole_processed_events(event_id,event_key,processed_at) VALUES(?,?,?)",
                    (row["event_id"], row["event_key"], datetime.now(timezone.utc).isoformat()),
                )
                processed += 1
            connection.execute("COMMIT")
            return ProcessResult(scanned=scanned, processed=processed, skipped=skipped)
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    @staticmethod
    def _apply(connection: sqlite3.Connection, event_type: str, payload: dict) -> None:
        reservation_id = str(payload["reservation_id"])
        now = datetime.now(timezone.utc).isoformat()
        current = connection.execute(
            "SELECT * FROM ejixhole_operational_reservations WHERE reservation_id = ?",
            (reservation_id,),
        ).fetchone()
        values = dict(current) if current else {
            "reservation_id": reservation_id,
            "status": payload.get("status", "pendiente"),
            "reservation_type": None,
            "people": None,
            "total": None,
            "paid_amount": "0",
            "pending_balance": None,
            "arrival_date": None,
            "departure_date": None,
        }
        if event_type == "reservation.created":
            values.update(status=payload["status"], reservation_type=payload["reservation_type"], people=payload["people"], total=str(payload["total"]), arrival_date=payload["arrival_date"], departure_date=payload["departure_date"])
        elif event_type == "reservation.confirmed":
            values.update(status="confirmada", total=str(payload["total"]), paid_amount=str(payload["paid_amount"]))
        elif event_type == "payment.recorded":
            values.update(status=payload["reservation_status"], paid_amount=str(payload["paid_amount"]), pending_balance=str(payload["pending_balance"]))
        elif event_type == "reservation.cancelled":
            values.update(status="cancelada", paid_amount=str(payload["paid_amount"]), pending_balance=str(payload["pending_balance"]))
        elif event_type == "visit.completed":
            values.update(status="completada", reservation_type=payload["reservation_type"], people=payload["people"], total=str(payload["total"]), paid_amount=str(payload["paid_amount"]), pending_balance="0", arrival_date=payload["arrival_date"], departure_date=payload["departure_date"])
        connection.execute(
            """
            INSERT INTO ejixhole_operational_reservations (
                reservation_id,status,reservation_type,people,total,paid_amount,pending_balance,
                arrival_date,departure_date,last_event_type,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(reservation_id) DO UPDATE SET
                status=excluded.status,reservation_type=excluded.reservation_type,
                people=excluded.people,total=excluded.total,paid_amount=excluded.paid_amount,
                pending_balance=excluded.pending_balance,arrival_date=excluded.arrival_date,
                departure_date=excluded.departure_date,last_event_type=excluded.last_event_type,
                updated_at=excluded.updated_at
            """,
            (reservation_id, values["status"], values["reservation_type"], values["people"], values["total"], values["paid_amount"], values["pending_balance"], values["arrival_date"], values["departure_date"], event_type, now),
        )

    def summary(self) -> dict:
        self.process_pending()
        with self.inbox._connect() as connection:
            total = connection.execute("SELECT COUNT(*) FROM ejixhole_operational_reservations").fetchone()[0]
            rows = connection.execute("SELECT status, COUNT(*) total FROM ejixhole_operational_reservations GROUP BY status").fetchall()
            processed = connection.execute("SELECT COUNT(*) FROM ejixhole_processed_events").fetchone()[0]
        return {"processed_events": int(processed), "reservations": int(total), "by_status": {row["status"]: int(row["total"]) for row in rows}}
