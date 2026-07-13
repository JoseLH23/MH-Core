"""
Una métrica capturada para una pieza de contenido — real o simulada,
con separación EXPLÍCITA entre ambas (campo `simulated`, siempre
presente, nunca ambiguo).

Fase "aprendizaje a partir del rendimiento": se agregan los
indicadores reales pedidos (impresiones, retención, duración media,
conversiones) y validaciones — un valor negativo o un porcentaje fuera
de 0-100 es un error real de datos, no algo que deba guardarse tal cual.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Metric(BaseModel):
    model_config = ConfigDict(extra="allow")

    content_id: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    impressions: int = 0
    retention_percent: Optional[float] = None  # 0-100 — % promedio del video visto
    avg_view_duration_seconds: Optional[float] = None
    conversions: Optional[int] = None  # solo si existe algo que contar como conversión

    simulated: bool = True
    captured_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @field_validator("views", "likes", "comments", "impressions", "conversions")
    @classmethod
    def no_negativos(cls, v):
        if v is not None and v < 0:
            raise ValueError("las métricas de conteo no pueden ser negativas")
        return v

    @field_validator("retention_percent")
    @classmethod
    def retencion_en_rango(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError("retention_percent debe estar entre 0 y 100")
        return v

    @field_validator("avg_view_duration_seconds")
    @classmethod
    def duracion_no_negativa(cls, v):
        if v is not None and v < 0:
            raise ValueError("avg_view_duration_seconds no puede ser negativa")
        return v

    # --- Indicadores derivados (calculados, nunca guardados dos veces) ---

    @property
    def ctr_percent(self) -> Optional[float]:
        """Click-through rate real: vistas / impresiones. None si no
        hay impresiones registradas — no se puede calcular un CTR de
        la nada, y 0% sería un dato falso, no ausente."""
        if not self.impressions:
            return None
        return round(self.views / self.impressions * 100, 2)

    @property
    def engagement_rate_percent(self) -> Optional[float]:
        if not self.views:
            return None
        return round((self.likes + self.comments) / self.views * 100, 2)
