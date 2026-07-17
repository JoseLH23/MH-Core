"""Predicciones operativas explicables y evaluables para EjiXhole."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import json

from mh_core.integrations.ejixhole_executive_dashboard import EjixholeExecutiveDashboardService


class EjixholePredictionsService:
    def __init__(self, path: str | Path | None = None) -> None:
        self.dashboard = EjixholeExecutiveDashboardService(path)
        self._initialize()

    def _initialize(self) -> None:
        with self.dashboard.processor.inbox._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ejixhole_prediction_snapshots (
                    business_date TEXT PRIMARY KEY,
                    horizon_start TEXT NOT NULL,
                    horizon_end TEXT NOT NULL,
                    expected_visitors INTEGER NOT NULL,
                    expected_revenue TEXT NOT NULL,
                    activity_level TEXT NOT NULL,
                    cancellation_risk TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    generated_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _level(value: int, medium: int, high: int) -> str:
        if value >= high:
            return "alto"
        if value >= medium:
            return "medio"
        return "bajo"

    def build(self, business_date: date | None = None) -> dict:
        target = business_date or datetime.now(timezone.utc).date()
        dashboard = self.dashboard.build(target, days=14)
        recent = dashboard["timeline"][-7:]
        reservations = sum(int(item["reservations"]) for item in recent)
        visits = sum(int(item["visits"]) for item in recent)
        revenue = sum(Decimal(str(item["net_revenue"])) for item in recent)
        upcoming_people = int(dashboard["kpis"]["upcoming_people_7_days"])
        upcoming_reservations = int(dashboard["kpis"]["upcoming_reservations_7_days"])
        cancellation_rate = float(dashboard["kpis"]["cancellation_rate"])

        expected_visitors = max(upcoming_people, round(visits))
        average_ticket = revenue / reservations if reservations else Decimal("0")
        expected_revenue = average_ticket * upcoming_reservations
        activity_level = self._level(expected_visitors, 6, 15)
        cancellation_risk = "alto" if cancellation_rate >= 25 else "medio" if cancellation_rate >= 10 else "bajo"
        confidence = "medium" if dashboard["processed_events"] >= 10 else "low"

        recommendations = []
        if activity_level == "alto":
            recommendations.append({"code": "STAFF_UP", "priority": "high", "message": "Prepara personal adicional, caja e insumos para los próximos 7 días."})
        elif activity_level == "medio":
            recommendations.append({"code": "CONFIRM_CAPACITY", "priority": "medium", "message": "Confirma capacidad, turnos y disponibilidad antes del fin de semana."})
        else:
            recommendations.append({"code": "MONITOR_DEMAND", "priority": "low", "message": "La demanda prevista es baja; monitorea nuevas reservaciones antes de ampliar recursos."})
        if cancellation_risk != "bajo":
            recommendations.append({"code": "REDUCE_CANCELLATIONS", "priority": "high", "message": "Refuerza confirmaciones y recordatorios previos para reducir cancelaciones."})

        generated_at = datetime.now(timezone.utc).isoformat()
        horizon_end = target + timedelta(days=7)
        with self.dashboard.processor.inbox._connect() as connection:
            connection.execute(
                """
                INSERT INTO ejixhole_prediction_snapshots (
                    business_date,horizon_start,horizon_end,expected_visitors,expected_revenue,
                    activity_level,cancellation_risk,confidence,generated_at
                ) VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(business_date) DO UPDATE SET
                    horizon_start=excluded.horizon_start,horizon_end=excluded.horizon_end,
                    expected_visitors=excluded.expected_visitors,expected_revenue=excluded.expected_revenue,
                    activity_level=excluded.activity_level,cancellation_risk=excluded.cancellation_risk,
                    confidence=excluded.confidence,generated_at=excluded.generated_at
                """,
                (target.isoformat(), target.isoformat(), horizon_end.isoformat(), expected_visitors,
                 f"{expected_revenue:.2f}", activity_level, cancellation_risk, confidence, generated_at),
            )

        return {
            "generated_at": generated_at,
            "business_date": target.isoformat(),
            "source": "ejixhole_events",
            "access": "read_only",
            "confidence": confidence,
            "predictions": {
                "expected_visitors_7_days": expected_visitors,
                "expected_revenue_7_days": f"{expected_revenue:.2f}",
                "activity_level": activity_level,
                "cancellation_risk": cancellation_risk,
                "upcoming_reservations_7_days": upcoming_reservations,
            },
            "explanations": [
                "La estimación usa eventos procesados, visitas recientes y reservaciones próximas.",
                "El riesgo de cancelación deriva de la tasa observada en el periodo reciente.",
                "Las predicciones son orientativas y no modifican precios, reservaciones ni pagos.",
            ],
            "recommendations": recommendations,
        }

    @staticmethod
    def _accuracy(expected: Decimal, actual: Decimal) -> float:
        if expected == 0 and actual == 0:
            return 100.0
        denominator = max(abs(expected), abs(actual), Decimal("1"))
        return round(max(Decimal("0"), Decimal("100") - abs(expected - actual) / denominator * 100), 1)

    def evaluation(self, as_of: date | None = None, limit: int = 12) -> dict:
        target = as_of or datetime.now(timezone.utc).date()
        self.dashboard.processor.process_pending()
        with self.dashboard.processor.inbox._connect() as connection:
            snapshots = connection.execute(
                """
                SELECT * FROM ejixhole_prediction_snapshots
                WHERE horizon_end <= ?
                ORDER BY business_date DESC
                LIMIT ?
                """,
                (target.isoformat(), limit),
            ).fetchall()
            evaluations = []
            for snapshot in snapshots:
                actual_visitors = connection.execute(
                    """
                    SELECT COALESCE(SUM(people),0)
                    FROM ejixhole_operational_reservations
                    WHERE status = 'completada' AND departure_date BETWEEN ? AND ?
                    """,
                    (snapshot["horizon_start"], snapshot["horizon_end"]),
                ).fetchone()[0]
                payment_rows = connection.execute(
                    """
                    SELECT event_type, payload_json FROM ejixhole_event_inbox
                    WHERE event_type = 'payment.recorded'
                      AND substr(occurred_at,1,10) BETWEEN ? AND ?
                    """,
                    (snapshot["horizon_start"], snapshot["horizon_end"]),
                ).fetchall()
                actual_revenue = Decimal("0")
                for row in payment_rows:
                    payload = json.loads(row["payload_json"])
                    amount = Decimal(str(payload.get("amount") or "0"))
                    actual_revenue += -amount if payload.get("payment_type") == "reembolso" else amount

                expected_visitors = Decimal(str(snapshot["expected_visitors"]))
                expected_revenue = Decimal(str(snapshot["expected_revenue"]))
                visitors_accuracy = self._accuracy(expected_visitors, Decimal(str(actual_visitors)))
                revenue_accuracy = self._accuracy(expected_revenue, actual_revenue)
                evaluations.append({
                    "business_date": snapshot["business_date"],
                    "horizon": {"start": snapshot["horizon_start"], "end": snapshot["horizon_end"]},
                    "expected": {"visitors": int(expected_visitors), "revenue": f"{expected_revenue:.2f}"},
                    "actual": {"visitors": int(actual_visitors or 0), "revenue": f"{actual_revenue:.2f}"},
                    "accuracy": {
                        "visitors_percent": visitors_accuracy,
                        "revenue_percent": revenue_accuracy,
                        "overall_percent": round((visitors_accuracy + revenue_accuracy) / 2, 1),
                    },
                    "original_confidence": snapshot["confidence"],
                })

        overall = round(sum(item["accuracy"]["overall_percent"] for item in evaluations) / len(evaluations), 1) if evaluations else None
        return {
            "as_of": target.isoformat(),
            "source": "prediction_snapshots_vs_actual_events",
            "access": "read_only",
            "evaluated_predictions": len(evaluations),
            "overall_accuracy_percent": overall,
            "evaluations": evaluations,
            "message": "Aún no hay predicciones maduras para evaluar." if not evaluations else None,
        }
