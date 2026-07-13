from pydantic import BaseModel, Field, HttpUrl


class Video(BaseModel):
    """
    Representa un video encontrado durante la investigación.
    """

    title: str = Field(..., description="Título del video")
    channel: str = Field(..., description="Canal del video")
    url: HttpUrl = Field(..., description="URL del video")

    views: int = Field(default=0, ge=0, description="Número total de vistas")
    views_per_day: float = Field(default=0, ge=0, description="Promedio de vistas por día")
    score: float = Field(default=0, ge=0, description="Puntuación calculada por MH Core")
    query: str = Field(default="", description="Consulta usada durante la investigación")
    engagement_rate: float = Field(default=0, ge=0, description="Engagement estimado")