class PredictionEngine:
    """
    Motor encargado de estimar la probabilidad de éxito de una oportunidad.
    """

    def __init__(self):
        self.name = "Prediction Engine v1"

    def predict(self, decision: dict, patterns: dict, learning_summary: dict) -> dict:
        best = decision.get("best_opportunity") or {}

        mh_score = best.get("mh_score", 0)
        opportunity_level = patterns.get("opportunity_level", "LOW")
        average_history_score = learning_summary.get("average_mh_score", 0)
        total_memories = learning_summary.get("total_memories", 0)

        probability = 0

        probability += min(mh_score, 80)

        if opportunity_level == "HIGH":
            probability += 10
        elif opportunity_level == "MEDIUM":
            probability += 5

        if average_history_score >= 70:
            probability += 5
        elif average_history_score >= 40:
            probability += 3

        if total_memories >= 20:
            confidence = "HIGH"
        elif total_memories >= 5:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        probability = min(round(probability, 2), 95)

        if probability >= 80:
            risk = "LOW"
            recommendation = "PRODUCIR"
        elif probability >= 55:
            risk = "MEDIUM"
            recommendation = "PRODUCIR_CON_CUIDADO"
        else:
            risk = "HIGH"
            recommendation = "NO_PRIORIZAR"

        return {
            "success_probability": probability,
            "confidence": confidence,
            "risk": risk,
            "recommendation": recommendation,
            "signals": {
                "mh_score": mh_score,
                "opportunity_level": opportunity_level,
                "average_history_score": average_history_score,
                "total_memories": total_memories
            }
        }