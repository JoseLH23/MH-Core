from mh_core.database.json_memory_repository import JsonMemoryRepository
from mh_core.engines.memory_engine import MemoryEngine
from mh_core.memory.vector_store import VectorMemoryStore

DECISION_EJEMPLO = {"decision": "PRODUCIR", "best_opportunity": {"title": "x", "url": "https://y.com"}}


# --- VectorMemoryStore (unidad, Python puro) -----------------------------


def test_encuentra_documento_relacionado_por_significado_no_texto_exacto():
    tienda = VectorMemoryStore(
        {
            "1": "neurociencia del estrés y la ansiedad en el cerebro humano",
            "2": "receta de pastel de chocolate fácil y rápida",
        }
    )
    resultados = tienda.buscar_similares("salud mental y estrés", k=2)

    assert resultados[0][0] == "1"  # el de neurociencia gana, por palabras compartidas reales
    assert resultados[0][1] > 0


def test_documento_sin_relacion_no_aparece():
    tienda = VectorMemoryStore({"1": "kayak y cascadas en la selva", "2": "receta de pastel de chocolate"})
    resultados = tienda.buscar_similares("inteligencia artificial en medicina")

    assert resultados == []  # ninguna palabra en común real


def test_respeta_el_limite_k():
    tienda = VectorMemoryStore({str(i): f"tema numero {i} sobre tecnología" for i in range(10)})
    resultados = tienda.buscar_similares("tecnología", k=3)

    assert len(resultados) <= 3


def test_indice_vacio_no_falla():
    tienda = VectorMemoryStore({})
    assert tienda.buscar_similares("cualquier cosa") == []


# --- MemoryEngine.recall_by_similarity (integración real) -----------------


def test_recall_by_similarity_encuentra_tema_relacionado(tmp_path):
    repo = JsonMemoryRepository(tmp_path / "history.json")
    engine = MemoryEngine(repository=repo)

    engine.remember("neurociencia del estrés y la ansiedad", DECISION_EJEMPLO, {})
    engine.remember("receta de pastel de chocolate", DECISION_EJEMPLO, {})

    # La consulta comparte "estrés" con el primer tema, pero no es
    # substring de él (a diferencia de recall_by_topic, que exige
    # substring exacto) — esto es lo que TF-IDF real sí resuelve.
    resultados = engine.recall_by_similarity("el estrés afecta el cerebro humano")

    assert len(resultados) >= 1
    memoria_top, score = resultados[0]
    assert "estrés" in memoria_top.topic
    assert score > 0


def test_recall_by_similarity_sin_memorias_no_falla(tmp_path):
    repo = JsonMemoryRepository(tmp_path / "history.json")
    engine = MemoryEngine(repository=repo)

    assert engine.recall_by_similarity("cualquier tema") == []


def test_recall_by_similarity_distinto_de_recall_by_topic(tmp_path):
    """recall_by_topic exige que la consulta sea SUBSTRING del tema —
    recall_by_similarity encuentra coincidencias por palabras
    compartidas aunque la consulta no sea substring exacto. Confirma
    que son capacidades genuinamente distintas, no el mismo código con
    otro nombre."""
    repo = JsonMemoryRepository(tmp_path / "history.json")
    engine = MemoryEngine(repository=repo)
    engine.remember("neurociencia del estrés y la ansiedad", DECISION_EJEMPLO, {})

    consulta = "el estrés afecta el cerebro humano"  # comparte "estrés", no es substring del tema
    assert engine.recall_by_topic(consulta) == []
    assert len(engine.recall_by_similarity(consulta)) == 1
