"""Resultado de intentar publicar una pieza de contenido."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PublishResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    content_id: str
    platform: str
    simulated: bool
    url: str
    published_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
