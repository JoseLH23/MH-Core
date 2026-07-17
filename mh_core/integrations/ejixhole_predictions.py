"""Predicciones operativas explicables para EjiXhole."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from mh_core.integrations.ejixhole_executive_dashboard import EjixholeExecutiveDashboardService


class EjixholePredictionsService:
    def __init__(self, path: str | Path | None = None) -> None:
        self.dashboard = EjixholeExecutiveDashboardService(path)

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

        recommendations = []
        if activity_level == "alto":
            recommendations.append({"code": "STAFF_UP", "priority": "high", "message": "Prepara personal adicional, caja e insumos para los próximos 7 días."})
        elif activity_level == "medio":
            recommendations.append({"code": "CONFIRM_CAPACITY", "priority": "medium", "message": "Confirma capacidad, turnos y disponibilidad antes del fin de semana."})
        else:
            recommendations.append({"code": "MONITOR_DEMAND", "priority": "low", "message": "La demanda prevista es baja; monitorea nuevas reservaciones antes de ampliar recursos."})
        if cancellation_risk != "bajo":
            recommendations.append({"code": "REDUCE_CANCELLATIONS", "priority": "high", "message": "Refuerza confirmaciones y recordatorios previos para reducir cancelaciones."})

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "business_date": target.isoformat(),
            "source": "ejixhole_events",
            "access": "read_only",
            "confidence": "medium" if dashboard["processed_events"] >= 10 else "low",
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
