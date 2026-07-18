"""Conexión lazy a SQLite o PostgreSQL para estado crítico de MH-Core."""
from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from mh_core.core.config import DATABASE_DIR


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_engine_lock = Lock()


def normalize_database_url(url: str) -> str:
    value = url.strip()
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value[len("postgres://") :]
    if value.startswith("postgresql://") and "+" not in value.split("://", 1)[0]:
        return "postgresql+psycopg://" + value[len("postgresql://") :]
    return value


def configured_database_url() -> str:
    configured = os.getenv("MH_DATABASE_URL", "").strip()
    if configured:
        return normalize_database_url(configured)
    path = (Path(DATABASE_DIR) / "state" / "mh_core_state.sqlite3").resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+pysqlite:///{path.as_posix()}"


def create_engine_for_url(url: str | None = None) -> Engine:
    database_url = normalize_database_url(url) if url else configured_database_url()
    kwargs: dict = {"pool_pre_ping": True, "future": True}

    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
        if database_url.endswith(":memory:"):
            kwargs["poolclass"] = StaticPool
    else:
        kwargs.update(
            pool_size=int(os.getenv("MH_DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("MH_DB_MAX_OVERFLOW", "5")),
            pool_timeout=int(os.getenv("MH_DB_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("MH_DB_POOL_RECYCLE", "1800")),
        )

    engine = create_engine(database_url, **kwargs)
    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def configure_sqlite(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=30000")
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=FULL")
            except Exception:
                pass
            finally:
                cursor.close()
    return engine


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = create_engine_for_url()
    return _engine


def session_factory(engine: Engine | None = None):
    return sessionmaker(bind=engine or get_engine(), expire_on_commit=False, future=True)


def initialize_schema(engine: Engine | None = None) -> Engine:
    selected = engine or get_engine()
    from mh_core.persistence import models as _models  # noqa: F401

    Base.metadata.create_all(selected)
    return selected
