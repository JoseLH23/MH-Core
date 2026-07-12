"""
Orchestrator central — Fase "Orchestrator" del roadmap.

HALLAZGO REAL de la auditoría: `ResearchService` (mh_core/services/
research_service.py) repite casi textual, en 4 métodos distintos
(ranking/decision/prediction/brain), la misma secuencia:
    RankingEngine -> PatternEngine -> DecisionEngine -> LearningEngine
    -> PredictionEngine -> MHBrain
cada uno recomputando desde cero lo que el anterior ya calculó. Este
Orchestrator centraliza esa secuencia UNA sola vez, testeable de forma
aislada (todos los engines son inyectables), y `ResearchService` pasa
a llamarlo en vez de repetir el bloque.

NO se fusiona la matemática de scoring de `ResearchService.research()`
(OpportunityFactory/analyze_opportunities, que reutiliza el `score`
que YouTubeResearchEngine ya calculó por video) con la de
ScoringEngine (`mh_score`, usada aquí) — son dos fórmulas reales
distintas y fusionarlas cambiaría en silencio los umbrales de
DecisionEngine. Sí se conectó `research()` a este Orchestrator (fase
"Integración completa") para que también se beneficie de
Pattern/Decision — ver docstring de `ResearchService.research()`.
"""
from typing import Optional

from mh_core.brain.brain_engine import MHBrain
from mh_core.engines.decision_engine import DecisionEngine
from mh_core.engines.learning_engine import LearningEngine
from mh_core.engines.pattern_engine import PatternEngine
from mh_core.engines.prediction_engine import PredictionEngine
from mh_core.engines.ranking_engine import RankingEngine
from mh_core.utils.logger import logger


class Orchestrator:
    def __init__(
        self,
        ranking_engine: Optional[RankingEngine] = None,
        pattern_engine: Optional[PatternEngine] = None,
        decision_engine: Optional[DecisionEngine] = None,
        prediction_engine: Optional[PredictionEngine] = None,
        learning_engine: Optional[LearningEngine] = None,
        brain: Optional[MHBrain] = None,
    ):
        self.ranking_engine = ranking_engine or RankingEngine()
        self.pattern_engine = pattern_engine or PatternEngine()
        self.decision_engine = decision_engine or DecisionEngine()
        self.prediction_engine = prediction_engine or PredictionEngine()
        self.learning_engine = learning_engine or LearningEngine()
        self.brain = brain or MHBrain()

    def run(self, topic: Optional[str], videos: list[dict], remember: bool = True, hasta: str = "brain") -> dict:
        """
        Ejecuta la secuencia completa (o parcial, con `hasta`) UNA sola
        vez. `hasta` acepta: "ranking", "decision", "prediction", "brain"
        — para que cada endpoint de ResearchService pida exactamente
        hasta dónde necesita, sin recalcular ni tampoco hacer trabajo
        de más que nadie pidió.

        `remember=False` es para cuando se quiere ranking/patterns sin
        escribir un recuerdo nuevo (ej. un endpoint de solo consulta).
        """
        logger.info(f"Orchestrator: iniciando pipeline (tema='{topic}', hasta='{hasta}', videos={len(videos)}).")

        ranked = self.ranking_engine.rank_videos(videos)
        resultado = {"topic": topic, "ranked": ranked}
        if hasta == "ranking":
            return resultado

        patterns = self.pattern_engine.detect_patterns(videos)
        decision = self.decision_engine.decide_best_opportunity(ranked)
        resultado["patterns"] = patterns
        resultado["decision"] = decision
        if hasta == "decision":
            if remember:
                resultado["memory"] = self.learning_engine.remember(topic=topic, decision=decision, patterns=patterns)
            return resultado

        memory = None
        if remember:
            memory = self.learning_engine.remember(topic=topic, decision=decision, patterns=patterns)
        learning_summary = self.learning_engine.summarize_learning()
        prediction = self.prediction_engine.predict(decision=decision, patterns=patterns, learning_summary=learning_summary)
        resultado["memory"] = memory
        resultado["learning_summary"] = learning_summary
        resultado["prediction"] = prediction
        if hasta == "prediction":
            return resultado

        brain_report = self.brain.generate_report(
            topic=topic, decision=decision, prediction=prediction, patterns=patterns, learning_summary=learning_summary
        )
        resultado["brain_report"] = brain_report

        logger.info(f"Orchestrator: pipeline completo (tema='{topic}').")
        return resultado
