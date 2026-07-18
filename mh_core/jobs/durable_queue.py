"""Cola SQL durable para trabajos de MH-Core."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import re
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, OperationalError

from mh_core.persistence.database import initialize_schema, session_factory
from mh_core.persistence.models import DurableJobRecord

_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,179}$")


class JobConflictError(ValueError):
    pass


class JobNotFoundError(LookupError):
    pass


class JobOwnershipError(RuntimeError):
    pass


@dataclass(frozen=True)
class JobSnapshot:
    id: str
    queue: str
    job_type: str
    payload: dict[str, Any]
    idempotency_key: str | None
    status: str
    priority: int
    attempts: int
    max_attempts: int
    available_at: datetime
    locked_at: datetime | None
    lock_expires_at: datetime | None
    locked_by: str | None
    last_error: str | None
    result: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True)
class EnqueueResult:
    job: JobSnapshot
    duplicate: bool


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _identifier(value: str, field: str, length: int) -> str:
    normalized = value.strip()
    if len(normalized) > length or not _ID.fullmatch(normalized):
        raise ValueError(f"{field} inválido")
    return normalized


def _payload(value: dict[str, Any] | None) -> tuple[dict[str, Any], str]:
    data = value or {}
    try:
        canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ValueError("payload debe ser JSON serializable") from exc
    if len(canonical.encode("utf-8")) > 131072:
        raise ValueError("payload excede 128 KiB")
    return data, canonical


def _snapshot(row: DurableJobRecord) -> JobSnapshot:
    return JobSnapshot(
        id=row.id,
        queue=row.queue,
        job_type=row.job_type,
        payload=dict(row.payload or {}),
        idempotency_key=row.idempotency_key,
        status=row.status,
        priority=row.priority,
        attempts=row.attempts,
        max_attempts=row.max_attempts,
        available_at=row.available_at,
        locked_at=row.locked_at,
        lock_expires_at=row.lock_expires_at,
        locked_by=row.locked_by,
        last_error=row.last_error,
        result=dict(row.result) if row.result is not None else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
        completed_at=row.completed_at,
    )


class DurableJobQueue:
    def __init__(self, engine: Engine | None = None, *, default_queue: str = "default") -> None:
        self.engine = initialize_schema(engine)
        self.sessions = session_factory(self.engine)
        self.default_queue = _identifier(default_queue, "queue", 80)

    def enqueue(
        self,
        job_type: str,
        payload: dict[str, Any] | None = None,
        *,
        queue: str | None = None,
        idempotency_key: str | None = None,
        priority: int = 0,
        max_attempts: int = 5,
        available_at: datetime | None = None,
    ) -> EnqueueResult:
        selected_queue = _identifier(queue or self.default_queue, "queue", 80)
        selected_type = _identifier(job_type, "job_type", 120)
        selected_key = _identifier(idempotency_key, "idempotency_key", 180) if idempotency_key else None
        data, canonical = _payload(payload)
        if not -100 <= priority <= 100:
            raise ValueError("priority fuera de rango")
        if not 1 <= max_attempts <= 20:
            raise ValueError("max_attempts fuera de rango")
        row = DurableJobRecord(
            id=str(uuid4()), queue=selected_queue, job_type=selected_type,
            payload=data, idempotency_key=selected_key, status="pending",
            priority=priority, attempts=0, max_attempts=max_attempts,
            available_at=available_at or utcnow(),
        )
        with self.sessions() as session:
            session.add(row)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                if not selected_key:
                    raise
                existing = session.scalar(select(DurableJobRecord).where(
                    DurableJobRecord.queue == selected_queue,
                    DurableJobRecord.idempotency_key == selected_key,
                ))
                if existing is None:
                    raise
                _, existing_canonical = _payload(dict(existing.payload or {}))
                if existing.job_type != selected_type or existing_canonical != canonical:
                    raise JobConflictError("La clave idempotente ya representa otro trabajo.")
                return EnqueueResult(_snapshot(existing), True)
            session.refresh(row)
            return EnqueueResult(_snapshot(row), False)

    def recover_abandoned(self, *, now: datetime | None = None) -> int:
        current = now or utcnow()
        recovered = 0
        with self.sessions() as session, session.begin():
            rows = session.scalars(select(DurableJobRecord).where(
                DurableJobRecord.status == "running",
                DurableJobRecord.lock_expires_at.is_not(None),
                DurableJobRecord.lock_expires_at <= current,
            ).with_for_update()).all()
            for row in rows:
                row.status = "dead_letter" if row.attempts >= row.max_attempts else "retry"
                row.available_at = current
                row.locked_at = row.lock_expires_at = None
                row.locked_by = None
                row.last_error = "Lease vencido antes de finalizar."
                row.updated_at = current
                if row.status == "dead_letter":
                    row.completed_at = current
                recovered += 1
        return recovered

    def claim(self, worker_id: str, *, queue: str | None = None, lease_seconds: int = 300, now: datetime | None = None) -> JobSnapshot | None:
        worker = _identifier(worker_id, "worker_id", 120)
        selected_queue = _identifier(queue or self.default_queue, "queue", 80)
        if not 30 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds fuera de rango")
        current = now or utcnow()
        self.recover_abandoned(now=current)
        expires = current + timedelta(seconds=lease_seconds)

        if self.engine.dialect.name == "postgresql":
            with self.sessions() as session, session.begin():
                row = session.scalar(select(DurableJobRecord).where(
                    DurableJobRecord.queue == selected_queue,
                    DurableJobRecord.status.in_(("pending", "retry")),
                    DurableJobRecord.available_at <= current,
                ).order_by(
                    DurableJobRecord.priority.desc(),
                    DurableJobRecord.available_at,
                    DurableJobRecord.created_at,
                ).with_for_update(skip_locked=True).limit(1))
                if row is None:
                    return None
                row.status = "running"
                row.attempts += 1
                row.locked_by = worker
                row.locked_at = current
                row.lock_expires_at = expires
                row.last_error = None
                session.flush()
                return _snapshot(row)

        for _ in range(5):
            with self.sessions() as session:
                job_id = session.scalar(select(DurableJobRecord.id).where(
                    DurableJobRecord.queue == selected_queue,
                    DurableJobRecord.status.in_(("pending", "retry")),
                    DurableJobRecord.available_at <= current,
                ).order_by(
                    DurableJobRecord.priority.desc(),
                    DurableJobRecord.available_at,
                    DurableJobRecord.created_at,
                ).limit(1))
                if job_id is None:
                    return None
                try:
                    changed = session.execute(update(DurableJobRecord).where(
                        DurableJobRecord.id == job_id,
                        DurableJobRecord.status.in_(("pending", "retry")),
                        DurableJobRecord.available_at <= current,
                    ).values(
                        status="running", attempts=DurableJobRecord.attempts + 1,
                        locked_by=worker, locked_at=current, lock_expires_at=expires,
                        last_error=None, updated_at=current,
                    ))
                    if changed.rowcount != 1:
                        session.rollback()
                        continue
                    session.commit()
                    return _snapshot(session.get(DurableJobRecord, job_id))
                except OperationalError:
                    session.rollback()
        return None

    def heartbeat(self, job_id: str, worker_id: str, *, lease_seconds: int = 300) -> JobSnapshot:
        worker = _identifier(worker_id, "worker_id", 120)
        current = utcnow()
        with self.sessions() as session:
            changed = session.execute(update(DurableJobRecord).where(
                DurableJobRecord.id == job_id,
                DurableJobRecord.status == "running",
                DurableJobRecord.locked_by == worker,
            ).values(lock_expires_at=current + timedelta(seconds=lease_seconds), updated_at=current))
            if changed.rowcount != 1:
                session.rollback()
                raise JobOwnershipError("Trabajo no asignado a este worker.")
            session.commit()
            return _snapshot(session.get(DurableJobRecord, job_id))

    def complete(self, job_id: str, worker_id: str, result: dict[str, Any] | None = None) -> JobSnapshot:
        worker = _identifier(worker_id, "worker_id", 120)
        data, _ = _payload(result)
        current = utcnow()
        with self.sessions() as session:
            changed = session.execute(update(DurableJobRecord).where(
                DurableJobRecord.id == job_id,
                DurableJobRecord.status == "running",
                DurableJobRecord.locked_by == worker,
            ).values(
                status="succeeded", result=data, locked_at=None,
                lock_expires_at=None, locked_by=None, completed_at=current,
                updated_at=current,
            ))
            if changed.rowcount != 1:
                session.rollback()
                raise JobOwnershipError("Trabajo no asignado a este worker.")
            session.commit()
            return _snapshot(session.get(DurableJobRecord, job_id))

    def fail(self, job_id: str, worker_id: str, error: BaseException | str, *, base_backoff_seconds: int = 30) -> JobSnapshot:
        worker = _identifier(worker_id, "worker_id", 120)
        current = utcnow()
        with self.sessions() as session, session.begin():
            row = session.scalar(select(DurableJobRecord).where(DurableJobRecord.id == job_id).with_for_update())
            if row is None:
                raise JobNotFoundError("Trabajo no encontrado.")
            if row.status != "running" or row.locked_by != worker:
                raise JobOwnershipError("Trabajo no asignado a este worker.")
            terminal = row.attempts >= row.max_attempts
            row.status = "dead_letter" if terminal else "retry"
            delay = min(3600, max(1, base_backoff_seconds) * (2 ** max(0, row.attempts - 1)))
            row.available_at = current if terminal else current + timedelta(seconds=delay)
            row.locked_at = row.lock_expires_at = None
            row.locked_by = None
            row.last_error = str(error).replace("\r", " ").replace("\n", " ")[:2000]
            row.updated_at = current
            if terminal:
                row.completed_at = current
            session.flush()
            return _snapshot(row)

    def retry_dead_letter(self, job_id: str) -> JobSnapshot:
        current = utcnow()
        with self.sessions() as session:
            changed = session.execute(update(DurableJobRecord).where(
                DurableJobRecord.id == job_id,
                DurableJobRecord.status == "dead_letter",
            ).values(
                status="pending", attempts=0, available_at=current,
                locked_at=None, lock_expires_at=None, locked_by=None,
                completed_at=None, last_error=None, updated_at=current,
            ))
            if changed.rowcount != 1:
                session.rollback()
                raise JobConflictError("El trabajo no está en dead-letter.")
            session.commit()
            return _snapshot(session.get(DurableJobRecord, job_id))

    def get(self, job_id: str) -> JobSnapshot:
        with self.sessions() as session:
            row = session.get(DurableJobRecord, job_id)
            if row is None:
                raise JobNotFoundError("Trabajo no encontrado.")
            return _snapshot(row)

    def list(self, *, queue: str | None = None, status: str | None = None, job_type: str | None = None, limit: int = 100, offset: int = 0) -> list[JobSnapshot]:
        if not 1 <= limit <= 200 or offset < 0:
            raise ValueError("Paginación inválida")
        query = select(DurableJobRecord)
        if queue:
            query = query.where(DurableJobRecord.queue == queue)
        if status:
            query = query.where(DurableJobRecord.status == status)
        if job_type:
            query = query.where(DurableJobRecord.job_type == job_type)
        query = query.order_by(DurableJobRecord.created_at.desc()).limit(limit).offset(offset)
        with self.sessions() as session:
            return [_snapshot(row) for row in session.scalars(query).all()]

    def stats(self, *, queue: str | None = None) -> dict[str, int]:
        query = select(DurableJobRecord.status, func.count(DurableJobRecord.id)).group_by(DurableJobRecord.status)
        if queue:
            query = query.where(DurableJobRecord.queue == queue)
        with self.sessions() as session:
            result = {status: int(total) for status, total in session.execute(query).all()}
        result["total"] = sum(result.values())
        return result
