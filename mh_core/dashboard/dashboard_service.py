from mh_core.engines.learning_engine import LearningEngine
from mh_core.services.research_service import ResearchService
from mh_core.plugins.plugin_manager import PluginManager
from mh_core.knowledge.knowledge_engine import KnowledgeEngine

class DashboardService:
    """
    Servicio encargado de exponer el estado general de MH Core.
    """
    @staticmethod
    def knowledge():
        engine = KnowledgeEngine()

        return {
            "endpoint": "/dashboard/knowledge",
            "status": "success",
            "topics": engine.get_topics(),
            "channels": engine.get_channels()
        }

    @staticmethod
    def overview():
        """
        HALLAZGO REAL (auditoría): este dashboard se escribió antes de
        Memory Engine, Orchestrator, Automation Engine, Agentes,
        integración con Gemini/Groq y el flujo de MindHigh — seguía
        diciendo "PENDING" para PredictionEngine y MHBrain, que llevan
        varias fases funcionando de verdad. También tenía un
        "overall_progress": "60%" fijo, sin ninguna fórmula real
        detrás — un número inventado, no un dato. Se quita en vez de
        inventar otro número igual de arbitrario.
        """
        learning_engine = LearningEngine()
        learning_summary = learning_engine.summarize_learning()

        return {
            "system": "MH Core",
            "version": "2.0",
            "status": "ONLINE",
            "modules": {
                "api": "READY",
                "research_engine": "READY",
                "scoring_engine": "READY",
                "ranking_engine": "READY",
                "pattern_engine": "READY",
                "decision_engine": "READY",
                "prediction_engine": "READY",
                "mh_brain": "READY",
                "learning_engine": "READY",
                "memory_engine": "READY",
                "orchestrator": "READY",
                "automation_engine": "READY",
                "agents": "READY",
                "dashboard": "READY",
                # Honestos sobre lo que de verdad no existe todavía,
                # en vez de omitirlos.
                "vector_db": "PENDING",
                "postgres": "PENDING",
            },
            "learning_summary": learning_summary,
        }
       
    @staticmethod
    def prediction():
        return {
            "endpoint": "/dashboard/prediction",
            "status": "success",
            "data": ResearchService.prediction()
        }

    @staticmethod
    def system_status():
        return {
            "system": "MH Core",
            "status": "ONLINE",
            "api": "OK",
            "database": "OK (JSON local — ver Master Plan sobre migración futura a Postgres)",
            "engines": {
                "research": "OK",
                "scoring": "OK",
                "ranking": "OK",
                "patterns": "OK",
                "decision": "OK",
                "prediction": "OK",
                "mh_brain": "OK",
                "learning": "OK",
                "memory": "OK",
                "orchestrator": "OK",
                "automation": "OK",
                "agents": "OK",
            }
        }
    
    @staticmethod
    def plugins():
        manager = PluginManager()

        return {
            "endpoint": "/dashboard/plugins",
            "status": "success",
            "available_plugins": manager.list_plugins()
        }

    @staticmethod
    def learning():
        learning_engine = LearningEngine()

        return {
            "endpoint": "/dashboard/learning",
            "status": "success",
            "data": learning_engine.summarize_learning()
        }
    
    @staticmethod
    def statistics():
        learning_engine = LearningEngine()
        summary = learning_engine.summarize_learning()

        return {
            "endpoint": "/dashboard/statistics",
            "status": "success",
            "statistics": {
                "total_memories": summary.get("total_memories", 0),
                "average_mh_score": summary.get("average_mh_score", 0),
                "most_common_topics": summary.get("most_common_topics", []),
                "most_common_decisions": summary.get("most_common_decisions", []),
                "most_common_channels": summary.get("most_common_channels", []),
                "most_common_priorities": summary.get("most_common_priorities", []),
                "most_common_opportunity_levels": summary.get("most_common_opportunity_levels", [])
            }
        }