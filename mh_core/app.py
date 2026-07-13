from dotenv import load_dotenv

# Debe ir ANTES de cualquier import de mh_core/apps — varios módulos
# leen variables de entorno (YOUTUBE_API_KEY, GEMINI_API_KEY, etc.) en
# el momento en que se importan, no de forma perezosa. Antes de esto,
# el proyecto no cargaba .env en ningún lado — solo funcionaba si la
# variable ya estaba exportada en el sistema/PowerShell.
load_dotenv()

from fastapi import FastAPI
from mh_core.dashboard.dashboard_routes import router as dashboard_router
from mh_core.routes.research_routes import router as research_router
from mh_core.routes.core_routes import router as core_router
from mh_core.routes.automation_routes import router as automation_router
from mh_core.routes.agent_routes import router as agent_router
from apps.mindhigh.routes.mindhigh_routes import router as mindhigh_router
from apps.mindhigh.routes.orchestrator_routes import router as mindhigh_orchestrator_router
from mh_core.routes.notification_routes import router as notification_router


app = FastAPI(
    title="MindHigh Core",
    version="1.0"
)


app.include_router(research_router)
app.include_router(dashboard_router)
app.include_router(core_router)
app.include_router(automation_router)
app.include_router(agent_router)
app.include_router(mindhigh_router)
app.include_router(mindhigh_orchestrator_router)
app.include_router(notification_router)

@app.get("/")
def home():
    return {
        "message": "MH Core API v1.0 - Running"
    }


@app.get("/status")
def status():
    return {
        "status": "online",
        "project": "MindHigh Core",
        "version": "1.0"
    }