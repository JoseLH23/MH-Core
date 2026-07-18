"""Analisis estacional explicable para EjiXhole."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
import json


class EjixholeSeasonalityService:
    MIN_COMPARABLE_DAYS = 8
    LOOKBACK_DAYS = 365

    def __init__(self, inbox) -> None:
        self.inbox = inbox

    def analyze(self, target: date) -> dict:
        start = target - timedelta(days=self.LOOKBACK_DAYS)
        with self.inbox._connect() as connection:
            rows = connection.execute(
                "SELECT event_type, payload_json, substr(occurred_at,1,10) AS event_day FROM ejixhole_event_inbox WHERE substr(occurred_at,1,10) BETWEEN ? AND ? ORDER BY occurred_at",
                (start.isoformat(), (target - timedelta(days=1)).isoformat()),
            ).fetchall()

        daily = defaultdict(lambda: {"reservations": 0, "visits": 0, "revenue": Decimal("0")})
        for row in rows:
            values = daily[row["event_day"]]
            payload = json.loads(row["payload_json"])
            if row["event_type"] == "reservation.created":
                values["reservations"] += 1
            elif row["event_type"] == "visit.completed":
                values["visits"] += int(payload.get("people") or 1)
            elif row["event_type"] == "payment.recorded":
                amount = Decimal(str(payload.get("amount") or "0"))
                values["revenue"] += -amount if payload.get("payment_type") == "reembolso" else amount

        all_scores = []
        comparable = []
        for day_text, values in daily.items():
            observed = date.fromisoformat(day_text)
            score = values["reservations"] + values["visits"]
            all_scores.append(score)
            if observed.weekday() == target.weekday() and observed.month == target.month:
                comparable.append(score)

        baseline = sum(all_scores) / len(all_scores) if all_scores else 0
        comparable_average = sum(comparable) / len(comparable) if comparable else 0
        enough = len(comparable) >= self.MIN_COMPARABLE_DAYS and baseline > 0
        factor = round(min(1.20, max(0.80, comparable_average / baseline)), 2) if enough else 1.0
        direction = "mayor_demanda" if factor >= 1.08 else "menor_demanda" if factor <= 0.92 else "estable"

        return {
            "status": "enabled" if enough else "insufficient_data",
            "factor": factor,
            "direction": direction,
            "day_type": "fin_de_semana" if target.weekday() >= 5 else "dia_entre_semana",
            "weekday": target.strftime("%A").lower(),
            "month": target.month,
            "comparable_days": len(comparable),
            "minimum_comparable_days": self.MIN_COMPARABLE_DAYS,
            "lookback_days": self.LOOKBACK_DAYS,
            "applied": enough,
            "explanation": "Se compara el mismo dia de semana y mes contra el promedio historico; el ajuste se limita entre 0.80 y 1.20." if enough else "Aun no hay suficientes dias comparables; la prediccion no se modifica.",
        }
