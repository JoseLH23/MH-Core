"""Resumen ejecutivo diario construido desde eventos procesados de EjiXhole."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import json

from mh_core.integrations.ejixhole_configured_processor import ConfiguredEjixholeEventProcessor


class EjixholeDailySummaryService:
    def __init__(self, path: str | Path | None = None) -> None:
        self.processor = ConfiguredEjixholeEventProcessor(path)

    @staticmethod
    def _decimal(value: str | None) -> Decimal:
        return Decimal(value or "0")

    def build(self, business_date: date | None = None) -> dict:
        target = business_date or datetime.now(timezone.utc).date()
        self.processor.process_pending()

        with self.processor.inbox._connect() as connection:
            def count(event_type: str) -> int:
                return int(connection.execute(
                    "SELECT COUNT(*) FROM ejixhole_event_inbox WHERE event_type=? AND substr(occurred_at,1,10)=?",
                    (event_type, target.isoformat()),
                ).fetchone()[0])

            payment_rows = connection.execute(
                "SELECT payload_json FROM ejixhole_event_inbox WHERE event_type='payment.recorded' AND substr(occurred_at,1,10)=?",
                (target.isoformat(),),
            ).fetchall()
            reservation_rows = connection.execute(
                "SELECT status,total,paid_amount,pending_balance FROM ejixhole_operational_reservations"
            ).fetchall()
            processed_events = int(connection.execute(
                "SELECT COUNT(*) FROM ejixhole_processed_events"
            ).fetchone()[0])

        gross = Decimal("0")
        refunds = Decimal("0")
        for row in payment_rows:
            payload = json.loads(row["payload_json"])
            amount = self._decimal(str(payload.get("amount", "0")))
            if payload.get("payment_type") == "reembolso":
                refunds += amount
            else:
                gross += amount

        pending = Decimal("0")
        active = 0
        by_status: dict[str, int] = {}
        for row in reservation_rows:
            reservation_status = row["status"]
            by_status[reservation_status] = by_status.get(reservation_status, 0) + 1
            if reservation_status not in {"completada", "cancelada"}:
                active += 1
                if row["pending_balance"] is not None:
                    pending += self._decimal(row["pending_balance"])
                elif row["total"] is not None:
                    pending += max(
                        Decimal("0"),
                        self._decimal(row["total"]) - self._decimal(row["paid_amount"]),
                    )

        created = count("reservation.created")
        cancelled = count("reservation.cancelled")
        completed = count("visit.completed")
        alerts: list[dict] = []
        if cancelled >= 3:
            alerts.append({"code": "HIGH_CANCELLATIONS", "severity": "warning", "message": f"Se registraron {cancelled} cancelaciones en el día."})
        if pending > Decimal("5000"):
            alerts.append({"code": "HIGH_PENDING_BALANCE", "severity": "warning", "message": f"El saldo pendiente activo supera $5,000: ${pending:.2f}."})
        if created > 0 and gross == 0:
            alerts.append({"code": "RESERVATIONS_WITHOUT_PAYMENTS", "severity": "info", "message": "Hubo reservaciones nuevas, pero ningún pago registrado hoy."})

        return {
            "business_date": target.isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "ejixhole_events",
            "processed_events": processed_events,
            "metrics": {
                "reservations_created": created,
                "payments_recorded": len(payment_rows),
                "gross_payments": f"{gross:.2f}",
                "refunds": f"{refunds:.2f}",
                "net_revenue": f"{gross - refunds:.2f}",
                "visits_completed": completed,
                "reservations_cancelled": cancelled,
                "active_reservations": active,
                "pending_balance": f"{pending:.2f}",
                "reservations_by_status": by_status,
            },
            "alerts": alerts,
        }
