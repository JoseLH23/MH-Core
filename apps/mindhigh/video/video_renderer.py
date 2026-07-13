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


class VideoRenderer:
    def renderizar(self, titulo: str, audio_path: Path, srt_path: Path, duracion: float, salida_path: Path) -> subprocess.Popen:
        salida_path.parent.mkdir(parents=True, exist_ok=True)

        titulo_escapado = titulo.replace("'", r"\'").replace(":", r"\:")
        srt_escapado = str(srt_path).replace("'", r"\'").replace(":", r"\:")

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
        return subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
