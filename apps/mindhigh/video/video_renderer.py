"""
VideoRenderer — arma el comando real de FFmpeg (fondo sólido + texto +
narración + subtítulos incrustados) y lo lanza como un proceso real
(`subprocess.Popen`, no `.run()`) para que VideoProductionEngine pueda
sostener la referencia al proceso y cancelarlo de verdad (terminate()),
no solo marcar una bandera que se revisa después.

No descarga ni inventa recursos visuales con copyright: el fondo es
generado por el propio FFmpeg (`lavfi color=...`), sin ninguna imagen
externa. Si en el futuro se agregan imágenes/clips propios, este es el
único archivo que habría que tocar.
"""
import subprocess
from pathlib import Path

RESOLUCION = "1280x720"
COLOR_FONDO = "0x0d1b2a"  # mismo tono oscuro que el panel — sin depender de ningún archivo externo


def _escapar_texto_para_filtro(texto: str) -> str:
    return texto.replace("\\", r"\\").replace("'", r"\'").replace(":", r"\:")


def _escapar_ruta_para_filtro(ruta: Path) -> str:
    """
    Bug real encontrado en Windows (no se ve en Linux/Mac, donde las
    rutas usan '/'): dentro de un argumento de filtro de FFmpeg, '\\'
    es el CARÁCTER DE ESCAPE — una ruta real de Windows como
    'C:\\Users\\...\\subtitulos.srt' se pasaba tal cual, y FFmpeg
    interpretaba cada '\\' como inicio de una secuencia de escape,
    comiéndose las diagonales enteras (el archivo terminaba
    literalmente ilegible: "C:UsersJoséLariosAppData...").

    Arreglo estándar de FFmpeg para esto: convertir '\\' a '/' primero
    (Windows acepta '/' igual de bien para abrir archivos) y solo
    entonces escapar ':' (la unidad, "C:") — así nunca hay una '\\'
    real que FFmpeg pueda malinterpretar.
    """
    texto = str(ruta).replace("\\", "/")
    texto = texto.replace(":", r"\:")
    texto = texto.replace("'", r"\'")
    return texto


class VideoRenderer:
    def renderizar(self, titulo: str, audio_path: Path, srt_path: Path, duracion: float, salida_path: Path) -> subprocess.Popen:
        salida_path.parent.mkdir(parents=True, exist_ok=True)

        titulo_escapado = _escapar_texto_para_filtro(titulo)
        srt_escapado = _escapar_ruta_para_filtro(srt_path)

        filtro_video = (
            f"drawtext=text='{titulo_escapado}':fontcolor=white:fontsize=42:"
            f"x=(w-text_w)/2:y=80:box=1:boxcolor=black@0.4:boxborderw=14,"
            f"subtitles='{srt_escapado}':force_style='FontSize=22,PrimaryColour=&HFFFFFF&'"
        )

        comando = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c={COLOR_FONDO}:s={RESOLUCION}:d={duracion:.3f}",
            "-i", str(audio_path),
            "-vf", filtro_video,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            str(salida_path),
        ]
        return subprocess.Popen(
            comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
