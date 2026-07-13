"""
Una pieza de contenido generada por MindHigh a partir de una
oportunidad real investigada por MH-Core.

Fase "calidad del contenido": ahora incluye salida estructurada
completa (gancho, descripción, hashtags, CTA — antes solo título+guion),
más los campos de control de la fase (duración objetivo, estilo,
versión) para que Quality Engine pueda evaluar y decidir regenerar.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

DURACIONES_VALIDAS = ("short", "medio", "largo")  # short (<60s), medio (3-5min), largo (>5min)


class ContentPiece(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    topic: str

    # Salida estructurada real (antes solo existían title/script).
    title: str
    hook: str = ""
    script: str
    description: str = ""
    hashtags: list[str] = Field(default_factory=list)
    cta: str = ""

    # Parámetros de control que pidió la fase — configurables, no fijos.
    duration_target: str = "short"
    style: str = "informativo"

    # Control de versiones (Quality Engine puede regenerar).
    version: int = 1
    parent_id: Optional[str] = None  # id de la versión anterior, si esta es una regeneración

    source_recommendation: Optional[str] = None  # decisión real de MH-Core que originó esto
    source_video_title: Optional[str] = None  # para verificación de originalidad
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    status: str = "generado"  # generado | aprobado | descartado | publicado
