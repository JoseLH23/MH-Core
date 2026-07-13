from apps.mindhigh.agents.content_agent import ContentAgent
from apps.mindhigh.agents.mindhigh_agent_manager import crear_mindhigh_agent_manager
from apps.mindhigh.agents.video_agent import VideoAgent
from apps.mindhigh.database.json_content_version_repository import JsonContentVersionRepository
from apps.mindhigh.database.json_video_render_repository import JsonVideoRenderRepository
from apps.mindhigh.models.content_piece import ContentPiece
from apps.mindhigh.services.content_generator import ContentGenerator
from apps.mindhigh.services.content_quality_pipeline import ContentQualityPipeline
from apps.mindhigh.video.video_production_engine import VideoProductionEngine

BRAIN_REPORT_EJEMPLO = {
    "executive_summary": {"topic": "ia en medicina", "final_recommendation": "PRODUCIR"},
    "reasoning": ["razón real"],
    "recommended_actions": ["acción real"],
}


class _TTSFalso:
    def sintetizar(self, texto, ruta_salida):
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        ruta_salida.write_bytes(b"audio falso")


class _RendererFalso:
    def renderizar(self, titulo, audio_path, srt_path, duracion, salida_path):
        import subprocess

        salida_path.parent.mkdir(parents=True, exist_ok=True)
        return subprocess.Popen(
            ["python3", "-c", f"open(r'{salida_path}', 'wb').write(b'mp4 falso')"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )


# --- ContentAgent ------------------------------------------------------


def test_content_agent_genera_y_evalua(tmp_path):
    pipeline = ContentQualityPipeline(
        content_generator=ContentGenerator(),
        version_repository=JsonContentVersionRepository(tmp_path / "versions.json"),
    )
    agente = ContentAgent(quality_pipeline=pipeline)

    reporte = agente.run(BRAIN_REPORT_EJEMPLO)

    assert reporte["agent"] == "content"
    assert "content_id" in reporte
    assert reporte["action_taken"] in ("APROBADO", "NO_APROBADO_TRAS_REINTENTOS")


# --- VideoAgent ----------------------------------------------------------


def test_video_agent_rechaza_contenido_no_aprobado(tmp_path):
    repo_contenido = JsonContentVersionRepository(tmp_path / "versions.json")
    pieza = ContentPiece(id="c1", topic="x", title="t", hook="h", script="s", description="d", hashtags=[], cta="c", status="generado")
    repo_contenido.guardar(pieza, __import__("apps.mindhigh.models.quality_evaluation", fromlist=["QualityEvaluation"]).QualityEvaluation(content_id="c1", claridad=0, gancho=0, retencion=0, utilidad=0, originalidad=0))

    agente = VideoAgent(
        video_engine=VideoProductionEngine(repository=JsonVideoRenderRepository(tmp_path / "renders.json")),
        content_repository=repo_contenido,
    )

    reporte = agente.run(content_id="c1")
    assert reporte["action_taken"] == "RECHAZADO_NO_APROBADO"


def test_video_agent_inicia_render_de_contenido_aprobado(tmp_path):
    from apps.mindhigh.models.quality_evaluation import QualityEvaluation

    repo_contenido = JsonContentVersionRepository(tmp_path / "versions.json")
    pieza = ContentPiece(id="c1", topic="x", title="t", hook="h", script="s", description="d", hashtags=[], cta="c", status="aprobado")
    repo_contenido.guardar(pieza, QualityEvaluation(content_id="c1", claridad=90, gancho=90, retencion=90, utilidad=90, originalidad=90))

    motor = VideoProductionEngine(
        repository=JsonVideoRenderRepository(tmp_path / "renders.json"),
        tts_engine=_TTSFalso(),
        renderer=_RendererFalso(),
        output_dir=tmp_path / "videos",
    )
    agente = VideoAgent(video_engine=motor, content_repository=repo_contenido)

    reporte = agente.run(content_id="c1")

    assert reporte["action_taken"] == "RENDER_INICIADO"
    assert "render_id" in reporte


def test_video_agent_contenido_inexistente(tmp_path):
    agente = VideoAgent(
        video_engine=VideoProductionEngine(repository=JsonVideoRenderRepository(tmp_path / "renders.json")),
        content_repository=JsonContentVersionRepository(tmp_path / "versions.json"),
    )
    reporte = agente.run(content_id="no-existe")
    assert reporte["action_taken"] == "CONTENIDO_NO_ENCONTRADO"


# --- Manager compuesto ------------------------------------------------


def test_manager_compuesto_registra_los_3_agentes():
    manager = crear_mindhigh_agent_manager()
    assert set(manager.list_agents()) == {"research", "content", "video"}
