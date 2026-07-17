"""Calibra la confianza de las predicciones con resultados maduros."""
from __future__ import annotations

from datetime import date

from mh_core.integrations.ejixhole_predictions import EjixholePredictionsService


class EjixholeCalibratedPredictionsService:
    def __init__(self, path=None) -> None:
        self.predictions = EjixholePredictionsService(path)

    @staticmethod
    def calibrate(accuracies: list[float], processed_events: int) -> dict:
        base = "medium" if processed_events >= 10 else "low"
        if not accuracies:
            return {
                "base": base,
                "calibrated": "low",
                "evaluated_predictions": 0,
                "historical_accuracy_percent": None,
                "trend": "insufficient_data",
                "warning": "Aún no hay predicciones maduras suficientes para validar la confianza.",
            }

        average = round(sum(accuracies) / len(accuracies), 1)
        if len(accuracies) < 3:
            calibrated = "low"
            warning = "La confianza permanece baja hasta contar con al menos 3 evaluaciones maduras."
        elif average >= 85 and len(accuracies) >= 6:
            calibrated = "high"
            warning = None
        elif average >= 70:
            calibrated = "medium"
            warning = None
        else:
            calibrated = "low"
            warning = "La precisión histórica todavía es insuficiente; interpreta la predicción con cautela."

        trend = "stable"
        if len(accuracies) >= 6:
            recent = sum(accuracies[:3]) / 3
            previous = sum(accuracies[3:6]) / 3
            if recent - previous >= 5:
                trend = "improving"
            elif previous - recent >= 5:
                trend = "declining"

        return {
            "base": base,
            "calibrated": calibrated,
            "evaluated_predictions": len(accuracies),
            "historical_accuracy_percent": average,
            "trend": trend,
            "warning": warning,
        }

    def build(self, business_date: date | None = None) -> dict:
        result = self.predictions.build(business_date)
        target = business_date or date.fromisoformat(result["business_date"])
        evaluation = self.predictions.evaluation(as_of=target, limit=12)
        accuracies = [float(item["accuracy"]["overall_percent"]) for item in evaluation["evaluations"]]
        processed_events = self.predictions.dashboard.processor.summary()["processed_events"]
        details = self.calibrate(accuracies, processed_events)
        result["confidence"] = details["calibrated"]
        result["confidence_details"] = details
        result["explanations"].insert(
            -1,
            "La confianza se calibra con la precisión histórica cuando existen evaluaciones maduras.",
        )
        with self.predictions.dashboard.processor.inbox._connect() as connection:
            connection.execute(
                "UPDATE ejixhole_prediction_snapshots SET confidence = ? WHERE business_date = ?",
                (details["calibrated"], result["business_date"]),
            )
        return result
