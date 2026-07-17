"""Dashboard ejecutivo privado construido únicamente con eventos de EjiXhole."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import json

from mh_core.integrations.ejixhole_event_processor import EjixholeEventProcessor


class EjixholeExecutiveDashboardService:
    def __init__(self, path: str | Path | None = None) -> None:
        self.processor = EjixholeEventProcessor(path)

    @staticmethod
    def _money(value: Decimal) -> str:
        return f"{value:.2f}"

    @staticmethod
    def _decimal(value: object) -> Decimal:
        return Decimal(str(value or "0"))

    def _period_metrics(self, connection, start: date, end: date) -> dict:
        start_text = start.isoformat()
        end_text = end.isoformat()
        rows = connection.execute(
            """
            SELECT event_type, payload_json
            FROM ejixhole_event_inbox
            WHERE substr(occurred_at,1,10) BETWEEN ? AND ?
            """,
            (start_text, end_text),
        ).fetchall()

        created = cancelled = completed = payments = 0
        gross = refunds = Decimal("0")
        daily: dict[str, dict] = {}
        for day_offset in range((end - start).days + 1):
            day = (start + timedelta(days=day_offset)).isoformat()
            daily[day] = {"reservations": 0, "net_revenue": Decimal("0"), "visits": 0, "cancellations": 0}

        dated_rows = connection.execute(
            """
            SELECT event_type, payload_json, substr(occurred_at,1,10) AS event_day
            FROM ejixhole_event_inbox
            WHERE substr(occurred_at,1,10) BETWEEN ? AND ?
            ORDER BY occurred_at
            """,
            (start_text, end_text),
        ).fetchall()
        for row in dated_rows:
            event_type = row["event_type"]
            day = row["event_day"]
            payload = json.loads(row["payload_json"])
            if event_type == "reservation.created":
                created += 1
                daily[day]["reservations"] += 1
            elif event_type == "reservation.cancelled":
                cancelled += 1
                daily[day]["cancellations"] += 1
            elif event_type == "visit.completed":
                completed += 1
                daily[day]["visits"] += 1
            elif event_type == "payment.recorded":
                payments += 1
                amount = self._decimal(payload.get("amount"))
                if payload.get("payment_type") == "reembolso":
                    refunds += amount
                    daily[day]["net_revenue"] -= amount
                else:
                    gross += amount
                    daily[day]["net_revenue"] += amount

        return {
            "reservations_created": created,
            "reservations_cancelled": cancelled,
            "visits_completed": completed,
            "payments_recorded": payments,
            "gross_payments": gross,
            "refunds": refunds,
            "net_revenue": gross - refunds,
            "daily": daily,
        }

    @staticmethod
    def _percent_change(current: Decimal | int, previous: Decimal | int) -> float | None:
        current_decimal = Decimal(str(current))
        previous_decimal = Decimal(str(previous))
        if previous_decimal == 0:
            return None if current_decimal == 0 else 100.0
        return round(float((current_decimal - previous_decimal) / previous_decimal * 100), 1)

    def build(self, business_date: date | None = None, days: int = 7) -> dict:
        target = business_date or datetime.now(timezone.utc).date()
        if not 1 <= days <= 31:
            raise ValueError("days debe estar entre 1 y 31")
        self.processor.process_pending()

        current_start = target - timedelta(days=days - 1)
        previous_end = current_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=days - 1)

        with self.processor.inbox._connect() as connection:
            current = self._period_metrics(connection, current_start, target)
            previous = self._period_metrics(connection, previous_start, previous_end)
            reservations = connection.execute(
                """
                SELECT status, reservation_type, people, total, paid_amount, pending_balance,
                       arrival_date, departure_date
                FROM ejixhole_operational_reservations
                """
            ).fetchall()
            processed_events = int(connection.execute(
                "SELECT COUNT(*) FROM ejixhole_processed_events"
            ).fetchone()[0])

        active = 0
        pending_balance = Decimal("0")
        upcoming_7_days = 0
        people_upcoming = 0
        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}
        for row in reservations:
            status = row["status"]
            by_status[status] = by_status.get(status, 0) + 1
            reservation_type = row["reservation_type"] or "sin_clasificar"
            by_type[reservation_type] = by_type.get(reservation_type, 0) + 1
            if status not in {"completada", "cancelada"}:
                active += 1
                pending_balance += self._decimal(row["pending_balance"])
                arrival = row["arrival_date"]
                if arrival and target.isoformat() <= arrival <= (target + timedelta(days=7)).isoformat():
                    upcoming_7_days += 1
                    people_upcoming += int(row["people"] or 0)

        cancellation_rate = (
            round(current["reservations_cancelled"] / current["reservations_created"] * 100, 1)
            if current["reservations_created"] else 0.0
        )
        trends = {
            "reservations_percent": self._percent_change(current["reservations_created"], previous["reservations_created"]),
            "net_revenue_percent": self._percent_change(current["net_revenue"], previous["net_revenue"]),
            "cancellations_percent": self._percent_change(current["reservations_cancelled"], previous["reservations_cancelled"]),
            "visits_percent": self._percent_change(current["visits_completed"], previous["visits_completed"]),
        }

        alerts: list[dict] = []
        recommendations: list[dict] = []
        if pending_balance > Decimal("5000"):
            alerts.append({"code": "HIGH_PENDING_BALANCE", "severity": "warning", "message": f"Hay ${pending_balance:.2f} pendientes de cobro."})
            recommendations.append({"code": "FOLLOW_UP_PAYMENTS", "priority": "high", "message": "Prioriza el seguimiento de reservaciones con saldo pendiente antes de su visita."})
        if cancellation_rate >= 20 and current["reservations_created"] >= 3:
            alerts.append({"code": "HIGH_CANCELLATION_RATE", "severity": "warning", "message": f"La tasa de cancelación del periodo es {cancellation_rate}%."})
            recommendations.append({"code": "REVIEW_CANCELLATIONS", "priority": "high", "message": "Revisa motivos de cancelación y confirma políticas y recordatorios previos."})
        if upcoming_7_days >= 5:
            alerts.append({"code": "BUSY_WEEK_AHEAD", "severity": "info", "message": f"Hay {upcoming_7_days} reservaciones y {people_upcoming} visitantes previstos en 7 días."})
            recommendations.append({"code": "PREPARE_OPERATIONS", "priority": "medium", "message": "Confirma personal, caja, insumos y capacidad para las próximas visitas."})
        if current["reservations_created"] > 0 and current["payments_recorded"] == 0:
            alerts.append({"code": "NO_PAYMENTS_RECORDED", "severity": "info", "message": "Hay reservaciones nuevas sin pagos registrados en el periodo."})
        if not recommendations:
            recommendations.append({"code": "CONTINUE_MONITORING", "priority": "low", "message": "La operación no presenta alertas críticas; continúa monitoreando cobros y próximas visitas."})

        timeline = [
            {
                "date": day,
                "reservations": values["reservations"],
                "net_revenue": self._money(values["net_revenue"]),
                "visits": values["visits"],
                "cancellations": values["cancellations"],
            }
            for day, values in current["daily"].items()
        ]

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "business_date": target.isoformat(),
            "period": {"days": days, "start": current_start.isoformat(), "end": target.isoformat()},
            "source": "ejixhole_events",
            "access": "read_only",
            "processed_events": processed_events,
            "kpis": {
                "net_revenue": self._money(current["net_revenue"]),
                "reservations_created": current["reservations_created"],
                "visits_completed": current["visits_completed"],
                "reservations_cancelled": current["reservations_cancelled"],
                "cancellation_rate": cancellation_rate,
                "active_reservations": active,
                "pending_balance": self._money(pending_balance),
                "upcoming_reservations_7_days": upcoming_7_days,
                "upcoming_people_7_days": people_upcoming,
            },
            "trends": trends,
            "timeline": timeline,
            "breakdown": {"reservations_by_status": by_status, "reservations_by_type": by_type},
            "alerts": alerts,
            "recommendations": recommendations,
        }
