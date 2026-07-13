class DecisionEngine:
    """
    Motor encargado de tomar decisiones sobre oportunidades rankeadas.
    """

    def __init__(self):
        self.name = "Decision Engine v2"

    def decide_best_opportunity(self, ranked_videos):
        if not ranked_videos:
            return {
                "decision": "NO_DECISION",
                "reason": "No hay oportunidades disponibles para analizar.",
                "best_opportunity": None
            }

        best = ranked_videos[0]
        score = best.get("mh_score", best.get("opportunity_score", 0))

        if score >= 70:
            decision = "PRODUCIR_INMEDIATAMENTE"
            reason = "Alta oportunidad: MH Core detectó fuerte crecimiento y buen potencial."
        elif score >= 40:
            decision = "PRODUCIR_CON_MEJORAS"
            reason = "Oportunidad media: se puede producir, pero necesita mejor ángulo, hook y diferenciación."
        else:
            decision = "NO_PRIORIZAR"
            reason = "Oportunidad baja: el potencial actual no justifica priorizar este tema."

        return {
            "decision": decision,
            "reason": reason,
            "best_opportunity": {
                "title": best.get("title"),
                "channel": best.get("channel"),
                "url": best.get("url"),
                "mh_score": score,
                "old_score": best.get("score"),
                "priority": best.get("priority")
            }
        }