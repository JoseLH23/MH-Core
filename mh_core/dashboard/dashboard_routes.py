from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from mh_core.dashboard.dashboard_service import DashboardService

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)

_PANEL_HTML = Path(__file__).parent / "static" / "panel.html"


@router.get("/panel", response_class=HTMLResponse)
def dashboard_panel():
    """Panel visual real — consume la API en vivo desde el navegador,
    no trae ningún dato incrustado aquí."""
    return _PANEL_HTML.read_text(encoding="utf-8")


@router.get("")
def dashboard_overview():
    return DashboardService.overview()


@router.get("/system")
def dashboard_system():
    return DashboardService.system_status()


@router.get("/learning")
def dashboard_learning():
    return DashboardService.learning()

@router.get("/statistics")
def dashboard_statistics():
    return DashboardService.statistics()

@router.get("/prediction")
def dashboard_prediction():
    return DashboardService.prediction()

@router.get("/plugins")
def dashboard_plugins():
    return DashboardService.plugins()

@router.get("/knowledge")
def dashboard_knowledge():
    return DashboardService.knowledge()