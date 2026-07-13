"""Una notificación interna real — no un correo/WhatsApp simulado."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

NIVELES_VALIDOS = ("info", "warning", "success")


class Notification(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    message: str
    level: str = "info"

    topic: str | None = None
    success_probability: float | None = None
    confidence: str | None = None
    priority: str | None = None
    source: str = "automation_engine"

    # Prevención de duplicados: mismo dedup_key en una ventana reciente
    # no genera una segunda notificación (ver NotificationRules).
    dedup_key: str

    read: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
