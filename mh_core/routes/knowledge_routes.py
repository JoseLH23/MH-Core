from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from mh_core.services.governed_knowledge_service import (
    GovernedKnowledgeService,
    KnowledgeUnavailableError,
)


router = APIRouter(prefix="/knowledge", tags=["knowledge"])
service = GovernedKnowledgeService()


@router.get("/status")
def knowledge_status():
    return service.status()


@router.get("/search")
def knowledge_search(
    q: str = Query(min_length=2, max_length=200),
    category: str | None = Query(default=None, min_length=1, max_length=50),
    limit: int = Query(default=5, ge=1, le=20),
):
    try:
        return service.search(q, category=category, limit=limit)
    except KnowledgeUnavailableError:
        raise HTTPException(
            status_code=503,
            detail="El conocimiento aprobado no está disponible.",
        )
