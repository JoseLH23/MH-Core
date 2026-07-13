from mh_core.dashboard.dashboard_service import DashboardService


def test_overview_no_tiene_modulos_reales_marcados_como_pending():
    """Regresión directa del hallazgo real: antes decía PENDING para
    prediction_engine y mh_brain, que ya son reales."""
    data = DashboardService.overview()

    assert data["modules"]["prediction_engine"] == "READY"
    assert data["modules"]["mh_brain"] == "READY"
    assert data["modules"]["memory_engine"] == "READY"
    assert data["modules"]["orchestrator"] == "READY"
    assert data["modules"]["automation_engine"] == "READY"
    assert data["modules"]["agents"] == "READY"


def test_overview_no_inventa_un_porcentaje_de_avance():
    """El "overall_progress": "60%" no tenía ninguna fórmula real
    detrás — se quitó en vez de inventar otro número."""
    data = DashboardService.overview()
    assert "overall_progress" not in data


def test_overview_incluye_resumen_de_aprendizaje_real():
    data = DashboardService.overview()
    assert "learning_summary" in data
    assert "total_memories" in data["learning_summary"]


def test_system_status_incluye_todos_los_engines_reales():
    data = DashboardService.system_status()

    for motor in [
        "research", "scoring", "ranking", "patterns", "decision",
        "prediction", "mh_brain", "learning", "memory", "orchestrator",
        "automation", "agents",
    ]:
        assert data["engines"][motor] == "OK", f"falta o está mal el engine: {motor}"
