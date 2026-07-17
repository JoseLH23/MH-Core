from datetime import date

from mh_core.integrations.ejixhole_predictions import EjixholePredictionsService


def test_predicciones_vacias_son_seguras(tmp_path):
    service = EjixholePredictionsService(tmp_path / "events.sqlite3")
    result = service.build(date(2026, 7, 17))

    assert result["access"] == "read_only"
    assert result["confidence"] == "low"
    assert result["predictions"]["expected_visitors_7_days"] == 0
    assert result["predictions"]["expected_revenue_7_days"] == "0.00"
    assert result["predictions"]["activity_level"] == "bajo"
    assert result["predictions"]["cancellation_risk"] == "bajo"
    assert result["recommendations"]


def test_prediccion_se_guarda_y_se_evalua_al_madurar(tmp_path):
    service = EjixholePredictionsService(tmp_path / "events.sqlite3")
    service.build(date(2026, 7, 1))

    early = service.evaluation(as_of=date(2026, 7, 7))
    mature = service.evaluation(as_of=date(2026, 7, 8))

    assert early["evaluated_predictions"] == 0
    assert mature["evaluated_predictions"] == 1
    assert mature["overall_accuracy_percent"] == 100.0
    assert mature["evaluations"][0]["business_date"] == "2026-07-01"
    assert mature["evaluations"][0]["actual"] == {"visitors": 0, "revenue": "0.00"}


def test_recalcular_misma_fecha_actualiza_snapshot_sin_duplicar(tmp_path):
    service = EjixholePredictionsService(tmp_path / "events.sqlite3")
    service.build(date(2026, 7, 1))
    service.build(date(2026, 7, 1))

    with service.dashboard.processor.inbox._connect() as connection:
        total = connection.execute("SELECT COUNT(*) FROM ejixhole_prediction_snapshots").fetchone()[0]

    assert total == 1
