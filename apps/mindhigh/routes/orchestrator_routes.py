from fastapi import APIRouter, HTTPException

from apps.mindhigh.mindhigh_orchestrator import MindHighOrchestrator
from apps.mindhigh.models.content_piece import DURACIONES_VALIDAS

router = APIRouter(prefix="/mindhigh/runs", tags=["MindHigh Orchestrator"])

_orchestrator = MindHighOrchestrator()


@router.post("")
def ejecutar(remember: bool = True, duration_target: str = "short", style: str = "informativo"):
    if duration_target not in DURACIONES_VALIDAS:
        raise HTTPException(status_code=400, detail=f"duration_target debe ser uno de: {DURACIONES_VALIDAS}")
    run = _orchestrator.ejecutar(remember=remember, duration_target=duration_target, style=style)
    return run.model_dump()


@router.get("")
def listar(limit: int = 20):
    return {"runs": [r.model_dump() for r in _orchestrator.run_repository.listar(limit=limit)]}


@router.get("/{run_id}")
def obtener(run_id: str):
    run = _orchestrator.run_repository.obtener_por_id(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run no encontrado.")
    return run.model_dump()


@router.post("/{run_id}/resume")
def reanudar(run_id: str):
    try:
        run = _orchestrator.reanudar(run_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return run.model_dump()
