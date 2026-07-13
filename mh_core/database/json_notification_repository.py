"""Implementación JSON de NotificationRepository — mismo manejo real
de archivo corrupto/vacío que el resto del proyecto."""
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from mh_core.database.notification_repository import NotificationRepository
from mh_core.models.notification import Notification
from mh_core.utils.logger import logger


class JsonNotificationRepository(NotificationRepository):
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
            logger.warning(
                f"JsonNotificationRepository: {self.path} tiene JSON inválido ({e}). "
                f"Respaldado en {respaldo}, se continúa con historial vacío."
            )
            return []
        return datos if isinstance(datos, list) else []

    def _guardar_crudo(self, registros: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(registros, ensure_ascii=False, indent=4), encoding="utf-8")

    def guardar(self, notificacion: Notification) -> Notification:
        registros = self._cargar_crudo()
        registros.append(notificacion.model_dump())
        self._guardar_crudo(registros)
        return notificacion

    def listar(self, solo_no_leidas: bool = False) -> list[Notification]:
        notificaciones = [Notification(**r) for r in self._cargar_crudo()]
        if solo_no_leidas:
            notificaciones = [n for n in notificaciones if not n.read]
        return list(reversed(notificaciones))  # más reciente primero

    def obtener_por_id(self, notification_id: str) -> Notification | None:
        for n in self.listar():
            if n.id == notification_id:
                return n
        return None

    def buscar_reciente_por_dedup_key(self, dedup_key: str, dentro_de_minutos: int) -> Notification | None:
        limite = datetime.now() - timedelta(minutes=dentro_de_minutos)
        for n in self.listar():
            if n.dedup_key == dedup_key and datetime.fromisoformat(n.created_at) >= limite:
                return n
        return None

    def marcar_leida(self, notification_id: str) -> Notification | None:
        registros = self._cargar_crudo()
        encontrada = False
        for r in registros:
            if r.get("id") == notification_id:
                r["read"] = True
                encontrada = True
        if not encontrada:
            return None
        self._guardar_crudo(registros)
        return self.obtener_por_id(notification_id)
