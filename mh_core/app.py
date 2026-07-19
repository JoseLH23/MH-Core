from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI
from mh_core.core.auth import requerir_scopes
from mh_core.dashboard.dashboard_routes import router as dashboard_router, router_publico as dashboard_router_publico
from mh_core.routes.research_routes import router as research_router
from mh_core.routes.core_routes import router as core_router
from mh_core.routes.automation_routes import router as automation_router
from mh_core.routes.agent_routes import router as agent_router
from apps.mindhigh.routes.mindhigh_routes import router as mindhigh_router
from apps.mindhigh.routes.orchestrator_routes import router as mindhigh_orchestrator_router
from apps.mindhigh.routes.video_routes import router as video_router
from apps.mindhigh.routes.mindhigh_agent_routes import router as mindhigh_agent_router
from mh_core.routes.notification_routes import router as notification_router
from mh_core.routes.ejixhole_routes import router as ejixhole_router
from mh_core.routes.ejixhole_event_routes import router as ejixhole_event_router
from mh_core.routes.ejixhole_operations_routes import router as ejixhole_operations_router
from mh_core.routes.ejixhole_daily_routes import router as ejixhole_daily_router
from mh_core.routes.ejixhole_executive_routes import router as ejixhole_executive_router
from mh_core.routes.ejixhole_predictions_routes import router as ejixhole_predictions_router

app = FastAPI(title="MindHigh Core", version="1.0")
_core_read = [Depends(requerir_scopes("core.read"))]
_mindhigh_execute = [Depends(requerir_scopes("mindhigh.execute"))]
_ejixhole_read = [Depends(requerir_scopes("ejixhole.read"))]

app.include_router(dashboard_router_publico)
app.include_router(ejixhole_event_router)
app.include_router(research_router, dependencies=_mindhigh_execute)
app.include_router(dashboard_router, dependencies=_core_read)
app.include_router(core_router, dependencies=_core_read)
app.include_router(automation_router, dependencies=_mindhigh_execute)
app.include_router(agent_router, dependencies=_mindhigh_execute)
app.include_router(mindhigh_router, dependencies=_mindhigh_execute)
app.include_router(mindhigh_orchestrator_router, dependencies=_mindhigh_execute)
app.include_router(video_router, dependencies=_mindhigh_execute)
app.include_router(mindhigh_agent_router, dependencies=_mindhigh_execute)
app.include_router(notification_router, dependencies=_core_read)
app.include_router(ejixhole_router, dependencies=_ejixhole_read)
app.include_router(ejixhole_operations_router, dependencies=_ejixhole_read)
app.include_router(ejixhole_daily_router, dependencies=_ejixhole_read)
app.include_router(ejixhole_executive_router, dependencies=_ejixhole_read)
app.include_router(ejixhole_predictions_router)


@app.get("/")
def home():
    return {"message": "MH Core API v1.0 - Running"}


@app.get("/status", dependencies=_core_read)
def status():
    return {"status": "online", "project": "MindHigh Core", "version": "1.0"}
