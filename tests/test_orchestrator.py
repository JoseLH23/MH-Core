from mh_core.core.orchestrator import Orchestrator
from mh_core.database.json_memory_repository import JsonMemoryRepository
from mh_core.engines.learning_engine import LearningEngine
from mh_core.engines.memory_engine import MemoryEngine

VIDEOS_EJEMPLO = [
    {
        "query": "inteligencia artificial",
        "video_id": "abc123",
        "title": "Por qué la IA está cambiando todo",
        "channel": "Canal Ejemplo",
        "views": 500000,
        "views_per_day": 20000,
        "likes": 30000,
        "comments": 1200,
        "age_days": 5,
        "url": "https://youtube.com/watch?v=abc123",
    },
    {
        "query": "inteligencia artificial",
        "video_id": "def456",
        "title": "El secreto detrás de ChatGPT",
        "channel": "Otro Canal",
        "views": 100000,
        "views_per_day": 3000,
        "likes": 5000,
        "comments": 300,
        "age_days": 20,
        "url": "https://youtube.com/watch?v=def456",
    },
]


def _orchestrator_aislado(tmp_path):
    """LearningEngine con MemoryEngine apuntando a un archivo temporal —
    nunca toca database/learning/history.json real."""
    repo = JsonMemoryRepository(tmp_path / "history.json")
    learning_engine = LearningEngine(memory_engine=MemoryEngine(repository=repo))
    return Orchestrator(learning_engine=learning_engine)


def test_run_hasta_ranking_no_calcula_de_mas(tmp_path):
    orquestador = _orchestrator_aislado(tmp_path)
    resultado = orquestador.run(topic="ia", videos=VIDEOS_EJEMPLO, hasta="ranking")

    assert "ranked" in resultado
    assert "patterns" not in resultado
    assert "decision" not in resultado
    assert len(resultado["ranked"]) == 2


def test_run_hasta_decision_incluye_patterns_y_decision(tmp_path):
    orquestador = _orchestrator_aislado(tmp_path)
    resultado = orquestador.run(topic="ia", videos=VIDEOS_EJEMPLO, hasta="decision", remember=False)

    assert "patterns" in resultado
    assert "decision" in resultado
    assert resultado["decision"]["decision"] in {
        "PRODUCIR_INMEDIATAMENTE", "PRODUCIR_CON_MEJORAS", "NO_PRIORIZAR", "NO_DECISION"
    }


def test_run_completo_hasta_brain_incluye_todo(tmp_path):
    orquestador = _orchestrator_aislado(tmp_path)
    resultado = orquestador.run(topic="ia", videos=VIDEOS_EJEMPLO, hasta="brain", remember=False)

    for clave in ["ranked", "patterns", "decision", "learning_summary", "prediction", "brain_report"]:
        assert clave in resultado
    assert "executive_summary" in resultado["brain_report"]


def test_remember_true_guarda_en_memory_engine(tmp_path):
    repo = JsonMemoryRepository(tmp_path / "history.json")
    learning_engine = LearningEngine(memory_engine=MemoryEngine(repository=repo))
    orquestador = Orchestrator(learning_engine=learning_engine)

    orquestador.run(topic="ia", videos=VIDEOS_EJEMPLO, hasta="decision", remember=True)

    memorias = learning_engine.get_history()
    assert len(memorias) == 1
    assert memorias[0]["topic"] == "ia"


def test_remember_false_no_guarda_nada(tmp_path):
    repo = JsonMemoryRepository(tmp_path / "history.json")
    learning_engine = LearningEngine(memory_engine=MemoryEngine(repository=repo))
    orquestador = Orchestrator(learning_engine=learning_engine)

    orquestador.run(topic="ia", videos=VIDEOS_EJEMPLO, hasta="brain", remember=False)

    assert learning_engine.get_history() == []


def test_run_con_lista_de_videos_vacia_no_falla(tmp_path):
    orquestador = _orchestrator_aislado(tmp_path)
    resultado = orquestador.run(topic="tema sin resultados", videos=[], hasta="brain", remember=False)

    assert resultado["decision"]["decision"] == "NO_DECISION"
    assert resultado["ranked"] == []
