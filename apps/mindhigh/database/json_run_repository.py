"""Implementación JSON de RunRepository — guardar() hace upsert por id
(una ejecución se actualiza varias veces mientras avanza de etapa)."""
import json
import shutil
from datetime import datetime
from pathlib import Path

from apps.mindhigh.database.run_repository import RunRepository
from apps.mindhigh.models.mindhigh_run import MindHighRun
from mh_core.utils.logger import logger


class JsonRunRepository(RunRepository):
    def __init__(self, path: Path):
        self.path = Path(path)

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
            logger.warning(f"JsonRunRepository: {self.path} tiene JSON inválido ({e}). Respaldado en {respaldo}.")
            return []
        return datos if isinstance(datos, list) else []

    def _guardar_crudo(self, registros: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")

    def guardar(self, run: MindHighRun) -> MindHighRun:
        registros = self._cargar_crudo()
        indice_existente = next((i for i, r in enumerate(registros) if r.get("id") == run.id), None)
        if indice_existente is not None:
            registros[indice_existente] = run.model_dump()
        else:
            registros.append(run.model_dump())
        self._guardar_crudo(registros)
        return run

    def obtener_por_id(self, run_id: str) -> MindHighRun | None:
        for r in self._cargar_crudo():
            if r.get("id") == run_id:
                return MindHighRun(**r)
        return None

    def listar(self, limit: int = 20) -> list[MindHighRun]:
        registros = self._cargar_crudo()
        return [MindHighRun(**r) for r in reversed(registros)][:limit]
