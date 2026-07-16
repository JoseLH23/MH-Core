from dotenv import load_dotenv

# Debe ir ANTES de cualquier import de mh_core/apps — varios módulos
# leen variables de entorno (YOUTUBE_API_KEY, GEMINI_API_KEY, etc.) en
# el momento en que se importan, no de forma perezosa. Antes de esto,
# el proyecto no cargaba .env en ningún lado — solo funcionaba si la
# variable ya estaba exportada en el sistema/PowerShell.
load_dotenv()

from fastapi import Depends, FastAPI
from mh_core.core.auth import verificar_api_key
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


app = FastAPI(
    title="MindHigh Core",
    version="1.0"
)

# CR-04 (auditoría de seguridad 13/jul/2026): deny-by-default real —
# TODOS los routers requieren X-API-Key (ver mh_core/core/auth.py).
# Se aplica aquí, centralizado, en vez de en cada archivo de rutas por
# separado — un solo lugar deja claro qué está protegido.
_auth = [Depends(verificar_api_key)]

app.include_router(dashboard_router_publico)  # solo el HTML del panel, sin X-API-Key

# Webhook máquina-a-máquina: no usa la API key humana. Verifica una firma HMAC,
# timestamp corto y deduplicación durable antes de aceptar cualquier evento.
app.include_router(ejixhole_event_router)

app.include_router(research_router, dependencies=_auth)
app.include_router(dashboard_router, dependencies=_auth)
app.include_router(core_router, dependencies=_auth)
app.include_router(automation_router, dependencies=_auth)
app.include_router(agent_router, dependencies=_auth)
app.include_router(mindhigh_router, dependencies=_auth)
app.include_router(mindhigh_orchestrator_router, dependencies=_auth)
app.include_router(video_router, dependencies=_auth)
app.include_router(mindhigh_agent_router, dependencies=_auth)
app.include_router(notification_router, dependencies=_auth)
app.include_router(ejixhole_router, dependencies=_auth)

# "/" se deja SIN proteger a propósito — es el liveness check mínimo
# que usan servicios de monitoreo/infra (Render, uptime checks) y no
# revela nada sensible. Todo lo demás, incluido /status, sí requiere
# X-API-Key.
@app.get("/")
def home():
    return {
        "message": "MH Core API v1.0 - Running"
    }


@app.get("/status", dependencies=_auth)
def status():
    return {
        "status": "online",
        "project": "MindHigh Core",
        "version": "1.0"
    }
