"""Métricas de proceso sin payloads, cabeceras sensibles ni consultas."""
from __future__ import annotations

from collections import Counter, deque
from datetime import datetime, timezone
from threading import Lock
import time


class RuntimeMetrics:
    def __init__(self, sample_limit: int = 5000) -> None:
        self._lock = Lock()
        self._started_at = datetime.now(timezone.utc)
        self._started_monotonic = time.monotonic()
        self._requests = 0
        self._active = 0
        self._status: Counter[str] = Counter()
        self._durations: deque[int] = deque(maxlen=sample_limit)
        self._last_error: datetime | None = None

    def begin(self) -> None:
        with self._lock:
            self._active += 1

    def finish(self, status_code: int, duration_ms: int) -> None:
        group = f"{max(1, min(5, status_code // 100))}xx"
        with self._lock:
            self._active = max(0, self._active - 1)
            self._requests += 1
            self._status[group] += 1
            self._durations.append(max(0, duration_ms))
            if status_code >= 500:
                self._last_error = datetime.now(timezone.utc)

    @staticmethod
    def _percentile(values: list[int], fraction: float) -> int:
        if not values:
            return 0
        ordered = sorted(values)
        index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
        return ordered[index]

    def snapshot(self) -> dict:
        with self._lock:
            total = self._requests
            failures = self._status.get("5xx", 0)
            durations = list(self._durations)
            availability = ((total - failures) / total * 100) if total else 100.0
            error_rate = (failures / total * 100) if total else 0.0
            p95 = self._percentile(durations, 0.95)
            checks = {
                "availability": availability >= 99.5,
                "error_rate": error_rate <= 1.0,
                "latency_p95": p95 <= 1500,
            }
            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "started_at": self._started_at.isoformat(),
                "uptime_seconds": int(time.monotonic() - self._started_monotonic),
                "requests": {
                    "total": total,
                    "active": self._active,
                    "by_status_group": dict(self._status),
                    "server_errors": failures,
                },
                "latency_ms": {
                    "samples": len(durations),
                    "p50": self._percentile(durations, 0.50),
                    "p95": p95,
                    "max": max(durations) if durations else 0,
                },
                "slo": {
                    "status": "healthy" if all(checks.values()) else "degraded",
                    "availability_percent": round(availability, 3),
                    "error_rate_percent": round(error_rate, 3),
                    "targets": {
                        "availability_percent": 99.5,
                        "error_rate_percent": 1.0,
                        "latency_p95_ms": 1500,
                    },
                    "checks": checks,
                },
                "last_server_error_at": self._last_error.isoformat() if self._last_error else None,
            }


runtime_metrics = RuntimeMetrics()
