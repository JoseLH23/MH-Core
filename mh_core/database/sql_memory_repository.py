"""Repositorio SQL para recuerdos de MH-Core."""
from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from mh_core.database.memory_repository import MemoryRepository
from mh_core.models.memory import Memory
from mh_core.persistence.database import initialize_schema, session_factory
from mh_core.persistence.models import MemoryRecord


def memory_key(memory: Memory) -> str:
    value = json.dumps(memory.clave_duplicado(), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class SqlMemoryRepository(MemoryRepository):
    def __init__(self, engine: Engine | None = None) -> None:
        self.engine = initialize_schema(engine)
        self.sessions = session_factory(self.engine)

    @staticmethod
    def _memory(record: MemoryRecord) -> Memory:
        return Memory.model_validate(dict(record.payload))

    def guardar(self, memoria: Memory) -> Memory:
        saved = memoria if memoria.id else memoria.model_copy(update={"id": str(uuid4())})
        row = MemoryRecord(
            id=saved.id,
            duplicate_key=memory_key(saved),
            topic=saved.topic,
            decision=saved.decision,
            best_url=saved.best_url,
            payload=saved.model_dump(mode="json", exclude_none=False),
        )
        with self.sessions() as session:
            session.add(row)
            try:
                session.commit()
                return saved
            except IntegrityError:
                session.rollback()
                existing = session.scalar(select(MemoryRecord).where(MemoryRecord.duplicate_key == row.duplicate_key))
                if existing is None:
                    raise
                return self._memory(existing)

    def listar(self) -> list[Memory]:
        with self.sessions() as session:
            rows = session.scalars(select(MemoryRecord).order_by(MemoryRecord.created_at, MemoryRecord.id)).all()
            return [self._memory(row) for row in rows]

    def buscar_por_tema(self, tema: str) -> list[Memory]:
        normalized = tema.strip().lower()
        if not normalized:
            return []
        with self.sessions() as session:
            rows = session.scalars(
                select(MemoryRecord)
                .where(func.lower(MemoryRecord.topic).contains(normalized))
                .order_by(MemoryRecord.created_at)
            ).all()
            return [self._memory(row) for row in rows]

    def recientes(self, n: int = 10) -> list[Memory]:
        if n <= 0:
            return []
        with self.sessions() as session:
            rows = session.scalars(
                select(MemoryRecord).order_by(MemoryRecord.created_at.desc(), MemoryRecord.id.desc()).limit(n)
            ).all()
            return [self._memory(row) for row in rows]

    def buscar_duplicado(self, memoria: Memory) -> Memory | None:
        with self.sessions() as session:
            row = session.scalar(select(MemoryRecord).where(MemoryRecord.duplicate_key == memory_key(memoria)))
            return self._memory(row) if row else None

    def count(self) -> int:
        with self.sessions() as session:
            return int(session.scalar(select(func.count(MemoryRecord.id))) or 0)
