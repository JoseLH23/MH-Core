"""Modelos SQL del estado crítico de MH-Core."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from mh_core.persistence.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


JOB_STATUSES = (
    "pending",
    "running",
    "retry",
    "succeeded",
    "dead_letter",
    "cancelled",
)


class DurableJobRecord(Base):
    __tablename__ = "mh_durable_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','running','retry','succeeded','dead_letter','cancelled')",
            name="ck_mh_durable_jobs_status",
        ),
        UniqueConstraint("queue", "idempotency_key", name="uq_mh_jobs_queue_idempotency"),
        Index(
            "ix_mh_jobs_claim",
            "queue",
            "status",
            "available_at",
            "priority",
            "created_at",
        ),
        Index("ix_mh_jobs_lock_expiry", "status", "lock_expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    queue: Mapped[str] = mapped_column(String(80), nullable=False, default="default")
    job_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    idempotency_key: Mapped[str | None] = mapped_column(String(180), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lock_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MemoryRecord(Base):
    __tablename__ = "mh_memories"
    __table_args__ = (
        UniqueConstraint("duplicate_key", name="uq_mh_memories_duplicate_key"),
        Index("ix_mh_memories_topic_created", "topic", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    duplicate_key: Mapped[str] = mapped_column(String(64), nullable=False)
    topic: Mapped[str | None] = mapped_column(String(300), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(120), nullable=True)
    best_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
