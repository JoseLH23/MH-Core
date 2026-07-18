"""Health checks públicos mínimos y observabilidad privada."""
from __future__ import annotations

from datetime import datetime, timezone
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from mh_core.core.runtime_metrics import runtime_metrics
from mh_core.integrations.ejixhole_state_store import ConfiguredEjixholeEventInbox
from mh_core.jobs.durable_queue import DurableJobQueue
from mh_core.persistence.database import get_engine

public_router = APIRouter(prefix="/health", tags=["Health"])
private_router = APIRouter(prefix="/observability", tags=["Observability"])


def dependency_checks() -> dict:
    checks = {}

    started = time.perf_counter()
    try:
        engine = get_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["persistence"] = {
            "status": "up",
            "backend": engine.dialect.name,
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
    except Exception:
        checks["persistence"] = {
            "status": "down",
            "backend": "unavailable",
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }

    started = time.perf_counter()
    try:
        inbox = ConfiguredEjixholeEventInbox()
        with inbox._connect() as connection:
            connection.execute("SELECT 1").fetchone()
        checks["ejixhole_state"] = {
            "status": "up",
            "backend": inbox.backend,
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
    except Exception:
        checks["ejixhole_state"] = {
            "status": "down",
            "backend": "unavailable",
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }

    try:
        job_stats = DurableJobQueue().stats()
        checks["durable_jobs"] = {
            "status": "up",
            "pending": job_stats.get("pending", 0) + job_stats.get("retry", 0),
            "dead_letter": job_stats.get("dead_letter", 0),
        }
    except Exception:
        checks["durable_jobs"] = {"status": "down", "pending": 0, "dead_letter": 0}

    return checks


@public_router.get("/live")
def liveness():
    return {"status": "alive", "service": "MH-Core", "version": "1.0"}


@public_router.get("/ready")
def readiness():
    checks = dependency_checks()
    ready = all(item["status"] == "up" for item in checks.values())
    content = {
        "status": "ready" if ready else "unavailable",
        "service": "MH-Core",
        "version": "1.0",
        "checks": checks,
    }
    return content if ready else JSONResponse(status_code=503, content=content)


@private_router.get("/summary")
def observability_summary():
    checks = dependency_checks()
    metrics = runtime_metrics.snapshot()
    healthy = all(item["status"] == "up" for item in checks.values()) and metrics["slo"]["status"] == "healthy"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "healthy" if healthy else "degraded",
        "dependencies": checks,
        "http": metrics,
    }
