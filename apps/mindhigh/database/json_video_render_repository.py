"""Implementación JSON de VideoRenderRepository — upsert por id, mismo
manejo real de archivo corrupto que el resto del proyecto.

FIX DE CONCURRENCIA REAL: VideoProductionEngine actualiza el mismo
render varias veces desde un hilo de fondo (progreso, cambio de
estado) mientras la API/tests pueden leerlo al mismo tiempo desde el
hilo principal. Sin un lock, dos escrituras casi simultáneas podían
pisarse entre sí (lectura-modificación-escritura no es atómica) — se
detectó como una intermitencia real de tests bajo carga (suite
completo), no en aislamiento. Se agrega un lock por instancia."""
import json
import shutil
import threading
from datetime import datetime
from pathlib import Path

from apps.mindhigh.database.video_render_repository import VideoRenderRepository
from apps.mindhigh.models.video_render import VideoRender
from mh_core.utils.logger import logger


class JsonVideoRenderRepository(VideoRenderRepository):
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()

    def _cargar_crudo(self) -> list[dict]:
        if not self.path.exists():
            return []
        contenido = self.path.read_text(encoding="utf-8").strip()
        if not contenido:
            return []
        try:
            datos = json.loads(contenido)
        except json.JSONDecodeError as e:
            respaldo = self.path.with_name(
                f"{self.path.stem}.corrupto-{datetime.now().strftime('%Y%m%dT%H%M%S')}{self.path.suffix}.bak"
            )
            shutil.copy2(self.path, respaldo)
            logger.warning(f"JsonVideoRenderRepository: {self.path} JSON inválido ({e}). Respaldado en {respaldo}.")
            return []
        return datos if isinstance(datos, list) else []

    def _guardar_crudo(self, registros: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")

    def guardar(self, render: VideoRender) -> VideoRender:
        with self._lock:
            registros = self._cargar_crudo()
            indice = next((i for i, r in enumerate(registros) if r.get("id") == render.id), None)
            if indice is not None:
                registros[indice] = render.model_dump()
            else:
                registros.append(render.model_dump())
            self._guardar_crudo(registros)
        return render

    def obtener_por_id(self, render_id: str) -> VideoRender | None:
        with self._lock:
            for r in self._cargar_crudo():
                if r.get("id") == render_id:
                    return VideoRender(**r)
            return None

    def listar(self, limit: int = 20) -> list[VideoRender]:
        with self._lock:
            registros = self._cargar_crudo()
        return [VideoRender(**r) for r in reversed(registros)][:limit]
