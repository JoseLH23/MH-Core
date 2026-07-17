from datetime import date

from mh_core.integrations.ejixhole_predictions import EjixholePredictionsService


def test_predicciones_vacias_son_seguras(tmp_path):
    result = EjixholePredictionsService(tmp_path / "events.sqlite3").build(date(2026, 7, 17))

    assert result["access"] == "read_only"
    assert result["confidence"] == "low"
    assert result["predictions"]["expected_visitors_7_days"] == 0
    assert result["predictions"]["expected_revenue_7_days"] == "0.00"
    assert result["predictions"]["activity_level"] == "bajo"
    assert result["predictions"]["cancellation_risk"] == "bajo"
    assert result["recommendations"]
