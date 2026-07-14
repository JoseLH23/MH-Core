import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from apps.mindhigh.database.json_video_render_repository import JsonVideoRenderRepository
from apps.mindhigh.video.subtitle_builder import construir_srt
from apps.mindhigh.video.video_production_engine import VideoProductionEngine


# --- SubtitleBuilder (real, determinista, sin FFmpeg) ----------------------


def test_srt_vacio_si_no_hay_texto():
    assert construir_srt("", 10.0) == ""


def test_srt_genera_bloques_con_formato_correcto():
    srt = construir_srt("Hola mundo esto es una prueba real de subtitulos generados", 10.0)

    assert "-->" in srt
    assert srt.strip().startswith("1")


def test_srt_reparte_tiempo_proporcional_a_palabras():
    # Primera línea con más palabras que la segunda -> debe durar más tiempo en pantalla.
    texto = "una dos tres cuatro cinco seis siete ocho nueve diez"  # 10 palabras, 2 líneas de 8/2
    srt = construir_srt(texto, duracion_total_segundos=10.0)

    lineas = [l for l in srt.split("\n\n") if l.strip()]
    assert len(lineas) == 2
    # La primera línea (8 palabras) debe cubrir más tiempo que la segunda (2 palabras).
    primer_fin = lineas[0].split("\n")[1].split(" --> ")[1]
    segundo_fin = lineas[1].split("\n")[1].split(" --> ")[1]
    assert primer_fin > "00:00:07"  # 8/10 del tiempo total, aprox 8s


# --- Dobles para no depender de pyttsx3/ffmpeg reales en la mayoría de tests --


class _TTSFalso:
    def __init__(self, falla=False):
        self.falla = falla
        self.llamadas = []

    def sintetizar(self, texto, ruta_salida):
        self.llamadas.append(texto)
        if self.falla:
            raise RuntimeError("TTS falló (simulado)")
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        ruta_salida.write_bytes(b"audio falso pero con contenido real de bytes")


class _RendererFalso:
    """No llama a FFmpeg real — crea un Popen de verdad pero con un
    comando trivial (`true`/`sleep`), para probar cancelación real sin
    depender de que FFmpeg esté instalado en el entorno de tests."""

    def __init__(self, falla=False, tardar_segundos=0):
        self.falla = falla
        self.tardar_segundos = tardar_segundos
        self.llamado_con = None

    def renderizar(self, titulo, audio_path, srt_path, duracion, salida_path):
        self.llamado_con = {"titulo": titulo, "salida": salida_path}
        if self.falla:
            comando = [sys.executable, "-c", "import sys; sys.exit(1)"]
        elif self.tardar_segundos:
            comando = [sys.executable, "-c", f"import time; time.sleep({self.tardar_segundos})"]
        else:
            salida_path.parent.mkdir(parents=True, exist_ok=True)
            comando = [sys.executable, "-c", f"open(r'{salida_path}', 'wb').write(b'mp4 falso')"]
        return subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def _medir_duracion_falsa(self, audio_path):
    return 5.0


def _engine(tmp_path, tts=None, renderer=None):
    engine = VideoProductionEngine(
        repository=JsonVideoRenderRepository(tmp_path / "renders.json"),
        tts_engine=tts or _TTSFalso(),
        renderer=renderer or _RendererFalso(),
        output_dir=tmp_path / "videos",
    )
    engine._medir_duracion = _medir_duracion_falsa.__get__(engine)
    return engine


def _esperar_estado_final(engine, render_id, timeout=5):
    limite = time.time() + timeout
    while time.time() < limite:
        render = engine.repository.obtener_por_id(render_id)
        if render.status in ("completed", "failed", "cancelled"):
            return render
        time.sleep(0.05)
    raise TimeoutError(f"El render {render_id} no terminó en {timeout}s")


# --- Flujo feliz -----------------------------------------------------------


def test_iniciar_render_completa_correctamente(tmp_path):
    engine = _engine(tmp_path)
    render = engine.iniciar_render("content-1", "Título real", "Un guion real de prueba corto.")

    final = _esperar_estado_final(engine, render.id)

    assert final.status == "completed"
    assert final.progress_percent == 100
    assert final.file_path is not None
    assert final.duration_seconds == 5.0


def test_render_queda_consultable_en_el_historial(tmp_path):
    engine = _engine(tmp_path)
    render = engine.iniciar_render("content-1", "Título", "Guion corto.")
    _esperar_estado_final(engine, render.id)

    historial = engine.repository.listar()
    assert len(historial) == 1
    assert historial[0].id == render.id


# --- Fallos por etapa, registrados, no silenciosos -------------------------


def test_fallo_en_tts_marca_render_como_failed(tmp_path):
    engine = _engine(tmp_path, tts=_TTSFalso(falla=True))
    render = engine.iniciar_render("content-1", "Título", "Guion.")

    final = _esperar_estado_final(engine, render.id)

    assert final.status == "failed"
    assert "TTS falló" in final.error


def test_fallo_en_ffmpeg_marca_render_como_failed(tmp_path):
    engine = _engine(tmp_path, renderer=_RendererFalso(falla=True))
    render = engine.iniciar_render("content-1", "Título", "Guion.")

    final = _esperar_estado_final(engine, render.id)

    assert final.status == "failed"
    assert "código" in final.error


# --- Cancelación real (proceso real terminado, no solo una bandera) --------


def test_cancelar_un_render_en_curso(tmp_path):
    engine = _engine(tmp_path, renderer=_RendererFalso(tardar_segundos=3))
    render = engine.iniciar_render("content-1", "Título", "Guion.")

    time.sleep(0.3)  # deja que llegue a la etapa de render real
    engine.cancelar(render.id)

    final = _esperar_estado_final(engine, render.id, timeout=5)
    assert final.status == "cancelled"


def test_cancelar_render_ya_completado_es_rechazado(tmp_path):
    engine = _engine(tmp_path)
    render = engine.iniciar_render("content-1", "Título", "Guion.")
    _esperar_estado_final(engine, render.id)

    with pytest.raises(ValueError, match="No se puede cancelar"):
        engine.cancelar(render.id)


def test_cancelar_render_inexistente_da_error_claro(tmp_path):
    engine = _engine(tmp_path)
    with pytest.raises(ValueError, match="no encontrado"):
        engine.cancelar("no-existe")


# --- Reintentos --------------------------------------------------------


def test_reintentar_un_render_fallido(tmp_path):
    tts = _TTSFalso(falla=True)
    engine = _engine(tmp_path, tts=tts)
    render = engine.iniciar_render("content-1", "Título", "Guion.")
    fallido = _esperar_estado_final(engine, render.id)
    assert fallido.status == "failed"

    tts.falla = False  # ahora sí funciona, como si se hubiera resuelto el problema real
    engine.reintentar(render.id)

    final = _esperar_estado_final(engine, render.id)
    assert final.status == "completed"
    assert final.attempts == 2


def test_reintentar_render_no_fallido_es_rechazado(tmp_path):
    engine = _engine(tmp_path)
    render = engine.iniciar_render("content-1", "Título", "Guion.")
    _esperar_estado_final(engine, render.id)  # queda "completed"

    with pytest.raises(ValueError, match="Solo se puede reintentar"):
        engine.reintentar(render.id)


# --- Smoke test REAL: TTS + FFmpeg de verdad, video muy corto --------------
# No usa dobles — prueba el pipeline real de punta a punta. Se mantiene
# deliberadamente corto (~3-4s de narración) para no volver lento el
# suite ni depender de hardware potente.


@pytest.mark.skipif(
    # shutil.which() es multiplataforma real (Windows/Linux/Mac) — el
    # bug real que reemplaza esto era `subprocess.run(["which", ...])`,
    # que solo existe en Linux/Mac. En Windows tronaba la COLECCIÓN
    # completa de tests con FileNotFoundError, no solo este test.
    shutil.which("ffmpeg") is None,
    reason="FFmpeg no está instalado en este entorno",
)
def test_smoke_render_real_corto_de_punta_a_punta(tmp_path):
    from apps.mindhigh.video.tts_engine import TTSEngine
    from apps.mindhigh.video.video_renderer import VideoRenderer

    try:
        import pyttsx3  # noqa: F401
    except ImportError:
        pytest.skip("pyttsx3 no está instalado en este entorno")

    engine = VideoProductionEngine(
        repository=JsonVideoRenderRepository(tmp_path / "renders.json"),
        tts_engine=TTSEngine(),
        renderer=VideoRenderer(),
        output_dir=tmp_path / "videos",
    )

    render = engine.iniciar_render(
        content_id="smoke-test",
        title="Prueba real corta",
        script="Esta es una prueba real y corta del motor de video.",
    )

    final = _esperar_estado_final(engine, render.id, timeout=60)

    assert final.status == "completed", f"Falló: {final.error}"
    assert final.file_path is not None

    ruta_video = Path(final.file_path)
    assert ruta_video.exists()
    assert ruta_video.stat().st_size > 1000  # un MP4 real pesa más que unos bytes vacíos
    assert final.duration_seconds is not None and final.duration_seconds > 0


# --- Bug real de Windows: escapado de rutas para el filtro de FFmpeg ------
# FFmpeg usa '\' como caracter de escape DENTRO de un argumento de
# filtro (-vf) — una ruta real de Windows ("C:\Users\...") se rompía
# ahi: cada '\' se comia el caracter siguiente, dejando una ruta
# ilegible tipo "C:UsersJoseLariosAppData...". Solo se ve en Windows
# (las rutas de Linux/Mac usan '/', que no tiene este problema).


def test_escapar_ruta_windows_no_deja_backslashes_sin_convertir():
    from pathlib import PureWindowsPath

    from apps.mindhigh.video.video_renderer import _escapar_ruta_para_filtro

    ruta = PureWindowsPath(r"C:\Users\José Larios\AppData\Local\Temp\subtitulos.srt")
    resultado = _escapar_ruta_para_filtro(ruta)

    assert "\\U" not in resultado  # ninguna diagonal seguida de letra (lo que FFmpeg mal interpretaba)
    assert "José" in resultado  # el texto real no se corrompe
    assert resultado.startswith("C\\:/")  # unidad escapada, resto con '/'


def test_escapar_ruta_linux_no_se_rompe():
    """En Linux/Mac (donde ya funcionaba) el comportamiento no debe cambiar."""
    from apps.mindhigh.video.video_renderer import _escapar_ruta_para_filtro

    ruta = Path("/tmp/render-123/subtitulos.srt")
    resultado = _escapar_ruta_para_filtro(ruta)

    assert resultado == "/tmp/render-123/subtitulos.srt"
