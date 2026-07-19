"""Salud operativa de MH-Core sin exponer secretos ni datos de negocio."""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import Lock
import time
from typing import Callable

from sqlalchemy import text

from mh_core.integrations.ejixhole_state_store import ConfiguredEjixholeEventInbox
from mh_core.jobs.durable_queue import DurableJobQueue
from mh_core.persistence.database import get_engine


class OperationalHealthService:
    def __init__(
        self,
        sample_limit: int = 1440,
        *,
        expected_interval_seconds: int = 60,
        max_gap_seconds: int = 180,
        monotonic: Callable[[], float] | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._lock = Lock()
        self._segments: deque[dict] = deque(maxlen=sample_limit)
        self._expected_interval_seconds = expected_interval_seconds
        self._max_gap_seconds = max_gap_seconds
        self._monotonic = monotonic or time.monotonic
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._started_at = self._now()
        self._last_observation_monotonic: float | None = None
        self._last_sample: dict | None = None

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

    def _record_interval(self, current_sample: dict) -> None:
        observed_at = self._monotonic()
        with self._lock:
            if self._last_observation_monotonic is not None and self._last_sample is not None:
                duration = max(0.0, observed_at - self._last_observation_monotonic)
                if duration > 0:
                    complete = duration <= self._max_gap_seconds
                    healthy = self._last_sample["healthy"] if complete else None
                    segment = {
                        "healthy": healthy,
                        "complete": complete,
                        "duration_seconds": duration,
                    }
                    if (
                        self._segments
                        and self._segments[-1]["healthy"] == healthy
                        and self._segments[-1]["complete"] == complete
                    ):
                        self._segments[-1]["duration_seconds"] += duration
                    else:
                        self._segments.append(segment)
            self._last_observation_monotonic = observed_at
            self._last_sample = current_sample

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
            "timestamp": self._now().isoformat(),
            "healthy": healthy,
            "checks": checks,
        }
        self._record_interval(sample)
        return sample

    def summary(self) -> dict:
        current = self.sample()
        with self._lock:
            segments = [dict(segment) for segment in self._segments]

        known_seconds = sum(
            segment["duration_seconds"] for segment in segments if segment["complete"]
        )
        healthy_seconds = sum(
            segment["duration_seconds"]
            for segment in segments
            if segment["complete"] and segment["healthy"] is True
        )
        unknown_seconds = sum(
            segment["duration_seconds"] for segment in segments if not segment["complete"]
        )
        availability = (
            healthy_seconds / known_seconds * 100 if known_seconds > 0 else None
        )
        target = 99.5
        measurement_complete = (
            known_seconds >= self._expected_interval_seconds and unknown_seconds == 0
        )
        availability_check = (
            availability >= target
            if measurement_complete and availability is not None
            else None
        )

        jobs_check = current["checks"]["durable_jobs"]
        jobs_available = jobs_check["status"] == "up"
        dead_letters = jobs_check.get("dead_letter") if jobs_available else None
        dead_letter_check = dead_letters == 0 if jobs_available else None
        dependencies_check = current["healthy"]

        checks = {
            "availability": availability_check,
            "dependencies": dependencies_check,
            "dead_letter": dead_letter_check,
        }
        known_failures = any(value is False for value in checks.values())
        unknown_checks = any(value is None for value in checks.values())
        slo_status = "degraded" if known_failures else "unknown" if unknown_checks else "healthy"

        return {
            "generated_at": self._now().isoformat(),
            "started_at": self._started_at.isoformat(),
            "status": "healthy" if dependencies_check and dead_letter_check is True else "degraded",
            "current": current,
            "slo": {
                "status": slo_status,
                "measurement": "time_weighted_probe_intervals",
                "availability_percent": round(availability, 3) if availability is not None else None,
                "target_percent": target,
                "known_seconds": round(known_seconds, 3),
                "healthy_seconds": round(healthy_seconds, 3),
                "unknown_seconds": round(unknown_seconds, 3),
                "expected_interval_seconds": self._expected_interval_seconds,
                "max_gap_seconds": self._max_gap_seconds,
                "measurement_complete": measurement_complete,
                "segments": len(segments),
                "checks": checks,
            },
        }


operational_health = OperationalHealthService()
