from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.mindhigh.models.marketing_campaign import CampaignBrief, MarketingCampaign
from apps.mindhigh.services.marketing_campaign_service import (
    MarketingCampaignService,
    MissingMarketingEvidenceError,
    UnsafeMarketingClaimError,
)
from mh_core.services.governed_knowledge_service import (
    GovernedKnowledgeService,
    KnowledgeUnavailableError,
)


router = APIRouter(prefix="/mindhigh/marketing", tags=["MindHigh Marketing"])
knowledge_service = GovernedKnowledgeService()


@router.get("/status")
def marketing_status() -> dict:
    """Estado mínimo para clientes autorizados a preparar campañas."""
    status = knowledge_service.status()
    return {
        "configured": status["configured"],
        "available": status["available"],
        "knowledge_version": status["knowledge_version"],
        "documents": status["documents"],
    }


@router.post("/campaigns/draft", response_model=MarketingCampaign)
def create_campaign_draft(brief: CampaignBrief) -> MarketingCampaign:
    if brief.approved_dynamic_facts:
        raise HTTPException(
            status_code=422,
            detail=(
                "Los datos dinámicos deben provenir de una fuente operacional autorizada; "
                "esta ruta todavía no acepta hechos declarados manualmente."
            ),
        )

    try:
        bundle = knowledge_service.load_bundle()
        return MarketingCampaignService(
            bundle,
            require_citations=True,
        ).generate(brief)
    except (KnowledgeUnavailableError, KeyError, MissingMarketingEvidenceError):
        raise HTTPException(
            status_code=503,
            detail="El conocimiento aprobado necesario para la campaña no está disponible.",
        )
    except UnsafeMarketingClaimError:
        raise HTTPException(
            status_code=422,
            detail="La campaña contiene un dato dinámico no autorizado.",
        )
