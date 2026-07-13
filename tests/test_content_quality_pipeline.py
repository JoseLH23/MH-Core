from apps.mindhigh.database.json_content_version_repository import JsonContentVersionRepository
from apps.mindhigh.models.content_piece import ContentPiece
from apps.mindhigh.services.content_quality_pipeline import ContentQualityPipeline

BRAIN_REPORT_EJEMPLO = {
    "executive_summary": {"topic": "ia en medicina", "final_recommendation": "PRODUCIR"},
    "reasoning": ["razón real"],
    "recommended_actions": ["acción real"],
}


class _GeneradorFijo:
    """Devuelve siempre la misma pieza de contenido (buena o mala, según se configure)."""

    def __init__(self, pieza_base: ContentPiece):
        self.pieza_base = pieza_base
        self.llamadas = 0

    def generar(self, brain_report, duration_target="short", style="informativo"):
        self.llamadas += 1
        # Nueva instancia cada vez (mismo contenido, id distinto) —
        # como haría un generador real.
        return self.pieza_base.model_copy(update={"id": f"c{self.llamadas}"})


class _GeneradorMejoraGradual:
    """Simula una regeneración real: el guion mejora en cada intento."""

    def __init__(self):
        self.llamadas = 0

    def generar(self, brain_report, duration_target="short", style="informativo"):
        self.llamadas += 1
        return ContentPiece(
            id=f"intento-{self.llamadas}",
            topic="ia en medicina",
            title="Título" if self.llamadas > 1 else "",  # el primer intento sale mal a propósito
            hook="¿Sabías esto?" if self.llamadas > 1 else "",
            script="Punto uno.\nPunto dos.\nPunto tres.\nCierre." if self.llamadas > 1 else "corto",
            description="Descripción real." if self.llamadas > 1 else "",
            hashtags=["#IA", "#Salud"] if self.llamadas > 1 else [],
            cta="Comenta." if self.llamadas > 1 else "",
        )


PIEZA_BUENA = ContentPiece(
    id="base",
    topic="ia en medicina",
    title="Cómo la IA está cambiando la medicina",
    hook="¿Sabías que esto ya pasa en hospitales reales?",
    script="Punto uno.\nPunto dos.\nPunto tres.\nCierre con CTA.",
    description="Video real sobre IA en medicina.",
    hashtags=["#IA", "#Salud", "#Medicina"],
    cta="Sígueme para más.",
)

PIEZA_MALA = ContentPiece(
    id="base-mala",
    topic="ia en medicina",
    title="",
    hook="",
    script="x",
    description="",
    hashtags=[],
    cta="",
)


def test_contenido_bueno_se_aprueba_en_el_primer_intento(tmp_path):
    generador = _GeneradorFijo(PIEZA_BUENA)
    repo = JsonContentVersionRepository(tmp_path / "content_versions.json")
    pipeline = ContentQualityPipeline(content_generator=generador, version_repository=repo)

    contenido, evaluacion, intentos = pipeline.generar_con_calidad(BRAIN_REPORT_EJEMPLO)

    assert evaluacion.aprobado is True
    assert generador.llamadas == 1
    assert len(intentos) == 1
    assert contenido.status == "aprobado"


def test_contenido_malo_regenera_hasta_mejorar(tmp_path):
    generador = _GeneradorMejoraGradual()
    repo = JsonContentVersionRepository(tmp_path / "content_versions.json")
    pipeline = ContentQualityPipeline(content_generator=generador, version_repository=repo, max_intentos=3)

    contenido, evaluacion, intentos = pipeline.generar_con_calidad(BRAIN_REPORT_EJEMPLO)

    assert generador.llamadas >= 2  # de verdad regeneró, no se quedó con el primer intento malo
    assert len(intentos) == generador.llamadas
    assert contenido.parent_id is not None or contenido.version > 1


def test_agota_intentos_devuelve_la_mejor_version_no_la_ultima_al_azar(tmp_path):
    generador = _GeneradorFijo(PIEZA_MALA)  # siempre mala — nunca va a aprobar
    repo = JsonContentVersionRepository(tmp_path / "content_versions.json")
    pipeline = ContentQualityPipeline(content_generator=generador, version_repository=repo, max_intentos=2)

    contenido, evaluacion, intentos = pipeline.generar_con_calidad(BRAIN_REPORT_EJEMPLO)

    assert generador.llamadas == 2  # se agotaron los intentos, no siguió indefinidamente
    assert evaluacion.aprobado is False
    assert contenido.status == "generado"  # honesto: no se marca como aprobado si no lo fue


def test_cada_version_se_guarda_en_el_repositorio(tmp_path):
    generador = _GeneradorMejoraGradual()
    repo = JsonContentVersionRepository(tmp_path / "content_versions.json")
    pipeline = ContentQualityPipeline(content_generator=generador, version_repository=repo, max_intentos=3)

    contenido, _, intentos = pipeline.generar_con_calidad(BRAIN_REPORT_EJEMPLO)

    historial = repo.historial(contenido.parent_id or contenido.id)
    assert len(historial) == len(intentos)


def test_verifica_originalidad_contra_el_video_investigado(tmp_path):
    brain_report_con_video = {
        "executive_summary": {
            "topic": "ia en medicina",
            "final_recommendation": "PRODUCIR",
            "recommended_video": "Cómo la IA está cambiando la medicina",  # idéntico al título generado
        },
    }
    generador = _GeneradorFijo(PIEZA_BUENA)
    repo = JsonContentVersionRepository(tmp_path / "content_versions.json")
    pipeline = ContentQualityPipeline(content_generator=generador, version_repository=repo, max_intentos=1)

    _, evaluacion, _ = pipeline.generar_con_calidad(brain_report_con_video)

    assert evaluacion.originalidad < 50  # título casi copiado del video real investigado
