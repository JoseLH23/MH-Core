"""Worker explícito para procesar la cola durable sin efectos al importar."""
from __future__ import annotations

import argparse
import os
import socket
import time
from typing import Any, Callable

from mh_core.jobs.durable_queue import DurableJobQueue, JobSnapshot
from mh_core.utils.logger import logger

JobHandler = Callable[[dict[str, Any]], dict[str, Any]]


def run_automation_once(payload: dict[str, Any]) -> dict[str, Any]:
    if payload:
        raise ValueError("automation.run_once no acepta payload en v1")
    from mh_core.engines.automation_engine import AutomationEngine

    result = AutomationEngine().run_once(remember=True)
    return {
        "completed": True,
        "brain_report": result.get("brain_report") if isinstance(result, dict) else None,
    }


DEFAULT_HANDLERS: dict[str, JobHandler] = {
    "automation.run_once": run_automation_once,
}


class DurableWorker:
    def __init__(
        self,
        queue: DurableJobQueue | None = None,
        *,
        worker_id: str | None = None,
        queue_name: str = "default",
        lease_seconds: int = 300,
        handlers: dict[str, JobHandler] | None = None,
    ) -> None:
        default_id = f"{socket.gethostname()}-{os.getpid()}"
        self.queue = queue or DurableJobQueue(default_queue=queue_name)
        self.worker_id = worker_id or default_id
        self.queue_name = queue_name
        self.lease_seconds = lease_seconds
        self.handlers = dict(DEFAULT_HANDLERS if handlers is None else handlers)

    def run_once(self) -> JobSnapshot | None:
        job = self.queue.claim(
            self.worker_id,
            queue=self.queue_name,
            lease_seconds=self.lease_seconds,
        )
        if job is None:
            return None

        handler = self.handlers.get(job.job_type)
        if handler is None:
            return self.queue.fail(
                job.id,
                self.worker_id,
                f"No existe un handler registrado para {job.job_type}.",
            )

        try:
            result = handler(dict(job.payload))
            if not isinstance(result, dict):
                raise TypeError("El handler debe devolver un diccionario JSON.")
            return self.queue.complete(job.id, self.worker_id, result)
        except Exception as exc:
            logger.warning("Job durable %s falló: %s", job.id, type(exc).__name__)
            return self.queue.fail(job.id, self.worker_id, exc)

    def run_forever(self, *, poll_seconds: float = 2.0) -> None:
        if not 0.1 <= poll_seconds <= 60:
            raise ValueError("poll_seconds debe estar entre 0.1 y 60")
        logger.info("Worker durable iniciado worker_id=%s queue=%s", self.worker_id, self.queue_name)
        while True:
            processed = self.run_once()
            if processed is None:
                time.sleep(poll_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Worker durable de MH-Core")
    parser.add_argument("--once", action="store_true", help="Procesa como máximo un trabajo y termina")
    parser.add_argument("--queue", default=os.getenv("MH_JOB_QUEUE", "default"))
    parser.add_argument("--worker-id", default=os.getenv("MH_JOB_WORKER_ID"))
    parser.add_argument("--lease-seconds", type=int, default=int(os.getenv("MH_JOB_LEASE_SECONDS", "300")))
    parser.add_argument("--poll-seconds", type=float, default=float(os.getenv("MH_JOB_POLL_SECONDS", "2")))
    args = parser.parse_args()

    worker = DurableWorker(
        worker_id=args.worker_id,
        queue_name=args.queue,
        lease_seconds=args.lease_seconds,
    )
    if args.once:
        worker.run_once()
    else:
        worker.run_forever(poll_seconds=args.poll_seconds)


if __name__ == "__main__":
    main()
