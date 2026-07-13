"""
MindHighOrchestrator — Fase 4: flujo coordinado y observable.

    Investigación -> generación con calidad (incluye evaluación,
    regeneración y selección de la mejor versión, ya resuelto por
    ContentQualityPipeline) -> aprobación -> publicación simulada ->
    métricas -> notificación

Cada ejecución tiene un id real, una etapa actual, y guarda el
resultado de cada etapa completada — permitiendo reanudar sin repetir
trabajo cuando es seguro hacerlo (ver reanudar()).

No reemplaza a MindHighPipeline (que sigue siendo válido para un
"run and forget" simple) — este orchestrator es la versión observable
y reanudable, para cuando eso importa (ejecución programada, panel
visual, depuración de fallos).
"""
from typing import Optional

from apps.mindhigh.database.json_run_repository import JsonRunRepository
from apps.mindhigh.database.run_repository import RunRepository
from apps.mindhigh.engines.metrics_engine import MetricsEngine
from apps.mindhigh.models.content_piece import ContentPiece
from apps.mindhigh.models.mindhigh_run import MindHighRun, RunStage
from apps.mindhigh.models.quality_evaluation import QualityEvaluation
from apps.mindhigh.publishing.publisher_adapter import PublisherAdapter
from apps.mindhigh.publishing.simulated_publisher import SimulatedPublisher
from apps.mindhigh.services.content_quality_pipeline import ContentQualityPipeline
from mh_core.agents.research_agent import ResearchAgent
from mh_core.core.config import DATABASE_DIR
from mh_core.notifications.notification_center import NotificationCenter
from mh_core.utils.logger import logger

RUNS_FILE = DATABASE_DIR / "mindhigh" / "runs.json"


class MindHighOrchestrator:
    def __init__(
        self,
        research_agent: Optional[ResearchAgent] = None,
        quality_pipeline: Optional[ContentQualityPipeline] = None,
        publisher: Optional[PublisherAdapter] = None,
        metrics_engine: Optional[MetricsEngine] = None,
        notification_center: Optional[NotificationCenter] = None,
        run_repository: Optional[RunRepository] = None,
    ):
        self.research_agent = research_agent or ResearchAgent()
        self.quality_pipeline = quality_pipeline or ContentQualityPipeline()
        self.publisher = publisher or SimulatedPublisher()
        self.metrics_engine = metrics_engine or MetricsEngine()
        self.notification_center = notification_center or NotificationCenter()
        self.run_repository = run_repository or JsonRunRepository(RUNS_FILE)

    def ejecutar(self, remember: bool = True, duration_target: str = "short", style: str = "informativo") -> MindHighRun:
        run = MindHighRun(duration_target=duration_target, style=style)
        self.run_repository.guardar(run)
        logger.info(f"MindHighOrchestrator: run {run.id} iniciado.")

        try:
            investigacion = self.research_agent.run(remember=remember)
        except Exception as e:
            return self._fallar(run, RunStage.RESEARCH, e)

        run.stage_results["research"] = investigacion
        run.current_stage = RunStage.CONTENT_GENERATION.value
        self.run_repository.guardar(run)

        brain_report = investigacion.get("report") or {}
        contenido, evaluacion = self._generar_con_calidad(run, brain_report, duration_target, style)
        if contenido is None:
            return run  # ya se marcó failed dentro de _generar_con_calidad

        run.current_stage = RunStage.PUBLISHING.value
        self._publicar_y_medir(run, contenido, evaluacion)

        run.current_stage = RunStage.NOTIFICATION.value
        self._notificar(run, brain_report)

        run.current_stage = RunStage.COMPLETED.value
        run.status = "completed"
        from datetime import datetime

        run.completed_at = datetime.now().isoformat(timespec="seconds")
        self.run_repository.guardar(run)
        logger.info(f"MindHighOrchestrator: run {run.id} completado.")
        return run

    def reanudar(self, run_id: str) -> MindHighRun:
        """
        Reanuda una ejecución fallida — SOLO si es seguro: la
        investigación ya se guardó (research completado), así que
        reanudar nunca vuelve a llamar a YouTube ni crea un segundo
        recuerdo duplicado para el mismo tema. Si falló antes de
        terminar research, no hay nada seguro que reanudar — se pide
        ejecutar() de nuevo.
        """
        run = self.run_repository.obtener_por_id(run_id)
        if run is None:
            raise ValueError(f"Run '{run_id}' no encontrado.")
        if run.status != "failed":
            raise ValueError(f"Run '{run_id}' no está en estado 'failed' (está en '{run.status}') — nada que reanudar.")
        if "research" not in run.stage_results:
            raise ValueError(
                f"Run '{run_id}' falló antes de completar la investigación — no es seguro reanudar "
                "(reanudar aquí repetiría la investigación y podría duplicar el recuerdo). Ejecuta uno nuevo."
            )

        logger.info(f"MindHighOrchestrator: reanudando run {run.id} desde '{run.current_stage}'.")
        run.status = "running"
        run.errors = []  # se limpian los errores de este intento — no del historial completo del run
        self.run_repository.guardar(run)

        brain_report = run.stage_results["research"].get("report") or {}
        contenido, evaluacion = self._generar_con_calidad(run, brain_report, run.duration_target, run.style)
        if contenido is None:
            return run

        run.current_stage = RunStage.PUBLISHING.value
        self._publicar_y_medir(run, contenido, evaluacion)

        run.current_stage = RunStage.NOTIFICATION.value
        self._notificar(run, brain_report)

        run.current_stage = RunStage.COMPLETED.value
        run.status = "completed"
        from datetime import datetime

        run.completed_at = datetime.now().isoformat(timespec="seconds")
        self.run_repository.guardar(run)
        return run

    # --- pasos internos, cada uno guarda el run tras completarse -----------

    def _generar_con_calidad(self, run: MindHighRun, brain_report: dict, duration_target: str, style: str):
        try:
            contenido, evaluacion, intentos = self.quality_pipeline.generar_con_calidad(
                brain_report, duration_target, style
            )
        except Exception as e:
            self._fallar(run, RunStage.CONTENT_GENERATION, e)
            return None, None

        run.stage_results["content_generation"] = {
            "content": contenido.model_dump(),
            "evaluation": evaluacion.model_dump(),
            "attempts": len(intentos),
        }
        self.run_repository.guardar(run)
        return contenido, evaluacion

    def _publicar_y_medir(self, run: MindHighRun, contenido: ContentPiece, evaluacion: QualityEvaluation) -> None:
        if not evaluacion.aprobado:
            run.stage_results["publishing"] = None
            run.stage_results["metrics"] = None
            logger.warning(f"MindHighOrchestrator: run {run.id} — contenido no aprobado, no se publica.")
            self.run_repository.guardar(run)
            return

        try:
            publicacion = self.publisher.publicar(contenido)
            metrica = self.metrics_engine.record_initial(contenido.id, simulated=publicacion.simulated)
            run.stage_results["publishing"] = publicacion.model_dump()
            run.current_stage = RunStage.METRICS.value
            run.stage_results["metrics"] = metrica.model_dump()
            self.run_repository.guardar(run)
        except Exception as e:
            # Publicación/métricas fallidas no deben perder el
            # contenido ya generado y aprobado — se registra el error
            # pero el run NO se marca failed por esto (el trabajo
            # valioso, el contenido, ya está a salvo en stage_results).
            run.errors.append({"stage": "publishing", "error": str(e)})
            logger.warning(f"MindHighOrchestrator: run {run.id} — falló publicación/métricas: {e}")
            self.run_repository.guardar(run)

    def _notificar(self, run: MindHighRun, brain_report: dict) -> None:
        try:
            notificacion = self.notification_center.evaluar_oportunidad(brain_report)
            run.stage_results["notification"] = notificacion.model_dump() if notificacion else None
        except Exception as e:
            run.errors.append({"stage": "notification", "error": str(e)})
            logger.warning(f"MindHighOrchestrator: run {run.id} — falló notificación: {e}")
        self.run_repository.guardar(run)

    def _fallar(self, run: MindHighRun, etapa: RunStage, error: Exception) -> MindHighRun:
        run.status = "failed"
        run.errors.append({"stage": etapa.value, "error": str(error)})
        self.run_repository.guardar(run)
        logger.warning(f"MindHighOrchestrator: run {run.id} falló en '{etapa.value}' ({error}).")
        return run
