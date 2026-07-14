"""
VideoProductionEngine — orquesta TTS -> subtítulos reales -> render
FFmpeg, corriendo en un hilo de fondo (mismo patrón que AutomationEngine)
para que se pueda consultar progreso, cancelar y reintentar sin
bloquear al llamador.

Solo toma contenido YA aprobado por Quality Engine (lo decide quien
llama — este engine no vuelve a evaluar calidad, no duplica esa
responsabilidad).
"""
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from apps.mindhigh.database.json_video_render_repository import JsonVideoRenderRepository
from apps.mindhigh.database.video_render_repository import VideoRenderRepository
from apps.mindhigh.models.video_render import VideoRender
from apps.mindhigh.video.subtitle_builder import construir_srt
from apps.mindhigh.video.tts_engine import TTSEngine
from apps.mindhigh.video.video_renderer import VideoRenderer
from mh_core.core.config import DATABASE_DIR
from mh_core.utils.logger import logger

RENDERS_FILE = DATABASE_DIR / "mindhigh" / "video_renders.json"
VIDEOS_DIR = DATABASE_DIR / "mindhigh" / "videos"


class VideoProductionEngine:
    def __init__(
        self,
        repository: Optional[VideoRenderRepository] = None,
        tts_engine: Optional[TTSEngine] = None,
        renderer: Optional[VideoRenderer] = None,
        output_dir: Optional[Path] = None,
    ):
        self.repository = repository or JsonVideoRenderRepository(RENDERS_FILE)
        self.tts_engine = tts_engine or TTSEngine()
        self.renderer = renderer or VideoRenderer()
        self.output_dir = output_dir or VIDEOS_DIR

        self._procesos_activos: dict[str, subprocess.Popen] = {}
        self._cancelados: set[str] = set()

    def iniciar_render(self, content_id: str, title: str, script: str) -> VideoRender:
        render = VideoRender(content_id=content_id, title=title, script=script)
        self.repository.guardar(render)

        hilo = threading.Thread(target=self._ejecutar, args=(render.id,), daemon=True)
        hilo.start()
        return render

    def cancelar(self, render_id: str) -> VideoRender:
        render = self.repository.obtener_por_id(render_id)
        if render is None:
            raise ValueError(f"Render '{render_id}' no encontrado.")
        if render.status not in ("queued", "rendering"):
            raise ValueError(f"No se puede cancelar un render en estado '{render.status}'.")

        self._cancelados.add(render_id)
        proceso = self._procesos_activos.get(render_id)
        if proceso is not None:
            proceso.terminate()
            logger.info(f"VideoProductionEngine: proceso de FFmpeg de {render_id} terminado por cancelación.")
        return render

    def reintentar(self, render_id: str) -> VideoRender:
        render = self.repository.obtener_por_id(render_id)
        if render is None:
            raise ValueError(f"Render '{render_id}' no encontrado.")
        if render.status != "failed":
            raise ValueError(f"Solo se puede reintentar un render en estado 'failed' (está en '{render.status}').")

        self._cancelados.discard(render_id)
        render.status = "queued"
        render.error = None
        self.repository.guardar(render)

        hilo = threading.Thread(target=self._ejecutar, args=(render_id,), daemon=True)
        hilo.start()
        return render

    # --- ejecución real, en hilo de fondo ---------------------------------

    def _actualizar(self, render: VideoRender, step: str, progress: int) -> None:
        render.current_step = step
        render.progress_percent = progress
        self.repository.guardar(render)

    def _fallar(self, render: VideoRender, error: Exception) -> None:
        render.status = "failed"
        render.error = str(error)
        self.repository.guardar(render)
        logger.warning(f"VideoProductionEngine: render {render.id} falló ({error}).")

    def _medir_duracion(self, audio_path: Path) -> float:
        resultado = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        try:
            return float(resultado.stdout.strip())
        except ValueError as e:
            raise RuntimeError(f"No se pudo medir la duración real del audio generado: {resultado.stderr}") from e

    def _ejecutar(self, render_id: str) -> None:
        render = self.repository.obtener_por_id(render_id)
        render.status = "rendering"
        render.started_at = datetime.now().isoformat(timespec="seconds")
        render.attempts += 1
        self._actualizar(render, step="narracion", progress=10)

        carpeta = self.output_dir / render_id
        audio_path = carpeta / "narracion.wav"
        srt_path = carpeta / "subtitulos.srt"
        video_path = carpeta / "video.mp4"

        try:
            self.tts_engine.sintetizar(render.script, audio_path)
        except Exception as e:
            self._fallar(render, e)
            return

        if render_id in self._cancelados:
            self._marcar_cancelado(render)
            return

        try:
            duracion = self._medir_duracion(audio_path)
        except Exception as e:
            self._fallar(render, e)
            return

        self._actualizar(render, step="subtitulos", progress=40)
        srt_contenido = construir_srt(render.script, duracion)
        srt_path.parent.mkdir(parents=True, exist_ok=True)
        srt_path.write_text(srt_contenido, encoding="utf-8")

        self._actualizar(render, step="render", progress=60)
        try:
            proceso = self.renderer.renderizar(render.title, audio_path, srt_path, duracion, video_path)
        except Exception as e:
            self._fallar(render, e)
            return

        self._procesos_activos[render_id] = proceso
        salida, _ = proceso.communicate()
        self._procesos_activos.pop(render_id, None)

        if render_id in self._cancelados:
            self._marcar_cancelado(render)
            return

        if proceso.returncode != 0:
            self._fallar(render, RuntimeError(f"FFmpeg terminó con código {proceso.returncode}: {(salida or '')[-500:]}"))
            return

        render.status = "completed"
        render.file_path = str(video_path)
        render.srt_path = str(srt_path)
        render.duration_seconds = round(duracion, 2)
        render.progress_percent = 100
        render.current_step = "completed"
        render.completed_at = datetime.now().isoformat(timespec="seconds")
        self.repository.guardar(render)
        logger.info(f"VideoProductionEngine: render {render_id} completado ({video_path}).")

    def _marcar_cancelado(self, render: VideoRender) -> None:
        render.status = "cancelled"
        render.current_step = "cancelled"
        self.repository.guardar(render)
        self._cancelados.discard(render.id)
        logger.info(f"VideoProductionEngine: render {render.id} cancelado.")
