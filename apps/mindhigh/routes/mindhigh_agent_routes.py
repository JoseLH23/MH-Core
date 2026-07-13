from fastapi import APIRouter, Depends, HTTPException

from apps.mindhigh.agents.mindhigh_agent_manager import crear_mindhigh_agent_manager
from mh_core.utils.rate_limit_dependency import limitar_generacion_ia

router = APIRouter(prefix="/mindhigh/agents", tags=["MindHigh Agents"])

_manager = crear_mindhigh_agent_manager()


@router.get("")
def listar_agentes():
    return {"agents": _manager.list_agents()}


@router.post("/{name}/run", dependencies=[Depends(limitar_generacion_ia)])
def ejecutar_agente(name: str, content_id: str | None = None, remember: bool = True, duration_target: str = "short", style: str = "informativo"):
    kwargs = {"remember": remember, "duration_target": duration_target, "style": style}
    if content_id:
        kwargs["content_id"] = content_id
    try:
        return _manager.run_agent(name, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"El agente falló al ejecutarse: {e}")
