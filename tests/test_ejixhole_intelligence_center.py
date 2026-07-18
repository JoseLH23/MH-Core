from datetime import date

from mh_core.integrations.ejixhole_intelligence_center import EjixholeIntelligenceCenterService


def test_centro_entrega_resumen_alertas_y_contexto(tmp_path):
    service = EjixholeIntelligenceCenterService(tmp_path / "events.sqlite3")

    result = service.build(date(2026, 7, 17))

    assert result["daily_summary"]["notification"]["channel"] == "admin_panel"
    assert result["context_factors"]["model_version"] == "v2"
    assert result["context_factors"]["weather"]["status"] == "not_connected"
    assert isinstance(result["alerts"], list)


def test_recomendacion_guarda_decision_y_resultado(tmp_path):
    service = EjixholeIntelligenceCenterService(tmp_path / "events.sqlite3")
    business_date = "2026-07-17"

    accepted = service.decide(business_date, "MONITOR_DEMAND", "accepted")
    outcome = service.record_outcome(business_date, "MONITOR_DEMAND", "helped", "Se ajustó el turno")
    rebuilt = service.build(date(2026, 7, 17))

    assert accepted["decision"] == "accepted"
    assert outcome["outcome"] == "helped"
    recommendation = next(item for item in rebuilt["recommendations"] if item["code"] == "MONITOR_DEMAND")
    assert recommendation["decision"]["outcome"] == "helped"
