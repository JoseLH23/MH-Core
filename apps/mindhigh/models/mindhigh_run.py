"""Una ejecución completa del flujo de MindHigh, con seguimiento real por etapa."""
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class RunStage(str, Enum):
    RESEARCH = "research"
    CONTENT_GENERATION = "content_generation"
    PUBLISHING = "publishing"
    METRICS = "metrics"
    NOTIFICATION = "notification"
    COMPLETED = "completed"


class MindHighRun(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "running"  # running | completed | failed
    current_stage: str = RunStage.RESEARCH.value

    # Resultado real de cada etapa que sí se completó — permite
    # reanudar sin repetir trabajo ya hecho (ej. no volver a
    # investigar en YouTube si la investigación ya se guardó aquí).
    stage_results: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict] = Field(default_factory=list)

    duration_target: str = "short"
    style: str = "informativo"

    started_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    completed_at: Optional[str] = None
