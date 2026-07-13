"""
ContentQualityPipeline — el flujo pedido:

    Generador (Gemini/Groq/plantillas) -> QualityEngine -> ¿aprobado?
        no -> regenerar (hasta max_intentos) -> ...
        sí -> listo

Cada versión (aprobada o no) se guarda con su evaluación —
ContentVersionRepository. Si se agotan los intentos sin aprobar, se
devuelve la MEJOR versión generada (mayor score_total), no la última
al azar — y se marca claramente que no llegó al umbral, en vez de
aparentar que sí se aprobó.
"""
from typing import Optional

from apps.mindhigh.database.content_version_repository import ContentVersionRepository
from apps.mindhigh.database.json_content_version_repository import JsonContentVersionRepository
from apps.mindhigh.models.content_piece import ContentPiece
from apps.mindhigh.models.quality_evaluation import QualityEvaluation
from apps.mindhigh.services.ai_content_generator import AIContentGenerator
from apps.mindhigh.services.quality_engine import QualityEngine
from mh_core.core.config import DATABASE_DIR
from mh_core.utils.logger import logger

VERSIONES_FILE = DATABASE_DIR / "mindhigh" / "content_versions.json"


class ContentQualityPipeline:
    def __init__(
        self,
        content_generator: Optional[AIContentGenerator] = None,
        quality_engine: Optional[QualityEngine] = None,
        version_repository: Optional[ContentVersionRepository] = None,
        max_intentos: int = 3,
    ):
        self.content_generator = content_generator or AIContentGenerator()
        self.quality_engine = quality_engine or QualityEngine()
        self.version_repository = version_repository or JsonContentVersionRepository(VERSIONES_FILE)
        self.max_intentos = max_intentos

    def generar_con_calidad(
        self, brain_report: dict, duration_target: str = "short", style: str = "informativo"
    ) -> tuple[ContentPiece, QualityEvaluation, list[QualityEvaluation]]:
        resumen = brain_report.get("executive_summary", {}) or {}
        video_original_titulo = resumen.get("recommended_video")

        contenido_base_id: Optional[str] = None
        mejor_contenido: Optional[ContentPiece] = None
        mejor_evaluacion: Optional[QualityEvaluation] = None
        todas_las_evaluaciones: list[QualityEvaluation] = []

        for intento in range(1, self.max_intentos + 1):
            contenido = self.content_generator.generar(brain_report, duration_target, style)
            contenido.version = intento
            if contenido_base_id is None:
                contenido_base_id = contenido.id
            else:
                contenido.parent_id = contenido_base_id

            evaluacion = self.quality_engine.evaluar(contenido, video_original_titulo)
            todas_las_evaluaciones.append(evaluacion)
            self.version_repository.guardar(contenido, evaluacion)

            logger.info(
                f"ContentQualityPipeline: intento {intento}/{self.max_intentos} — "
                f"score_total={evaluacion.score_total} (aprobado={evaluacion.aprobado})."
            )

            if mejor_evaluacion is None or evaluacion.score_total > mejor_evaluacion.score_total:
                mejor_contenido, mejor_evaluacion = contenido, evaluacion

            if evaluacion.aprobado:
                contenido.status = "aprobado"
                return contenido, evaluacion, todas_las_evaluaciones

        # Se agotaron los intentos sin aprobar — se devuelve la mejor
        # versión real generada, marcada honestamente como no aprobada.
        logger.warning(
            f"ContentQualityPipeline: ningún intento superó el umbral tras {self.max_intentos} intentos — "
            f"se devuelve la mejor versión (score_total={mejor_evaluacion.score_total})."
        )
        mejor_contenido.status = "generado"
        return mejor_contenido, mejor_evaluacion, todas_las_evaluaciones
