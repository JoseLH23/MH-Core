"""Resultado de evaluar la calidad de una pieza de contenido generada."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

UMBRAL_APROBACION = 60  # de 100 — score_total mínimo para no regenerar


class QualityEvaluation(BaseModel):
    model_config = ConfigDict(extra="allow")

    content_id: str

    # Los 4 criterios pedidos explícitamente, cada uno 0-100.
    claridad: float
    gancho: float
    retencion: float
    utilidad: float

    # Verificación de originalidad respecto al video investigado —
    # 100 = totalmente distinto, 0 = prácticamente copiado.
    originalidad: float

    score_total: float = 0.0
    aprobado: bool = False
    razones: list[str] = Field(default_factory=list)

    evaluated_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def model_post_init(self, __context) -> None:
        if self.score_total == 0.0:
            self.score_total = round(
                (self.claridad + self.gancho + self.retencion + self.utilidad + self.originalidad) / 5, 1
            )
        if not self.aprobado:
            self.aprobado = self.score_total >= UMBRAL_APROBACION
