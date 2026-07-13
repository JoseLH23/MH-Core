"""
Modelo de un recuerdo (memoria) guardado por LearningEngine/MemoryEngine.

Existía este archivo pero estaba vacío (hallazgo de la auditoría) — se
llena aquí siguiendo el mismo estilo real del proyecto (Pydantic v2,
como Video/Opportunity), en vez de crear un archivo nuevo.

TOLERANTE A PROPÓSITO: el history.json real ya tiene 4 registros con
esquemas ligeramente distintos entre sí (algunos con `opportunity_score`,
otros con `mh_score`/`old_score`; campos a veces ausentes o en null).
Por eso los campos "de negocio" son Optional con default, y
`model_config` permite campos extra sin fallar — nunca se pierde un
registro histórico solo porque su forma exacta cambió con el tiempo.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class Memory(BaseModel):
    """Un recuerdo estructurado: qué tema se investigó, qué se decidió, y por qué."""

    model_config = ConfigDict(extra="allow")

    # `id` es nuevo (no existía en el formato viejo) — Optional para
    # que los 4 registros reales ya guardados carguen igual sin id.
    id: Optional[str] = Field(default=None, description="Identificador único del recuerdo, si existe")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    topic: Optional[str] = None
    decision: Optional[str] = None
    reason: Optional[str] = None

    best_video: Optional[str] = None
    best_channel: Optional[str] = None
    best_url: Optional[str] = None

    priority: Optional[str] = None
    opportunity_level: Optional[str] = None
    dominant_channel: Optional[str] = None

    # Nombres de score que ya conviven en los datos reales — se
    # conservan tal cual, no se renombran (retrocompatibilidad).
    mh_score: Optional[float] = None
    old_score: Optional[float] = None
    opportunity_score: Optional[float] = None

    patterns: dict[str, Any] = Field(default_factory=dict)

    def clave_duplicado(self) -> tuple:
        """Define qué cuenta como 'duplicado evidente' — mismo tema,
        misma decisión y misma URL ganadora. Ver MemoryEngine.remember()."""
        return (self.topic, self.decision, self.best_url)
