from fastapi import APIRouter, Depends, HTTPException

from mh_core.agents.agent_manager import AgentManager
from mh_core.utils.logger import logger
from mh_core.utils.rate_limit_dependency import limitar_generacion_ia

router = APIRouter(prefix="/agents", tags=["Agents"])

_manager = AgentManager()


@router.get("")
def list_agents():
    return {"agents": _manager.list_agents()}


@router.post("/{name}/run", dependencies=[Depends(limitar_generacion_ia)])
def run_agent(name: str, remember: bool = True):
    try:
        return _manager.run_agent(name, remember=remember)
    except ValueError as e:
        # Mensaje seguro de exponer: es "agente no encontrado", no un
        # detalle interno del sistema.
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # AL-07: la excepción real (puede incluir rutas, config,
        # detalles del proveedor) solo va al log, nunca al cliente.
        logger.warning(f"agents/{name}/run: falló ({e}).")
        raise HTTPException(status_code=502, detail="El agente falló al ejecutarse. Revisa el log del servidor.")
