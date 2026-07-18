"""Centro operativo: alertas, resumen, contexto y seguimiento de recomendaciones."""
from __future__ import annotations

from datetime import date, datetime, timezone

from mh_core.integrations.ejixhole_calibrated_predictions import EjixholeCalibratedPredictionsService
from mh_core.integrations.ejixhole_seasonality import EjixholeSeasonalityService


class EjixholeIntelligenceCenterService:
    def __init__(self, path=None) -> None:
        self.predictions = EjixholeCalibratedPredictionsService(path)
        self._initialize()

    @property
    def inbox(self):
        return self.predictions.predictions.dashboard.processor.inbox

    def _initialize(self) -> None:
        with self.inbox._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ejixhole_recommendation_decisions (
                    business_date TEXT NOT NULL,
                    code TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    decided_at TEXT NOT NULL,
                    outcome TEXT,
                    outcome_note TEXT,
                    outcome_at TEXT,
                    PRIMARY KEY (business_date, code)
                )
                """
            )

    def build(self, business_date: date | None = None) -> dict:
        result = self.predictions.build(business_date)
        target = date.fromisoformat(result["business_date"])
        dashboard = self.predictions.predictions.dashboard.build(target, days=14)
        seasonality = EjixholeSeasonalityService(self.inbox).analyze(target)
        kpis = dashboard["kpis"]
        alerts = []
        if result["predictions"]["cancellation_risk"] == "alto":
            alerts.append({"code": "CANCELLATION_RISK", "severity": "high", "message": "El riesgo de cancelación previsto es alto."})
        if float(kpis.get("pending_balance", 0) or 0) > 0:
            alerts.append({"code": "PENDING_BALANCE", "severity": "medium", "message": f"Hay ${float(kpis['pending_balance']):,.2f} de saldo pendiente."})
        if result["predictions"]["activity_level"] == "alto":
            alerts.append({"code": "HIGH_ACTIVITY", "severity": "high", "message": "La actividad prevista es alta; prepara personal, caja e insumos."})
        if seasonality["applied"] and seasonality["direction"] == "mayor_demanda":
            alerts.append({"code": "SEASONAL_DEMAND_UP", "severity": "medium", "message": "El patrón histórico del día y mes apunta a una demanda superior al promedio."})

        context = {
            "model_version": "v2.1",
            "weekday": target.strftime("%A").lower(),
            "historical_events": dashboard["processed_events"],
            "reservation_mix": dashboard.get("breakdown", {}).get("reservations_by_type", {}),
            "seasonality": seasonality,
            "weather": {"status": "not_connected", "message": "El clima aún no modifica la predicción."},
        }
        summary = {
            "title": "Resumen ejecutivo diario",
            "message": (
                f"Se esperan {result['predictions']['expected_visitors_7_days']} visitantes y "
                f"${float(result['predictions']['expected_revenue_7_days']):,.2f} de ingresos en 7 días."
            ),
            "alerts_count": len(alerts),
            "notification": {"channel": "admin_panel", "ready": True, "read_only": True},
        }

        decisions = self._decisions(result["business_date"])
        for recommendation in result["recommendations"]:
            recommendation["decision"] = decisions.get(recommendation["code"])

        result.update({"alerts": alerts, "daily_summary": summary, "context_factors": context})
        return result

    def decide(self, business_date: str, code: str, decision: str) -> dict:
        if decision not in {"accepted", "dismissed"}:
            raise ValueError("decision inválida")
        now = datetime.now(timezone.utc).isoformat()
        with self.inbox._connect() as connection:
            connection.execute(
                """
                INSERT INTO ejixhole_recommendation_decisions (business_date, code, decision, decided_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(business_date, code) DO UPDATE SET decision=excluded.decision, decided_at=excluded.decided_at
                """,
                (business_date, code, decision, now),
            )
        return {"business_date": business_date, "code": code, "decision": decision, "decided_at": now}

    def record_outcome(self, business_date: str, code: str, outcome: str, note: str | None = None) -> dict:
        if outcome not in {"helped", "neutral", "not_helpful"}:
            raise ValueError("outcome inválido")
        now = datetime.now(timezone.utc).isoformat()
        with self.inbox._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE ejixhole_recommendation_decisions
                SET outcome=?, outcome_note=?, outcome_at=?
                WHERE business_date=? AND code=?
                """,
                (outcome, note, now, business_date, code),
            )
            if cursor.rowcount == 0:
                raise ValueError("No existe una decisión registrada para esta recomendación.")
        return {"business_date": business_date, "code": code, "outcome": outcome, "note": note, "outcome_at": now}

    def history(self, limit: int = 50) -> dict:
        with self.inbox._connect() as connection:
            rows = connection.execute(
                """
                SELECT business_date, code, decision, decided_at, outcome, outcome_note, outcome_at
                FROM ejixhole_recommendation_decisions
                ORDER BY decided_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        items = [dict(row) for row in rows]
        accepted = [item for item in items if item["decision"] == "accepted"]
        evaluated = [item for item in accepted if item["outcome"]]
        helped = [item for item in evaluated if item["outcome"] == "helped"]
        pending = [item for item in accepted if not item["outcome"]]
        helped_percent = round((len(helped) / len(evaluated)) * 100, 1) if evaluated else None

        return {
            "summary": {
                "total_decisions": len(items),
                "accepted": len(accepted),
                "dismissed": len([item for item in items if item["decision"] == "dismissed"]),
                "evaluated": len(evaluated),
                "pending_evaluation": len(pending),
                "helped_percent": helped_percent,
            },
            "items": items,
        }

    def _decisions(self, business_date: str) -> dict[str, dict]:
        with self.inbox._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM ejixhole_recommendation_decisions WHERE business_date=?",
                (business_date,),
            ).fetchall()
        return {row["code"]: dict(row) for row in rows}
