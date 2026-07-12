from mh_core.intelligence.analyzer import analyze_opportunities
from mh_core.core.orchestrator import Orchestrator
from mh_core.utils.logger import logger
from mh_core.plugins.plugin_manager import PluginManager


class ResearchService:

    @staticmethod
    def _run_source():
        manager = PluginManager()
        plugin_result = manager.run_plugin("youtube")
        return plugin_result["data"]

    @staticmethod
    def research():
        """
        INTEGRACIÓN COMPLETA (última pieza pendiente del roadmap):
        antes, este endpoint era el ÚNICO que NO pasaba por la cadena
        real de engines (Ranking/Pattern/Decision) — usaba solo
        OpportunityFactory + analyze_opportunities, un camino aislado.

        Ahora también corre por el Orchestrator, así que se beneficia
        de Pattern/Decision igual que /ranking, /decision, /prediction
        y /brain. Las claves "research"/"analysis" que ya existían NO
        cambiaron (nada que ya consuma este endpoint se rompe) — se
        agregan "engine_decision"/"engine_patterns" con lo que aporta
        la cadena de engines real.

        Las DOS matemáticas de score (la de YouTubeResearchEngine, ya
        incluida en cada video como `score`, y la de ScoringEngine,
        calculada aparte como `mh_score`) siguen siendo distintas a
        propósito — fusionarlas cambiaría en silencio qué recomienda
        DecisionEngine (sus umbrales HIGH/MEDIUM/LOW están calibrados
        sobre la fórmula de ScoringEngine). Eso es una decisión de
        negocio aparte, no algo para decidir dentro de esta fase.
        """
        logger.info("Starting research pipeline...")

        result = ResearchService._run_source()
        videos = result.get("top_videos", [])
        analysis = analyze_opportunities(videos)

        pipeline = Orchestrator().run(topic=result.get("topic"), videos=videos, remember=False, hasta="decision")

        logger.info("Research pipeline finished successfully.")

        return {
            "research": result,
            "analysis": analysis,
            "engine_decision": pipeline["decision"],
            "engine_patterns": pipeline["patterns"]
        }

    @staticmethod
    def ranking():
        result = ResearchService._run_source()
        videos = result.get("top_videos", [])

        pipeline = Orchestrator().run(topic=result.get("topic"), videos=videos, remember=False, hasta="ranking")

        return {
            "endpoint": "/research/ranking",
            "status": "success",
            "topic": result.get("topic"),
            "total_videos_analyzed": len(videos),
            "top_opportunities": pipeline["ranked"]
        }

    @staticmethod
    def decision():
        result = ResearchService._run_source()
        videos = result.get("top_videos", [])

        pipeline = Orchestrator().run(topic=result.get("topic"), videos=videos, remember=True, hasta="decision")

        return {
            "endpoint": "/research/decision",
            "status": "success",
            "topic": result.get("topic"),
            "decision": pipeline["decision"],
            "patterns": pipeline["patterns"],
            "memory_saved": pipeline.get("memory")
        }

    @staticmethod
    def prediction():
        result = ResearchService._run_source()
        videos = result.get("top_videos", [])

        pipeline = Orchestrator().run(topic=result.get("topic"), videos=videos, remember=False, hasta="prediction")

        return {
            "endpoint": "/research/prediction",
            "status": "success",
            "topic": result.get("topic"),
            "decision": pipeline["decision"],
            "patterns": pipeline["patterns"],
            "prediction": pipeline["prediction"]
        }

    @staticmethod
    def brain():
        result = ResearchService._run_source()
        videos = result.get("top_videos", [])

        pipeline = Orchestrator().run(topic=result.get("topic"), videos=videos, remember=False, hasta="brain")

        return {
            "endpoint": "/research/brain",
            "status": "success",
            "brain_report": pipeline["brain_report"]
        }

    @staticmethod
    def learning():
        from mh_core.engines.learning_engine import LearningEngine

        learning_engine = LearningEngine()
        summary = learning_engine.summarize_learning()

        return {
            "endpoint": "/research/learning",
            "status": "success",
            "learning_summary": summary
        }