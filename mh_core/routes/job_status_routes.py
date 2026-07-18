"""Diagnóstico privado y de solo lectura de la cola durable."""
from fastapi import APIRouter, HTTPException, Query

from mh_core.jobs.durable_queue import DurableJobQueue, JobNotFoundError

router = APIRouter(prefix="/jobs", tags=["Durable jobs"])


@router.get("/stats")
def stats(queue: str | None = Query(default=None, max_length=80)):
    return DurableJobQueue().stats(queue=queue)


@router.get("")
def list_jobs(
    queue: str | None = Query(default=None, max_length=80),
    job_status: str | None = Query(default=None, alias="status", max_length=24),
    job_type: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return DurableJobQueue().list(
        queue=queue,
        status=job_status,
        job_type=job_type,
        limit=limit,
        offset=offset,
    )


@router.get("/{job_id}")
def get_job(job_id: str):
    try:
        return DurableJobQueue().get(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado.") from exc
