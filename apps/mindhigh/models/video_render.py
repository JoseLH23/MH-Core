"""Un render de video real — estado, progreso, archivo y metadatos."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

ESTADOS_RENDER = ("queued", "rendering", "completed", "failed", "cancelled")


class VideoRender(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content_id: str
    title: str
    script: str

    status: str = "queued"
    current_step: Optional[str] = None
    progress_percent: int = 0

    file_path: Optional[str] = None
    srt_path: Optional[str] = None
    duration_seconds: Optional[float] = None

    error: Optional[str] = None
    attempts: int = 0

    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
