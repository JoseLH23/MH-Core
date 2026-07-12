from fastapi import APIRouter, HTTPException

from mh_core.agents.agent_manager import AgentManager

router = APIRouter(prefix="/agents", tags=["Agents"])

_manager = AgentManager()


@router.get("")
def list_agents():
    return {"agents": _manager.list_agents()}


@router.post("/{name}/run")
def run_agent(name: str, remember: bool = True):
    try:
        return _manager.run_agent(name, remember=remember)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"El agente falló al ejecutarse: {e}")
