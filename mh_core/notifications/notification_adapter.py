"""
Contrato de "canal de entrega" de una notificación — mismo patrón que
PublisherAdapter/MemoryRepository. Hoy solo existe LogNotificationAdapter
(real, no simulado: escribe al logger real del proyecto). NO se
implementa correo/WhatsApp/push porque no hay credenciales configuradas
— cuando existan, un EmailNotificationAdapter que implemente este
mismo contrato se conecta sin tocar NotificationCenter.
"""
from abc import ABC, abstractmethod

from mh_core.models.notification import Notification


class NotificationAdapter(ABC):
    @abstractmethod
    def enviar(self, notificacion: Notification) -> None: ...
