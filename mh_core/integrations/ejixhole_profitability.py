"""Ingresos por servicio con transparencia sobre costos faltantes."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import json


class EjixholeProfitabilityService:
    def __init__(self, inbox) -> None:
        self.inbox = inbox

    def build(self, target: date, days: int = 30) -> dict:
        if not 1 <= days <= 365:
            raise ValueError("days debe estar entre 1 y 365")
        start = target - timedelta(days=days - 1)
        with self.inbox._connect() as connection:
            rows = connection.execute(
                "SELECT event_type, payload_json, substr(occurred_at,1,10) AS event_day FROM ejixhole_event_inbox WHERE substr(occurred_at,1,10) BETWEEN ? AND ? ORDER BY occurred_at",
                (start.isoformat(), target.isoformat()),
            ).fetchall()

        reservations: dict[str, dict] = {}
        revenue_by_service: dict[str, Decimal] = {}
        refunds_by_service: dict[str, Decimal] = {}
        completed_by_service: dict[str, int] = {}

        for row in rows:
            payload = json.loads(row["payload_json"])
            event_type = row["event_type"]
            if event_type == "reservation.created":
                reservations[str(payload["reservation_id"])] = {
                    "service_id": str(payload.get("service_id") or "sin_servicio"),
                    "reservation_type": payload.get("reservation_type") or "sin_clasificar",
                }
            elif event_type == "payment.recorded":
                reservation = reservations.get(str(payload.get("reservation_id")))
                if not reservation:
                    continue
                service_id = reservation["service_id"]
                amount = Decimal(str(payload.get("amount") or "0"))
                if payload.get("payment_type") == "reembolso":
                    refunds_by_service[service_id] = refunds_by_service.get(service_id, Decimal("0")) + amount
                else:
                    revenue_by_service[service_id] = revenue_by_service.get(service_id, Decimal("0")) + amount
            elif event_type == "visit.completed":
                reservation = reservations.get(str(payload.get("reservation_id")))
                if reservation:
                    service_id = reservation["service_id"]
                    completed_by_service[service_id] = completed_by_service.get(service_id, 0) + 1

        service_ids = sorted(set(revenue_by_service) | set(refunds_by_service) | set(completed_by_service))
        items = []
        total_net = Decimal("0")
        for service_id in service_ids:
            gross = revenue_by_service.get(service_id, Decimal("0"))
            refunds = refunds_by_service.get(service_id, Decimal("0"))
            net = gross - refunds
            total_net += net
            items.append({
                "service_id": service_id,
                "gross_revenue": f"{gross:.2f}",
                "refunds": f"{refunds:.2f}",
                "net_revenue": f"{net:.2f}",
                "completed_visits": completed_by_service.get(service_id, 0),
                "costs": None,
                "margin": None,
                "cost_status": "missing",
            })

        items.sort(key=lambda item: Decimal(item["net_revenue"]), reverse=True)
        return {
            "period": {"days": days, "start": start.isoformat(), "end": target.isoformat()},
            "source": "ejixhole_events",
            "access": "read_only",
            "total_net_revenue": f"{total_net:.2f}",
            "services": items,
            "costs_available": False,
            "message": "Se muestran ingresos netos conocidos. Los márgenes no se calculan hasta registrar costos reales por servicio.",
        }
