from fastapi import APIRouter
from mh_core.dashboard.dashboard_service import DashboardService

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


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