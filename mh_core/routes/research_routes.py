"""
AL-09 (auditoría de seguridad 13/jul/2026): estas rutas ejecutaban
investigación real (llamadas a YouTube, y algunas hasta escriben en
Memory Engine) detrás de un GET — un prefetcher de navegador, un bot,
una caché o un reintento automático puede disparar un GET sin que
nadie lo pida de verdad, gastando cuota real. Los GET nunca deben
tener efectos secundarios (RFC 9110). Se cambian a POST.
"""
from fastapi import APIRouter, Depends
from mh_core.services.research_service import ResearchService
from mh_core.utils.rate_limit_dependency import limitar_generacion_ia

router = APIRouter(
    prefix="/research",
    tags=["Research"],
    dependencies=[Depends(limitar_generacion_ia)],
)


@router.post("")
def research():
    return ResearchService.research()


@router.post("/ranking")
def research_ranking():
    return ResearchService.ranking()


@router.post("/decision")
def research_decision():
    return ResearchService.decision()

@router.get("/learning")
def research_learning():
    # Este SÍ se queda como GET a propósito: solo lee el resumen ya
    # guardado (LearningEngine.summarize_learning()), no dispara
    # ninguna investigación nueva ni gasta cuota externa.
    return ResearchService.learning()

@router.post("/prediction")
def research_prediction():
    return ResearchService.prediction()

@router.post("/brain")
def research_brain():
    return ResearchService.brain()
