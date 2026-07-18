"""Salud operativa de MH-Core sin exponer secretos ni datos de negocio."""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import Lock
import time

from sqlalchemy import text

from mh_core.integrations.ejixhole_state_store import ConfiguredEjixholeEventInbox
from mh_core.jobs.durable_queue import DurableJobQueue
from mh_core.persistence.database import get_engine


class OperationalHealthService:
    def __init__(self, sample_limit: int = 1440) -> None:
        self._lock = Lock()
        self._samples: deque[dict] = deque(maxlen=sample_limit)
        self._started_at = datetime.now(timezone.utc)

    @staticmethod
    def _timed_check(callable_check) -> tuple[bool, int, object]:
        started = time.perf_counter()
        try:
            detail = callable_check()
            return True, int((time.perf_counter() - started) * 1000), detail
        except Exception:
            return False, int((time.perf_counter() - started) * 1000), None

    def _persistence(self) -> dict:
        engine = get_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"backend": engine.dialect.name}

    @staticmethod
    def _ejixhole_state() -> dict:
        inbox = ConfiguredEjixholeEventInbox()
        with inbox._connect() as connection:
            connection.execute("SELECT 1").fetchone()
        return {"backend": inbox.backend}

    @staticmethod
    def _durable_jobs() -> dict:
        stats = DurableJobQueue().stats()
        return {
            "pending": stats.get("pending", 0) + stats.get("retry", 0),
            "running": stats.get("running", 0),
            "dead_letter": stats.get("dead_letter", 0),
        }

    def sample(self) -> dict:
        checks = {}
        for name, operation in (
            ("persistence", self._persistence),
            ("ejixhole_state", self._ejixhole_state),
            ("durable_jobs", self._durable_jobs),
        ):
            ok, latency_ms, detail = self._timed_check(operation)
            checks[name] = {
                "status": "up" if ok else "down",
                "latency_ms": latency_ms,
                **(detail or {}),
            }

        healthy = all(check["status"] == "up" for check in checks.values())
        sample = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "healthy": healthy,
            "checks": checks,
        }
        with self._lock:
            self._samples.append(sample)
        return sample

    def summary(self) -> dict:
        current = self.sample()
        with self._lock:
            samples = list(self._samples)
        healthy_samples = sum(1 for item in samples if item["healthy"])
        availability = healthy_samples / len(samples) * 100 if samples else 100.0
        target = 99.5
        dead_letters = current["checks"]["durable_jobs"].get("dead_letter", 0)
        checks = {
            "availability": availability >= target,
            "dependencies": current["healthy"],
            "dead_letter": dead_letters == 0,
        }
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "started_at": self._started_at.isoformat(),
            "status": "healthy" if all(checks.values()) else "degraded",
            "current": current,
            "slo": {
                "availability_percent": round(availability, 3),
                "target_percent": target,
                "samples": len(samples),
                "healthy_samples": healthy_samples,
                "checks": checks,
            },
        }


operational_health = OperationalHealthService()
