from mh_core.core.mission import MISSION
from mh_core.core.philosophy import MH_PRINCIPLES
from mh_core.knowledge.knowledge_engine import KnowledgeEngine


class MHBrain:
    """
    Cerebro ejecutivo de MH Core.
    Combina decisión, predicción, patrones, aprendizaje y misión.
    """

    def __init__(self):
        self.name = "MH Brain v1"

    def generate_report(
        self,
        topic: str,
        decision: dict,
        prediction: dict,
        patterns: dict,
        learning_summary: dict
    ) -> dict:

        best = decision.get("best_opportunity") or {}

        probability = prediction.get("success_probability", 0)
        confidence = prediction.get("confidence", "LOW")
        risk = prediction.get("risk", "HIGH")
        recommendation = prediction.get("recommendation", "NO_PRIORIZAR")

        reasons = self._generate_reasons(
            decision=decision,
            prediction=prediction,
            patterns=patterns,
            learning_summary=learning_summary
        )

        actions = self._generate_actions(
            recommendation=recommendation,
            risk=risk,
            confidence=confidence,
            patterns=patterns
        )
        
        knowledge = KnowledgeEngine()

        topics = knowledge.get_topics()
        channels = knowledge.get_channels()

        return {
            "brain": self.name,
            "mission": MISSION,
            "principles": MH_PRINCIPLES,
            "executive_summary": {
                "topic": topic,
                "recommended_video": best.get("title"),
                "recommended_channel": best.get("channel"),
                "success_probability": probability,
                "confidence": confidence,
                "risk": risk,
                "final_recommendation": recommendation
            },
            "reasoning": reasons,
            "recommended_actions": actions,

            "knowledge": {
                "topics": topics,
                "channels": channels
            },

            "evidence": {
                "decision": decision,
                "prediction": prediction,
                "patterns": patterns,
                "learning_summary": learning_summary
            }
        }

    def _generate_reasons(
        self,
        decision: dict,
        prediction: dict,
        patterns: dict,
        learning_summary: dict
    ) -> list[str]:

        reasons = []

        best = decision.get("best_opportunity") or {}
        mh_score = best.get("mh_score", 0)

        if mh_score >= 70:
            reasons.append("El MH Score es alto, lo que indica una oportunidad fuerte según el criterio interno de MH Core.")
        elif mh_score >= 40:
            reasons.append("El MH Score es medio, por lo que la oportunidad existe pero requiere mejor enfoque.")
        else:
            reasons.append("El MH Score es bajo, por lo que la oportunidad no debe priorizarse sin más evidencia.")

        opportunity_level = patterns.get("opportunity_level")

        if opportunity_level == "HIGH":
            reasons.append("El patrón general del mercado indica un nivel de oportunidad alto.")
        elif opportunity_level == "MEDIUM":
            reasons.append("El patrón general del mercado indica una oportunidad media.")
        else:
            reasons.append("El patrón general todavía no muestra suficiente fuerza de mercado.")

        if prediction.get("risk") == "LOW":
            reasons.append("La predicción estima riesgo bajo para esta oportunidad.")
        elif prediction.get("risk") == "MEDIUM":
            reasons.append("La predicción estima riesgo medio; conviene producir con cuidado.")
        else:
            reasons.append("La predicción estima riesgo alto; conviene esperar o buscar otro ángulo.")

        total_memories = learning_summary.get("total_memories", 0)

        if total_memories >= 20:
            reasons.append("El sistema cuenta con suficiente historial para generar una recomendación con mayor confianza.")
        elif total_memories >= 5:
            reasons.append("El sistema ya tiene historial inicial, pero todavía está construyendo confianza.")
        else:
            reasons.append("El historial aún es pequeño, por lo que la confianza predictiva es limitada.")

        return reasons

    def _generate_actions(
        self,
        recommendation: str,
        risk: str,
        confidence: str,
        patterns: dict
    ) -> list[str]:

        actions = []

        if recommendation == "PRODUCIR":
            actions.append("Producir contenido sobre este tema lo antes posible.")
        elif recommendation == "PRODUCIR_CON_CUIDADO":
            actions.append("Producir solo si se mejora el ángulo, el hook y la diferenciación.")
        else:
            actions.append("No priorizar esta oportunidad por ahora.")

        title_patterns = patterns.get("title_patterns", {})

        if title_patterns.get("question_titles", 0) > 0:
            actions.append("Usar un título con pregunta o curiosidad abierta.")

        if title_patterns.get("emotional_titles", 0) > 0:
            actions.append("Incluir una palabra emocional o de alta curiosidad en el título.")

        if risk == "MEDIUM":
            actions.append("Validar el tema con una segunda investigación antes de invertir demasiado tiempo.")

        if confidence == "LOW":
            actions.append("Seguir acumulando historial antes de confiar plenamente en la predicción.")

        return actions