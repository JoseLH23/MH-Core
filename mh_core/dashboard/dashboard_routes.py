from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from mh_core.dashboard.dashboard_service import DashboardService

# CR-04 (auditoría de seguridad): el HTML del panel necesita cargar
# SIN X-API-Key (un navegador no puede mandar headers custom al
# navegar directo a una URL) — por eso vive en un router aparte, sin
# la dependencia de auth que sí protege todos los DATOS que ese mismo
# panel consume después vía fetch() con la key que el usuario
# introduce (ver panel.html). El HTML en sí no expone ningún dato.
router_publico = APIRouter(prefix="/dashboard", tags=["Dashboard"])

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)

_PANEL_HTML = Path(__file__).parent / "static" / "panel.html"


@router_publico.get("/panel", response_class=HTMLResponse)
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