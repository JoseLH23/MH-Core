"""
Una pieza de contenido generada por MindHigh a partir de una
oportunidad real investigada por MH-Core.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ContentPiece(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    topic: str
    title: str
    script: str
    source_recommendation: Optional[str] = None  # decisión real de MH-Core que originó esto
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    status: str = "generado"  # generado | publicado | descartado
