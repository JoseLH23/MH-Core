from apps.mindhigh.engines.metrics_engine import MetricsEngine
from apps.mindhigh.database.json_metrics_repository import JsonMetricsRepository
from apps.mindhigh.mindhigh_pipeline import MindHighPipeline
from apps.mindhigh.models.content_piece import ContentPiece
from apps.mindhigh.publishing.simulated_publisher import SimulatedPublisher
from apps.mindhigh.services.content_generator import ContentGenerator

BRAIN_REPORT_EJEMPLO = {
    "executive_summary": {
        "topic": "inteligencia artificial en medicina",
        "recommended_channel": "Canal X",
        "final_recommendation": "PRODUCIR",
    },
    "reasoning": ["El MH Score es alto.", "El riesgo estimado es bajo."],
    "recommended_actions": ["Producir cuanto antes.", "Usar un título con pregunta."],
}


class _ResearchAgentFalso:
    def __init__(self, brain_report):
        self.brain_report = brain_report

    def run(self, remember=True):
        return {"agent": "research", "action_taken": "PRODUCIR", "report": self.brain_report}


class _ResearchAgentQueFalla:
    def run(self, remember=True):
        raise RuntimeError("investigación falló (simulado)")


# --- ContentGenerator ---------------------------------------------------


def test_content_generator_produce_titulo_y_guion_reales():
    generador = ContentGenerator()
    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert isinstance(contenido, ContentPiece)
    assert "inteligencia artificial" in contenido.topic
    assert "MH Score es alto" in contenido.script
    assert "Producir cuanto antes" in contenido.script
    assert contenido.source_recommendation == "PRODUCIR"


def test_content_generator_sin_datos_no_falla():
    generador = ContentGenerator()
    contenido = generador.generar({})

    assert contenido.topic == "tema sin especificar"
    assert isinstance(contenido.title, str) and len(contenido.title) > 0


# --- SimulatedPublisher ----------------------------------------------------


def test_simulated_publisher_nunca_llama_red_real():
    generador = ContentGenerator()
    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    resultado = SimulatedPublisher(platform="youtube").publicar(contenido)

    assert resultado.simulated is True
    assert resultado.url.startswith("https://simulado.mindhigh.local/")
    assert resultado.content_id == contenido.id


# --- MetricsEngine / JsonMetricsRepository ---------------------------------


def test_metrics_engine_registra_metrica_inicial_en_cero(tmp_path):
    repo = JsonMetricsRepository(tmp_path / "metrics.json")
    engine = MetricsEngine(repository=repo)

    metrica = engine.record_initial("contenido-1", simulated=True)

    assert metrica.views == 0
    assert metrica.simulated is True

    persistidas = engine.for_content("contenido-1")
    assert len(persistidas) == 1


def test_metrics_engine_persiste_entre_instancias(tmp_path):
    repo1 = JsonMetricsRepository(tmp_path / "metrics.json")
    MetricsEngine(repository=repo1).record_initial("c1")

    repo2 = JsonMetricsRepository(tmp_path / "metrics.json")
    engine2 = MetricsEngine(repository=repo2)

    assert len(engine2.all()) == 1


def test_metrics_repository_archivo_corrupto_no_falla(tmp_path):
    ruta = tmp_path / "corrupto.json"
    ruta.write_text("{roto", encoding="utf-8")

    engine = MetricsEngine(repository=JsonMetricsRepository(ruta))
    assert engine.all() == []

    respaldos = list(tmp_path.glob("corrupto.corrupto-*.json.bak"))
    assert len(respaldos) == 1


# --- MindHighPipeline (end-to-end, todo inyectado) -------------------------


def test_pipeline_completo_conecta_todos_los_pasos(tmp_path):
    repo_metricas = JsonMetricsRepository(tmp_path / "metrics.json")
    pipeline = MindHighPipeline(
        research_agent=_ResearchAgentFalso(BRAIN_REPORT_EJEMPLO),
        publisher=SimulatedPublisher(),
        metrics_engine=MetricsEngine(repository=repo_metricas),
    )

    resultado = pipeline.run(remember=False)

    assert resultado["research"]["action_taken"] == "PRODUCIR"
    assert "inteligencia artificial" in resultado["content"]["topic"]
    assert resultado["publish_result"]["simulated"] is True
    assert resultado["initial_metric"]["content_id"] == resultado["content"]["id"]


def test_pipeline_propaga_error_real_de_investigacion(tmp_path):
    repo_metricas = JsonMetricsRepository(tmp_path / "metrics.json")
    pipeline = MindHighPipeline(
        research_agent=_ResearchAgentQueFalla(),
        metrics_engine=MetricsEngine(repository=repo_metricas),
    )

    try:
        pipeline.run()
        assert False, "debía propagar el error, no tragárselo"
    except RuntimeError:
        pass
