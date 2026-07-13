from abc import ABC, abstractmethod

from mh_core.models.notification import Notification


class NotificationRepository(ABC):
    @abstractmethod
    def guardar(self, notificacion: Notification) -> Notification: ...

    @abstractmethod
    def listar(self, solo_no_leidas: bool = False) -> list[Notification]: ...

    @abstractmethod
    def obtener_por_id(self, notification_id: str) -> Notification | None: ...

    @abstractmethod
    def buscar_reciente_por_dedup_key(self, dedup_key: str, dentro_de_minutos: int) -> Notification | None: ...

    @abstractmethod
    def marcar_leida(self, notification_id: str) -> Notification | None: ...
