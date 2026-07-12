from mh_core.services.research_service import ResearchService

VIDEOS_EJEMPLO = [
    {
        "query": "ia", "video_id": "abc", "title": "Video de prueba viral", "channel": "Canal",
        "views": 200000, "views_per_day": 15000, "likes": 8000, "comments": 400,
        "age_days": 4, "url": "https://youtube.com/watch?v=abc", "score": 120.5,
    }
]


def test_research_incluye_analysis_y_engine_decision(monkeypatch):
    """research() debe seguir teniendo 'research'/'analysis' (compatibilidad)
    Y ahora también 'engine_decision'/'engine_patterns' (integración completa)."""

    def _fuente_falsa():
        return {"topic": "inteligencia artificial", "top_videos": VIDEOS_EJEMPLO}

    monkeypatch.setattr(ResearchService, "_run_source", staticmethod(_fuente_falsa))

    resultado = ResearchService.research()

    # Compatibilidad: nada de lo que ya existía se quitó.
    assert "research" in resultado
    assert "analysis" in resultado
    assert resultado["analysis"]["total_opportunities"] == 1

    # Integración nueva: ahora también pasa por Ranking/Pattern/Decision real.
    assert "engine_decision" in resultado
    assert "engine_patterns" in resultado
    assert resultado["engine_decision"]["decision"] in {
        "PRODUCIR_INMEDIATAMENTE", "PRODUCIR_CON_MEJORAS", "NO_PRIORIZAR", "NO_DECISION"
    }
    assert resultado["engine_patterns"]["total_videos"] == 1


def test_research_no_guarda_memoria(monkeypatch, tmp_path):
    """research() usa remember=False — es un endpoint de exploración, no debe
    escribir en el historial real cada vez que alguien lo consulta."""
    from mh_core.core.orchestrator import Orchestrator
    from mh_core.database.json_memory_repository import JsonMemoryRepository
    from mh_core.engines.learning_engine import LearningEngine
    from mh_core.engines.memory_engine import MemoryEngine

    repo = JsonMemoryRepository(tmp_path / "history.json")
    learning_engine = LearningEngine(memory_engine=MemoryEngine(repository=repo))

    # Se reemplaza el Orchestrator que usa el service por uno aislado,
    # para comprobar remember=False sin tocar el archivo real.
    orquestador_aislado = Orchestrator(learning_engine=learning_engine)
    monkeypatch.setattr(
        "mh_core.services.research_service.Orchestrator",
        lambda: orquestador_aislado,
    )
    monkeypatch.setattr(
        ResearchService, "_run_source",
        staticmethod(lambda: {"topic": "ia", "top_videos": VIDEOS_EJEMPLO}),
    )

    ResearchService.research()

    assert learning_engine.get_history() == []
