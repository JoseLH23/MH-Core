import pytest

from apps.mindhigh.database.json_content_version_repository import JsonContentVersionRepository
from apps.mindhigh.database.json_metrics_repository import JsonMetricsRepository
from mh_core.database.json_notification_repository import JsonNotificationRepository
from apps.mindhigh.database.json_run_repository import JsonRunRepository
from apps.mindhigh.engines.metrics_engine import MetricsEngine
from apps.mindhigh.mindhigh_orchestrator import MindHighOrchestrator
from apps.mindhigh.publishing.simulated_publisher import SimulatedPublisher
from apps.mindhigh.services.content_generator import ContentGenerator
from apps.mindhigh.services.content_quality_pipeline import ContentQualityPipeline
from mh_core.notifications.notification_center import NotificationCenter

BRAIN_REPORT_EJEMPLO = {
    "executive_summary": {"topic": "ia en medicina", "final_recommendation": "PRODUCIR", "success_probability": 30},
    "reasoning": ["razón real"],
    "recommended_actions": ["acción real"],
}


class _ResearchAgentFalso:
    def __init__(self, brain_report=None, falla=False):
        self.brain_report = brain_report or BRAIN_REPORT_EJEMPLO
        self.falla = falla
        self.llamadas = 0

    def run(self, remember=True):
        self.llamadas += 1
        if self.falla:
            raise RuntimeError("investigación falló (simulado)")
        return {"agent": "research", "action_taken": "PRODUCIR", "report": self.brain_report}


def _orchestrator_aislado(tmp_path, research_agent=None):
    return MindHighOrchestrator(
        research_agent=research_agent or _ResearchAgentFalso(),
        quality_pipeline=ContentQualityPipeline(
            content_generator=ContentGenerator(),
            version_repository=JsonContentVersionRepository(tmp_path / "versions.json"),
        ),
        publisher=SimulatedPublisher(),
        metrics_engine=MetricsEngine(repository=JsonMetricsRepository(tmp_path / "metrics.json")),
        notification_center=NotificationCenter(repository=JsonNotificationRepository(tmp_path / "notifications.json")),
        run_repository=JsonRunRepository(tmp_path / "runs.json"),
    )


# --- Ejecución completa, feliz -----------------------------------------


def test_ejecutar_completa_todas_las_etapas(tmp_path):
    orquestador = _orchestrator_aislado(tmp_path)
    run = orquestador.ejecutar(remember=False)

    assert run.status == "completed"
    assert run.current_stage == "completed"
    assert "research" in run.stage_results
    assert "content_generation" in run.stage_results
    assert run.completed_at is not None


def test_cada_run_tiene_id_unico(tmp_path):
    orquestador = _orchestrator_aislado(tmp_path)
    run1 = orquestador.ejecutar(remember=False)
    run2 = orquestador.ejecutar(remember=False)

    assert run1.id != run2.id


def test_run_queda_consultable_por_id(tmp_path):
    orquestador = _orchestrator_aislado(tmp_path)
    run = orquestador.ejecutar(remember=False)

    encontrado = orquestador.run_repository.obtener_por_id(run.id)
    assert encontrado is not None
    assert encontrado.status == "completed"


# --- Fallo por etapa, con error registrado (no silencioso) ---------------


def test_fallo_en_investigacion_marca_run_como_failed(tmp_path):
    agente_que_falla = _ResearchAgentFalso(falla=True)
    orquestador = _orchestrator_aislado(tmp_path, research_agent=agente_que_falla)

    run = orquestador.ejecutar(remember=False)

    assert run.status == "failed"
    assert run.current_stage == "research"
    assert run.errors[0]["stage"] == "research"
    assert "investigación falló" in run.errors[0]["error"]
    assert "research" not in run.stage_results  # no llegó a completarse


# --- Reanudación segura ---------------------------------------------------


def test_reanudar_no_repite_la_investigacion(tmp_path):
    """Simula un run que falló DESPUÉS de completar research (ej. la
    generación falló) — reanudar debe usar el research ya guardado,
    sin volver a llamar al ResearchAgent."""
    agente = _ResearchAgentFalso()
    orquestador = _orchestrator_aislado(tmp_path, research_agent=agente)

    run = orquestador.ejecutar(remember=False)
    assert agente.llamadas == 1
    assert run.status == "completed"

    # Forzar un estado "failed" artificial, como si algo hubiera
    # fallado justo después de research, para probar reanudar().
    run.status = "failed"
    run.current_stage = "content_generation"
    orquestador.run_repository.guardar(run)

    reanudado = orquestador.reanudar(run.id)

    assert agente.llamadas == 1  # NO volvió a investigar
    assert reanudado.status == "completed"


def test_reanudar_run_sin_research_no_es_seguro(tmp_path):
    orquestador = _orchestrator_aislado(tmp_path)

    from apps.mindhigh.models.mindhigh_run import MindHighRun

    run_sin_research = MindHighRun(status="failed", current_stage="research")
    orquestador.run_repository.guardar(run_sin_research)

    with pytest.raises(ValueError, match="no es seguro reanudar"):
        orquestador.reanudar(run_sin_research.id)


def test_reanudar_run_que_no_esta_failed_rechazado(tmp_path):
    orquestador = _orchestrator_aislado(tmp_path)
    run = orquestador.ejecutar(remember=False)  # queda "completed"

    with pytest.raises(ValueError, match="no está en estado 'failed'"):
        orquestador.reanudar(run.id)


def test_reanudar_run_inexistente_da_error_claro(tmp_path):
    orquestador = _orchestrator_aislado(tmp_path)
    with pytest.raises(ValueError, match="no encontrado"):
        orquestador.reanudar("no-existe")


# --- No publica contenido no aprobado -------------------------------------


def test_contenido_no_aprobado_no_se_publica_ni_genera_metrica(tmp_path):
    class _GeneradorSiempreMalo:
        def generar(self, brain_report, duration_target="short", style="informativo"):
            from apps.mindhigh.models.content_piece import ContentPiece
            import uuid

            return ContentPiece(id=str(uuid.uuid4()), topic="x", title="", hook="", script="x", description="", hashtags=[], cta="")

    orquestador = MindHighOrchestrator(
        research_agent=_ResearchAgentFalso(),
        quality_pipeline=ContentQualityPipeline(
            content_generator=_GeneradorSiempreMalo(),
            version_repository=JsonContentVersionRepository(tmp_path / "versions.json"),
            max_intentos=1,
        ),
        publisher=SimulatedPublisher(),
        metrics_engine=MetricsEngine(repository=JsonMetricsRepository(tmp_path / "metrics.json")),
        notification_center=NotificationCenter(repository=JsonNotificationRepository(tmp_path / "notifications.json")),
        run_repository=JsonRunRepository(tmp_path / "runs.json"),
    )

    run = orquestador.ejecutar(remember=False)

    assert run.status == "completed"  # el run en sí no "falla" por esto — es un resultado válido
    assert run.stage_results["publishing"] is None
    assert run.stage_results["metrics"] is None
