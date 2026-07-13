import json

from mh_core.database.json_memory_repository import JsonMemoryRepository
from mh_core.engines.memory_engine import MemoryEngine
from mh_core.models.memory import Memory

DECISION_EJEMPLO = {
    "decision": "PRODUCIR_INMEDIATAMENTE",
    "reason": "Alta oportunidad",
    "best_opportunity": {
        "title": "Video ganador",
        "channel": "Canal X",
        "url": "https://youtube.com/watch?v=abc",
        "mh_score": 88.5,
        "old_score": 70.0,
        "priority": "HIGH",
    },
}
PATTERNS_EJEMPLO = {"opportunity_level": "alta", "dominant_channel": "Canal X", "total_videos": 5}


def _engine(tmp_path, nombre="history.json"):
    repo = JsonMemoryRepository(tmp_path / nombre)
    return MemoryEngine(repository=repo), repo


# --- Persistencia entre "ejecuciones" (instancias nuevas) -----------------


def test_remember_persiste_entre_instancias_nuevas(tmp_path):
    engine1, _ = _engine(tmp_path)
    engine1.remember("tema de prueba", DECISION_EJEMPLO, PATTERNS_EJEMPLO)

    # Una instancia nueva, mismo archivo — simula una nueva "ejecución".
    engine2, _ = _engine(tmp_path)
    memorias = engine2.all()

    assert len(memorias) == 1
    assert memorias[0].topic == "tema de prueba"
    assert memorias[0].best_channel == "Canal X"


# --- Recuperar por tema -----------------------------------------------------


def test_recall_by_topic_encuentra_coincidencia_parcial(tmp_path):
    engine, _ = _engine(tmp_path)
    engine.remember("inteligencia artificial en la medicina", DECISION_EJEMPLO, PATTERNS_EJEMPLO)
    engine.remember("neurociencia del sueño", DECISION_EJEMPLO, PATTERNS_EJEMPLO)

    encontrados = engine.recall_by_topic("inteligencia artificial")

    assert len(encontrados) == 1
    assert "medicina" in encontrados[0].topic


def test_recall_by_topic_sin_coincidencias_devuelve_lista_vacia(tmp_path):
    engine, _ = _engine(tmp_path)
    engine.remember("neurociencia", DECISION_EJEMPLO, PATTERNS_EJEMPLO)

    assert engine.recall_by_topic("algo que no existe") == []


# --- Recientes ---------------------------------------------------------------


def test_recent_devuelve_mas_nuevo_primero(tmp_path):
    engine, _ = _engine(tmp_path)
    engine.remember("primero", DECISION_EJEMPLO, PATTERNS_EJEMPLO)
    engine.remember("segundo", {**DECISION_EJEMPLO, "decision": "OTRA_DECISION"}, PATTERNS_EJEMPLO)

    recientes = engine.recent(n=10)

    assert recientes[0].topic == "segundo"
    assert recientes[1].topic == "primero"


def test_recent_respeta_el_limite(tmp_path):
    engine, _ = _engine(tmp_path)
    for i in range(5):
        engine.remember(f"tema {i}", {**DECISION_EJEMPLO, "decision": f"D{i}"}, PATTERNS_EJEMPLO)

    assert len(engine.recent(n=2)) == 2


# --- Duplicados evidentes -----------------------------------------------------


def test_remember_evita_duplicado_evidente(tmp_path):
    engine, _ = _engine(tmp_path)
    engine.remember("mismo tema", DECISION_EJEMPLO, PATTERNS_EJEMPLO)
    engine.remember("mismo tema", DECISION_EJEMPLO, PATTERNS_EJEMPLO)  # mismo tema+decisión+URL

    assert len(engine.all()) == 1


def test_remember_no_bloquea_temas_distintos_aunque_misma_decision(tmp_path):
    engine, _ = _engine(tmp_path)
    engine.remember("tema A", DECISION_EJEMPLO, PATTERNS_EJEMPLO)
    engine.remember("tema B", DECISION_EJEMPLO, PATTERNS_EJEMPLO)

    assert len(engine.all()) == 2


# --- Archivo inexistente, vacío o corrupto ------------------------------------


def test_archivo_inexistente_no_falla(tmp_path):
    engine, _ = _engine(tmp_path, nombre="no_existe_todavia.json")
    assert engine.all() == []


def test_archivo_vacio_no_falla(tmp_path):
    ruta = tmp_path / "vacio.json"
    ruta.write_text("", encoding="utf-8")

    engine, _ = _engine(tmp_path, nombre="vacio.json")
    assert engine.all() == []


def test_archivo_corrupto_no_falla_y_se_respalda(tmp_path):
    ruta = tmp_path / "corrupto.json"
    ruta.write_text("{esto no es json valido", encoding="utf-8")

    engine, _ = _engine(tmp_path, nombre="corrupto.json")
    memorias = engine.all()

    assert memorias == []
    # Se debe haber creado un respaldo del contenido original, no perderlo.
    respaldos = list(tmp_path.glob("corrupto.corrupto-*.json.bak"))
    assert len(respaldos) == 1
    assert "esto no es json valido" in respaldos[0].read_text(encoding="utf-8")


def test_archivo_corrupto_permite_seguir_guardando(tmp_path):
    ruta = tmp_path / "corrupto2.json"
    ruta.write_text("[{roto", encoding="utf-8")

    engine, _ = _engine(tmp_path, nombre="corrupto2.json")
    engine.remember("tema nuevo tras corrupción", DECISION_EJEMPLO, PATTERNS_EJEMPLO)

    assert len(engine.all()) == 1


# --- Retrocompatibilidad con el formato ya guardado en producción ------------


def test_carga_formato_historico_real_sin_id_y_con_campos_variados(tmp_path):
    """Reproduce exactamente la forma de los registros reales ya guardados
    en database/learning/history.json (sin `id`, con opportunity_score
    en unos y mh_score/old_score en otros)."""
    ruta = tmp_path / "historico.json"
    registros_reales = [
        {
            "timestamp": "2026-06-30T01:17:59",
            "topic": "neurociencia: tema real",
            "decision": "PRODUCIR_CON_MEJORAS",
            "reason": "Oportunidad media",
            "best_video": "Video real",
            "best_channel": "AprendemosJuntos",
            "best_url": "https://www.youtube.com/watch?v=TjqrualxgkI",
            "opportunity_score": 51.89,
            "priority": "MEDIA",
            "patterns": {"total_videos": 5},
        },
        {
            "timestamp": "2026-07-02T15:37:41",
            "topic": "neurociencia: otro tema real",
            "decision": "PRODUCIR_CON_MEJORAS",
            "reason": "Oportunidad media",
            "best_video": "Otro video",
            "best_channel": "DrossRotzank",
            "best_url": "https://www.youtube.com/watch?v=LANJywmkHK4",
            "mh_score": 66.63,
            "old_score": 256.43322908687406,
            "priority": "MEDIUM",
            "opportunity_level": None,
            "dominant_channel": None,
            "patterns": {"total_videos": 5},
        },
    ]
    ruta.write_text(json.dumps(registros_reales, ensure_ascii=False), encoding="utf-8")

    engine, _ = _engine(tmp_path, nombre="historico.json")
    memorias = engine.all()

    assert len(memorias) == 2
    assert all(isinstance(m, Memory) for m in memorias)
    assert memorias[0].opportunity_score == 51.89
    assert memorias[1].mh_score == 66.63
    assert memorias[0].id is None  # los registros viejos no tenían id — no truena, queda None

    # El resumen (usado por Brain/Prediction) también debe funcionar sobre datos históricos reales.
    resumen = engine.summarize()
    assert resumen["total_memories"] == 2
