import pytest

from apps.mindhigh.database.json_metrics_repository import JsonMetricsRepository
from apps.mindhigh.engines.performance_engine import PerformanceEngine
from apps.mindhigh.models.metric import Metric


def _engine(tmp_path) -> PerformanceEngine:
    return PerformanceEngine(repository=JsonMetricsRepository(tmp_path / "metrics.json"))


# --- Validaciones del modelo ------------------------------------------


def test_views_negativas_rechazadas():
    with pytest.raises(ValueError):
        Metric(content_id="c1", views=-5)


def test_retencion_fuera_de_rango_rechazada():
    with pytest.raises(ValueError):
        Metric(content_id="c1", retention_percent=150)


def test_duracion_negativa_rechazada():
    with pytest.raises(ValueError):
        Metric(content_id="c1", avg_view_duration_seconds=-1)


# --- Indicadores derivados ------------------------------------------------


def test_ctr_se_calcula_a_partir_de_vistas_e_impresiones():
    m = Metric(content_id="c1", views=50, impressions=1000)
    assert m.ctr_percent == 5.0


def test_ctr_none_sin_impresiones():
    m = Metric(content_id="c1", views=50, impressions=0)
    assert m.ctr_percent is None


def test_engagement_rate_se_calcula():
    m = Metric(content_id="c1", views=100, likes=10, comments=5)
    assert m.engagement_rate_percent == 15.0


# --- registrar_metrica_real -------------------------------------------


def test_registrar_metrica_real_queda_marcada_no_simulada(tmp_path):
    engine = _engine(tmp_path)
    metrica = engine.registrar_metrica_real("c1", views=1000, likes=50, impressions=5000, retention_percent=45.5)

    assert metrica.simulated is False
    assert metrica.views == 1000
    assert engine.ultima_metrica("c1").simulated is False


def test_registrar_metrica_real_persiste(tmp_path):
    ruta = tmp_path / "metrics.json"
    PerformanceEngine(repository=JsonMetricsRepository(ruta)).registrar_metrica_real("c1", views=100)

    engine2 = PerformanceEngine(repository=JsonMetricsRepository(ruta))
    assert engine2.ultima_metrica("c1").views == 100


# --- comparar_rendimiento -----------------------------------------------


def test_comparar_rendimiento_dos_versiones(tmp_path):
    engine = _engine(tmp_path)
    engine.registrar_metrica_real("v1", views=100, likes=5, impressions=1000)
    engine.registrar_metrica_real("v2", views=500, likes=50, impressions=1000)

    comparacion = engine.comparar_rendimiento("v1", "v2")

    assert comparacion["a"]["disponible"] is True
    assert comparacion["b"]["views"] == 500
    assert comparacion["b"]["ctr_percent"] > comparacion["a"]["ctr_percent"]


def test_comparar_rendimiento_sin_datos_no_falla(tmp_path):
    engine = _engine(tmp_path)
    comparacion = engine.comparar_rendimiento("no-existe-a", "no-existe-b")

    assert comparacion["a"]["disponible"] is False
    assert comparacion["b"]["disponible"] is False


# --- resumen_para_aprendizaje: separación real/simulado -------------------


def test_resumen_separa_reales_de_simuladas(tmp_path):
    engine = _engine(tmp_path)
    engine.registrar_metrica_real("c1", views=1000, impressions=10000)  # real, ctr 10%

    # Simulada — guardada directo con simulated=True (como haría MetricsEngine.record_initial)
    engine.repository.guardar(Metric(content_id="c2", views=0, simulated=True))

    resumen = engine.resumen_para_aprendizaje()

    assert resumen["real"]["total"] == 1
    assert resumen["simulated"]["total"] == 1
    assert resumen["real"]["avg_ctr_percent"] == 10.0


def test_resumen_sin_datos_no_falla(tmp_path):
    engine = _engine(tmp_path)
    resumen = engine.resumen_para_aprendizaje()

    assert resumen["real"]["total"] == 0
    assert resumen["simulated"]["total"] == 0


def test_resumen_filtra_por_content_ids(tmp_path):
    engine = _engine(tmp_path)
    engine.registrar_metrica_real("c1", views=100)
    engine.registrar_metrica_real("c2", views=200)

    resumen = engine.resumen_para_aprendizaje(content_ids=["c1"])
    assert resumen["real"]["total"] == 1
    assert resumen["real"]["total_views"] == 100
