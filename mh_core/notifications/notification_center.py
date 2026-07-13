"""
NotificationCenter — evalúa un brain_report real contra NotificationRules
y, si la oportunidad es lo bastante fuerte, crea y entrega una
notificación (con prevención de duplicados).
"""
from pathlib import Path
from typing import Optional

from mh_core.core.config import DATABASE_DIR
from mh_core.database.json_notification_repository import JsonNotificationRepository
from mh_core.database.notification_repository import NotificationRepository
from mh_core.models.notification import Notification
from mh_core.notifications.log_notification_adapter import LogNotificationAdapter
from mh_core.notifications.notification_adapter import NotificationAdapter
from mh_core.notifications.notification_rules import NotificationRules
from mh_core.utils.logger import logger

NOTIFICATIONS_FILE = DATABASE_DIR / "notifications" / "notifications.json"
VENTANA_DEDUP_MINUTOS = 60 * 6  # 6 horas — misma oportunidad no notifica dos veces el mismo día de trabajo


class NotificationCenter:
    def __init__(
        self,
        repository: Optional[NotificationRepository] = None,
        rules: Optional[NotificationRules] = None,
        adapters: Optional[list[NotificationAdapter]] = None,
    ):
        self.repository = repository or JsonNotificationRepository(NOTIFICATIONS_FILE)
        self.rules = rules or NotificationRules()
        self.adapters = adapters if adapters is not None else [LogNotificationAdapter()]

    def evaluar_oportunidad(self, brain_report: dict) -> Optional[Notification]:
        """Si el brain_report describe una oportunidad lo bastante
        fuerte (según NotificationRules) y no es un duplicado reciente,
        crea la notificación, la persiste y la entrega por los
        adaptadores configurados. Devuelve None si no aplicaba —
        nunca lanza por una oportunidad débil, eso es un caso normal."""
        resumen = brain_report.get("executive_summary", {}) or {}
        topic = resumen.get("topic")
        probabilidad = resumen.get("success_probability", 0) or 0
        confianza = resumen.get("confidence")
        recomendacion = resumen.get("final_recommendation")

        best = (brain_report.get("evidence", {}) or {}).get("decision", {}).get("best_opportunity", {}) or {}
        prioridad = best.get("priority")

        if not self.rules.cumple(probabilidad, confianza, prioridad):
            return None

        dedup_key = f"{topic}:{recomendacion}"
        duplicado = self.repository.buscar_reciente_por_dedup_key(dedup_key, VENTANA_DEDUP_MINUTOS)
        if duplicado is not None:
            logger.info(f"NotificationCenter: oportunidad para '{topic}' ya se notificó recientemente — se omite.")
            return None

        notificacion = Notification(
            title=f"Oportunidad fuerte detectada: {topic}",
            message=(
                f"Probabilidad de éxito {probabilidad:.0f}%, confianza {confianza}, "
                f"recomendación: {recomendacion}."
            ),
            level="success",
            topic=topic,
            success_probability=probabilidad,
            confidence=confianza,
            priority=prioridad,
            dedup_key=dedup_key,
        )

        guardada = self.repository.guardar(notificacion)
        for adaptador in self.adapters:
            adaptador.enviar(guardada)

        return guardada

    def listar(self, solo_no_leidas: bool = False) -> list[Notification]:
        return self.repository.listar(solo_no_leidas=solo_no_leidas)

    def obtener(self, notification_id: str) -> Optional[Notification]:
        return self.repository.obtener_por_id(notification_id)

    def marcar_leida(self, notification_id: str) -> Optional[Notification]:
        return self.repository.marcar_leida(notification_id)
