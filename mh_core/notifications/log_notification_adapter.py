from mh_core.models.notification import Notification
from mh_core.notifications.notification_adapter import NotificationAdapter
from mh_core.utils.logger import logger


class LogNotificationAdapter(NotificationAdapter):
    """El único canal real disponible hoy: registra la notificación en
    el log real del proyecto (mismo archivo que todo lo demás)."""

    def enviar(self, notificacion: Notification) -> None:
        logger.info(
            f"NOTIFICACIÓN [{notificacion.level.upper()}] {notificacion.title} — {notificacion.message}"
        )
