from mh_core.integrations.ejixhole_intelligence_center import EjixholeIntelligenceCenterService


def test_historial_resume_decisiones_y_resultados(tmp_path):
    service = EjixholeIntelligenceCenterService(tmp_path / "events.sqlite3")

    service.decide("2026-07-17", "STAFF", "accepted")
    service.record_outcome("2026-07-17", "STAFF", "helped", "Se reforzó el turno")
    service.decide("2026-07-18", "SUPPLIES", "accepted")
    service.decide("2026-07-18", "CASH", "dismissed")

    result = service.history()

    assert result["summary"]["total_decisions"] == 3
    assert result["summary"]["accepted"] == 2
    assert result["summary"]["dismissed"] == 1
    assert result["summary"]["evaluated"] == 1
    assert result["summary"]["pending_evaluation"] == 1
    assert result["summary"]["helped_percent"] == 100.0
    assert result["items"][0]["business_date"] == "2026-07-18"
