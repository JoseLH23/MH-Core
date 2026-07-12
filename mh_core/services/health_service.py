from datetime import datetime

def get_health_status():
    return {
        "status": "healthy",
        "system": "MH Core",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "modules": {
            "api": "online",
            "database": "json (local, database/)",
            "research_engine": "online (YouTube real)",
            "memory_engine": "online (JSON repository, migrable a Postgres)",
            "decision_engine": "online",
            "prediction_engine": "online",
            "orchestrator": "online",
            "automation_engine": "online",
            "intelligence_engine": "pending",
            "media_engine": "pending"
        }
    }