from pathlib import Path

from mh_core.config import YOUTUBE_API_KEY
from mh_core.engines.youtube_research_engine import YouTubeResearchEngine


def get_research_status():
    return {
        "module": "MindHigh Research Engine",
        "status": "ready",
        "youtube_api_configured": bool(YOUTUBE_API_KEY),
        "message": "Research Engine connected to MH Core"
    }


def run_research():
    project_path = Path("temp")
    project_path.mkdir(exist_ok=True)

    engine = YouTubeResearchEngine()
    result = engine.research(project_path)

    if result is None:
        return {
            "status": "error",
            "message": "No se encontraron tendencias."
        }

    return {
        "status": "success",
        "topic": result["topic"],
        "winner": result["winner"],
        "top_videos": result["top_videos"][:5],
        "report_path": result["report_path"]
    }