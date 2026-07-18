from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from sqlalchemy import update

from mh_core.jobs.durable_queue import DurableJobQueue, JobConflictError, utcnow
from mh_core.jobs.worker import DurableWorker
from mh_core.persistence.database import create_engine_for_url
from mh_core.persistence.models import DurableJobRecord


def queue_for(tmp_path):
    engine = create_engine_for_url(f"sqlite+pysqlite:///{(tmp_path / 'jobs.sqlite3').as_posix()}")
    return DurableJobQueue(engine)


def test_enqueue_idempotente_reutiliza_el_mismo_job(tmp_path):
    queue = queue_for(tmp_path)
    first = queue.enqueue("automation.run_once", {}, idempotency_key="daily-2026-07-18")
    second = queue.enqueue("automation.run_once", {}, idempotency_key="daily-2026-07-18")
    assert first.duplicate is False
    assert second.duplicate is True
    assert first.job.id == second.job.id


def test_idempotencia_rechaza_otro_payload(tmp_path):
    queue = queue_for(tmp_path)
    queue.enqueue("custom.test", {"value": 1}, idempotency_key="same-key")
    with pytest.raises(JobConflictError):
        queue.enqueue("custom.test", {"value": 2}, idempotency_key="same-key")


def test_dos_workers_no_reclaman_el_mismo_job(tmp_path):
    queue = queue_for(tmp_path)
    expected = queue.enqueue("custom.test", {}).job.id

    def claim(worker):
        result = queue.claim(worker)
        return result.id if result else None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, ["worker-a", "worker-b"]))
    assert results.count(expected) == 1
    assert results.count(None) == 1


def test_fallo_terminal_va_a_dead_letter_y_se_puede_reintentar(tmp_path):
    queue = queue_for(tmp_path)
    job = queue.enqueue("custom.test", {}, max_attempts=1).job
    claimed = queue.claim("worker-a")
    assert claimed and claimed.id == job.id
    failed = queue.fail(job.id, "worker-a", RuntimeError("fallo controlado"))
    assert failed.status == "dead_letter"
    retried = queue.retry_dead_letter(job.id)
    assert retried.status == "pending"
    assert retried.attempts == 0


def test_recupera_un_lease_abandonado(tmp_path):
    queue = queue_for(tmp_path)
    job = queue.enqueue("custom.test", {}).job
    queue.claim("worker-a")
    with queue.sessions() as session:
        session.execute(
            update(DurableJobRecord)
            .where(DurableJobRecord.id == job.id)
            .values(lock_expires_at=utcnow() - timedelta(seconds=1))
        )
        session.commit()
    assert queue.recover_abandoned() == 1
    assert queue.get(job.id).status == "retry"


def test_worker_completa_un_handler_registrado(tmp_path):
    queue = queue_for(tmp_path)
    job = queue.enqueue("custom.test", {"value": 7}).job
    worker = DurableWorker(
        queue,
        worker_id="worker-test",
        handlers={"custom.test": lambda payload: {"result": payload["value"] * 2}},
    )
    completed = worker.run_once()
    assert completed and completed.id == job.id
    assert completed.status == "succeeded"
    assert completed.result == {"result": 14}
