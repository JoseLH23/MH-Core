from mh_core.integrations.ejixhole_calibrated_predictions import (
    EjixholeCalibratedPredictionsService,
)


def test_sin_historial_mantiene_confianza_baja():
    result = EjixholeCalibratedPredictionsService.calibrate([], processed_events=100)

    assert result["calibrated"] == "low"
    assert result["trend"] == "insufficient_data"
    assert result["warning"]


def test_precision_suficiente_calibra_confianza_media():
    result = EjixholeCalibratedPredictionsService.calibrate(
        [82.0, 78.0, 76.0], processed_events=100
    )

    assert result["calibrated"] == "medium"
    assert result["historical_accuracy_percent"] == 78.7
    assert result["warning"] is None


def test_historial_solido_y_en_mejora_calibra_confianza_alta():
    result = EjixholeCalibratedPredictionsService.calibrate(
        [94.0, 93.0, 92.0, 84.0, 83.0, 82.0], processed_events=100
    )

    assert result["calibrated"] == "high"
    assert result["trend"] == "improving"


def test_precision_baja_fuerza_advertencia():
    result = EjixholeCalibratedPredictionsService.calibrate(
        [55.0, 50.0, 45.0], processed_events=100
    )

    assert result["calibrated"] == "low"
    assert result["warning"]
