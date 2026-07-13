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
        learning_engine = LearningEngine()
        learning_summary = learning_engine.summarize_learning()

        return {
            "system": "MH Core",
            "version": "2.0",
            "status": "ONLINE",
            "overall_progress": "60%",
            "modules": {
                "api": "READY",
                "research_engine": "READY",
                "scoring_engine": "READY",
                "ranking_engine": "READY",
                "pattern_engine": "READY",
                "decision_engine": "READY",
                "learning_engine": "READY",
                "dashboard": "IN_PROGRESS",
                "prediction_engine": "PENDING",
                "mh_brain": "PENDING"
            },
            "learning_summary": learning_summary
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
            "database": "OK",
            "engines": {
                "research": "OK",
                "scoring": "OK",
                "ranking": "OK",
                "patterns": "OK",
                "decision": "OK",
                "learning": "OK"
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