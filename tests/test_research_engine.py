import tempfile

from mh_core.engines.research_engine import ResearchEngine


class _YouTubeFalso:
    """Doble de YouTubeResearchEngine — no toca la red ni necesita API key real."""

    def __init__(self, resultado):
        self.resultado = resultado
        self.llamado_con = None

    def research(self, project):
        self.llamado_con = project
        return self.resultado


class _YouTubeQueFalla:
    def research(self, project):
        raise RuntimeError("falla simulada de la API de YouTube")


def test_get_topic_usa_youtube_cuando_hay_resultado_real():
    youtube_falso = _YouTubeFalso({"topic": "tema real de YouTube", "winner": {}, "top_videos": []})

    with tempfile.TemporaryDirectory() as tmp:
        engine = ResearchEngine(youtube_engine=youtube_falso, project_dir=tmp)
        topic = engine.get_topic()

    assert topic == "tema real de YouTube"
    assert youtube_falso.llamado_con is not None


def test_get_topic_cae_a_fallback_si_youtube_devuelve_none():
    """research() devuelve None cuando no hay YOUTUBE_API_KEY o no hubo resultados — caso honesto, no un error."""
    youtube_falso = _YouTubeFalso(None)

    with tempfile.TemporaryDirectory() as tmp:
        engine = ResearchEngine(youtube_engine=youtube_falso, project_dir=tmp)
        topic = engine.get_topic()

    assert topic in engine.topics


def test_get_topic_cae_a_fallback_si_youtube_lanza_excepcion():
    """La excepción real se captura y se registra — nunca un except/pass silencioso."""
    with tempfile.TemporaryDirectory() as tmp:
        engine = ResearchEngine(youtube_engine=_YouTubeQueFalla(), project_dir=tmp)
        topic = engine.get_topic()

    assert topic in engine.topics


def test_get_topic_siempre_devuelve_string_no_vacio():
    with tempfile.TemporaryDirectory() as tmp:
        engine = ResearchEngine(youtube_engine=_YouTubeFalso(None), project_dir=tmp)
        topic = engine.get_topic()

    assert isinstance(topic, str)
    assert len(topic) > 0
