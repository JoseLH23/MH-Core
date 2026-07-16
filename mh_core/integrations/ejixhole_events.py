"""Recepción autenticada e idempotente de eventos de dominio de EjiXhole."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import hmac
import json
import os
from pathlib import Path
import sqlite3
import time
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mh_core.core.config import DATABASE_DIR


EVENT_CONTRACT_VERSION = "v1"
EVENT_SIGNATURE_PREFIX = "sha256="
DEFAULT_MAX_AGE_SECONDS = 300
MAX_EVENT_BODY_BYTES = 64 * 1024


class EjixholeEventConfigurationError(RuntimeError):
    """La recepción de eventos no está configurada de forma segura."""


class EjixholeEventAuthenticationError(ValueError):
    """La firma, fecha o identidad del evento no es válida."""


class EjixholeEventConflictError(ValueError):
    """Un identificador ya recibido intenta representar otro contenido."""


class ReservationCreatedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reservation_id: int = Field(gt=0)
    service_id: int = Field(gt=0)
    unit_id: int | None = Field(default=None, gt=0)
    reservation_type: Literal["entrada", "camping", "hospedaje"]
    arrival_date: date
    departure_date: date
    people: int = Field(gt=0)
    origin: Literal["recepcion", "recepcion_express", "portal", "telefono"]
    total: Decimal = Field(ge=0)
    status: Literal["pendiente"]


class ReservationConfirmedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reservation_id: int = Field(gt=0)
    status: Literal["confirmada"]
    total: Decimal = Field(ge=0)
    paid_amount: Decimal = Field(ge=0)
    confirmation_source: Literal["manual", "payment"]


class PaymentRecordedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_id: int = Field(gt=0)
    reservation_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0)
    payment_type: Literal["anticipo", "pago_completo", "pago_saldo", "reembolso"]
    payment_method: Literal["efectivo", "tarjeta", "transferencia", "otro"]
    paid_amount: Decimal = Field(ge=0)
    pending_balance: Decimal
    reservation_status: Literal[
        "pendiente", "confirmada", "en_curso", "completada", "cancelada"
    ]


class ReservationCancelledPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reservation_id: int = Field(gt=0)
    status: Literal["cancelada"]
    paid_amount: Decimal = Field(ge=0)
    pending_balance: Decimal


class VisitCompletedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reservation_id: int = Field(gt=0)
    reservation_type: Literal["entrada", "camping", "hospedaje"]
    arrival_date: date
    departure_date: date
    people: int = Field(gt=0)
    total: Decimal = Field(ge=0)
    paid_amount: Decimal = Field(ge=0)
    checkin_at: datetime
    checkout_at: datetime
    status: Literal["completada"]


_PAYLOAD_MODELS: dict[str, type[BaseModel]] = {
    "reservation.created": ReservationCreatedPayload,
    "reservation.confirmed": ReservationConfirmedPayload,
    "payment.recorded": PaymentRecordedPayload,
    "reservation.cancelled": ReservationCancelledPayload,
    "visit.completed": VisitCompletedPayload,
}


class EventAggregate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["reservation", "payment"]
    id: str = Field(min_length=1, max_length=64)


class EjixholeEventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_key: str = Field(min_length=3, max_length=160)
    event_type: Literal[
        "reservation.created",
        "reservation.confirmed",
        "payment.recorded",
        "reservation.cancelled",
        "visit.completed",
    ]
    schema_version: Literal[1]
    source: Literal["ejixhole"]
    occurred_at: datetime
    aggregate: EventAggregate
    payload: dict[str, Any]

    @model_validator(mode="after")
    def validate_contract(self) -> "EjixholeEventEnvelope":
        if not self.event_key.startswith(f"{self.event_type}:"):
            raise ValueError("event_key no corresponde al tipo de evento")

        payload_model = _PAYLOAD_MODELS[self.event_type]
        validated_payload = payload_model.model_validate(self.payload)
        payload = validated_payload.model_dump(mode="json")

        if self.event_type == "payment.recorded":
            expected_type = "payment"
            expected_id = str(payload["payment_id"])
        else:
            expected_type = "reservation"
            expected_id = str(payload["reservation_id"])

        if self.aggregate.type != expected_type or self.aggregate.id != expected_id:
            raise ValueError("aggregate no corresponde al payload del evento")

        self.payload = payload
        return self


class EjixholeEventReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    accepted: Literal[True] = True
    duplicate: bool


class EjixholeEventVerifier:
    def __init__(
        self,
        secret: str | None = None,
        max_age_seconds: int | None = None,
        now: callable | None = None,
    ) -> None:
        configured_secret = (
            secret if secret is not None else os.getenv("EJIXHOLE_EVENT_SIGNING_SECRET", "")
        )
        self.secret = configured_secret.strip()
        if len(self.secret) < 32:
            raise EjixholeEventConfigurationError(
                "EJIXHOLE_EVENT_SIGNING_SECRET no está configurada o es demasiado corta."
            )

        configured_age = max_age_seconds
        if configured_age is None:
            raw_age = os.getenv(
                "EJIXHOLE_EVENT_MAX_AGE_SECONDS", str(DEFAULT_MAX_AGE_SECONDS)
            )
            try:
                configured_age = int(raw_age)
            except ValueError as exc:
                raise EjixholeEventConfigurationError(
                    "EJIXHOLE_EVENT_MAX_AGE_SECONDS debe ser entero."
                ) from exc
        if configured_age < 30 or configured_age > 3600:
            raise EjixholeEventConfigurationError(
                "EJIXHOLE_EVENT_MAX_AGE_SECONDS debe estar entre 30 y 3600."
            )

        self.max_age_seconds = configured_age
        self.now = now or time.time

    def verify(
        self,
        body: bytes,
        *,
        event_id: str | None,
        timestamp: str | None,
        signature: str | None,
    ) -> UUID:
        if not event_id or not timestamp or not signature:
            raise EjixholeEventAuthenticationError(
                "Faltan cabeceras de autenticación del evento."
            )

        try:
            parsed_event_id = UUID(event_id)
            parsed_timestamp = int(timestamp)
        except (ValueError, TypeError) as exc:
            raise EjixholeEventAuthenticationError(
                "Identificador o timestamp del evento inválido."
            ) from exc

        age = abs(int(self.now()) - parsed_timestamp)
        if age > self.max_age_seconds:
            raise EjixholeEventAuthenticationError(
                "El timestamp del evento está fuera de la ventana permitida."
            )

        if not signature.startswith(EVENT_SIGNATURE_PREFIX):
            raise EjixholeEventAuthenticationError("Formato de firma inválido.")

        signed_content = timestamp.encode("ascii") + b"." + body
        expected = hmac.new(
            self.secret.encode("utf-8"), signed_content, hashlib.sha256
        ).hexdigest()
        provided = signature[len(EVENT_SIGNATURE_PREFIX) :]
        if not hmac.compare_digest(provided.encode("ascii", "ignore"), expected.encode("ascii")):
            raise EjixholeEventAuthenticationError("Firma del evento inválida.")

        return parsed_event_id


@dataclass(frozen=True)
class InboxStoreResult:
    duplicate: bool


class SqliteEjixholeEventInbox:
    """Bandeja de entrada durable con deduplicación entre hilos y procesos."""

    def __init__(self, path: str | Path | None = None) -> None:
        configured_path = path or os.getenv("EJIXHOLE_EVENT_INBOX_PATH")
        self.path = Path(configured_path) if configured_path else (
            DATABASE_DIR / "integrations" / "ejixhole_events.sqlite3"
        )
        self.path = self.path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=10,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = FULL")
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
        envelope_hash = hashlib.sha256(raw_body).hexdigest()
        event_id = str(envelope.event_id)
        received_at = datetime.now(timezone.utc).isoformat()
        payload_json = json.dumps(
            envelope.payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT event_id, event_key, envelope_sha256
                FROM ejixhole_event_inbox
                WHERE event_id = ? OR event_key = ?
                LIMIT 1
                """,
                (event_id, envelope.event_key),
            ).fetchone()
            if existing is not None:
                if existing["envelope_sha256"] != envelope_hash:
                    connection.execute("ROLLBACK")
                    raise EjixholeEventConflictError(
                        "El event_id o event_key ya existe con otro contenido."
                    )
                connection.execute("COMMIT")
                return InboxStoreResult(duplicate=True)

            connection.execute(
                """
                INSERT INTO ejixhole_event_inbox (
                    event_id, event_key, event_type, schema_version,
                    aggregate_type, aggregate_id, occurred_at,
                    payload_json, envelope_sha256, received_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    envelope.event_key,
                    envelope.event_type,
                    envelope.schema_version,
                    envelope.aggregate.type,
                    envelope.aggregate.id,
                    envelope.occurred_at.isoformat(),
                    payload_json,
                    envelope_hash,
                    received_at,
                ),
            )
            connection.execute("COMMIT")
            return InboxStoreResult(duplicate=False)
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM ejixhole_event_inbox"
            ).fetchone()
            return int(row["total"])
