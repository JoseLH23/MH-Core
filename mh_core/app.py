from fastapi import FastAPI
from mh_core.dashboard.dashboard_routes import router as dashboard_router
from mh_core.routes.research_routes import router as research_router
from mh_core.routes.core_routes import router as core_router
from mh_core.routes.automation_routes import router as automation_router


app = FastAPI(
    title="MindHigh Core",
    version="1.0"
)


app.include_router(research_router)
app.include_router(dashboard_router)
app.include_router(core_router)
app.include_router(automation_router)

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