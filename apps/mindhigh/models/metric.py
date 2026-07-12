"""Una métrica capturada para una pieza de contenido ya publicada."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Metric(BaseModel):
    model_config = ConfigDict(extra="allow")

    content_id: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    simulated: bool = True
    captured_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
