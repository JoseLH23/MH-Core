from fastapi import APIRouter
from mh_core.services.research_service import ResearchService

router = APIRouter(
    prefix="/research",
    tags=["Research"]
)


@router.get("")
def research():
    return ResearchService.research()


@router.get("/ranking")
def research_ranking():
    return ResearchService.ranking()


@router.get("/decision")
def research_decision():
    return ResearchService.decision()

@router.get("/learning")
def research_learning():
    return ResearchService.learning()

@router.get("/prediction")
def research_prediction():
    return ResearchService.prediction()

@router.get("/brain")
def research_brain():
    return ResearchService.brain()