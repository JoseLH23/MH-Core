import os
from uuid import uuid4

import pytest

from mh_core.database.sql_memory_repository import SqlMemoryRepository
from mh_core.jobs.durable_queue import DurableJobQueue
from mh_core.models.memory import Memory
from mh_core.persistence.database import create_engine_for_url


@pytest.mark.skipif(not os.getenv("MH_TEST_POSTGRES_URL"), reason="PostgreSQL desechable no configurado")
def test_postgres_soporta_job_y_memoria_durables():
    engine = create_engine_for_url(os.environ["MH_TEST_POSTGRES_URL"])
    queue = DurableJobQueue(engine, default_queue="ci")
    key = f"ci-{uuid4()}"
    queued = queue.enqueue("ci.smoke", {"ok": True}, idempotency_key=key, max_attempts=2)
    claimed = queue.claim("ci-worker", queue="ci")
    assert claimed and claimed.id == queued.job.id
    completed = queue.complete(claimed.id, "ci-worker", {"stored": True})
    assert completed.status == "succeeded"

    memories = SqlMemoryRepository(engine)
    topic = f"ci-{uuid4()}"
    saved = memories.guardar(Memory(topic=topic, decision="TEST", best_url=topic))
    assert memories.buscar_por_tema(topic)[0].id == saved.id
