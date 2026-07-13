"""
Implementación JSON de MemoryRepository — el ÚNICO lugar del proyecto
que ahora lee/escribe el archivo de historial (antes, LearningEngine
lo hacía directo con json.load/json.dump; se movió aquí para no tener
dos caminos de almacenamiento).

Ruta inyectable a propósito: nunca depende de una variable global de
"archivo de pruebas" — quien la construya decide el Path (real o
temporal).
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

from mh_core.database.memory_repository import MemoryRepository
from mh_core.models.memory import Memory
from mh_core.utils.logger import logger


class JsonMemoryRepository(MemoryRepository):
    def __init__(self, path: Path):
        self.path = Path(path)

    def _cargar_crudo(self) -> list[dict]:
        if not self.path.exists():
            return []

        contenido = self.path.read_text(encoding="utf-8").strip()
        if not contenido:
            # Archivo vacío — caso honesto, no un error, no hace falta backup.
            logger.info(f"JsonMemoryRepository: {self.path} está vacío, se trata como historial vacío.")
            return []

        try:
            datos = json.loads(contenido)
        except json.JSONDecodeError as e:
            # RIESGO REAL DE PÉRDIDA DE DATOS si se ignorara sin más:
            # se respalda el archivo corrupto ANTES de tratarlo como
            # vacío, para que nada se pierda en silencio.
            respaldo = self.path.with_name(
                f"{self.path.stem}.corrupto-{datetime.now().strftime('%Y%m%dT%H%M%S')}{self.path.suffix}.bak"
            )
            shutil.copy2(self.path, respaldo)
            logger.warning(
                f"JsonMemoryRepository: {self.path} tiene JSON inválido ({e}). "
                f"Se respaldó el contenido original en {respaldo} y se continúa con historial vacío."
            )
            return []

        if not isinstance(datos, list):
            logger.warning(
                f"JsonMemoryRepository: {self.path} no contiene una lista JSON (tipo real: {type(datos).__name__}). "
                "Se trata como historial vacío para no fallar, pero el archivo no se sobrescribe todavía."
            )
            return []

        return datos

    def _guardar_crudo(self, registros: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(registros, ensure_ascii=False, indent=4), encoding="utf-8")

    def listar(self) -> list[Memory]:
        return [Memory(**registro) for registro in self._cargar_crudo()]

    def guardar(self, memoria: Memory) -> Memory:
        registros = self._cargar_crudo()
        registros.append(memoria.model_dump(exclude_none=False))
        self._guardar_crudo(registros)
        return memoria

    def buscar_por_tema(self, tema: str) -> list[Memory]:
        tema_normalizado = tema.strip().lower()
        return [m for m in self.listar() if m.topic and tema_normalizado in m.topic.lower()]

    def recientes(self, n: int = 10) -> list[Memory]:
        memorias = self.listar()
        return list(reversed(memorias))[:n]

    def buscar_duplicado(self, memoria: Memory) -> Memory | None:
        clave = memoria.clave_duplicado()
        for existente in self.listar():
            if existente.clave_duplicado() == clave:
                return existente
        return None
