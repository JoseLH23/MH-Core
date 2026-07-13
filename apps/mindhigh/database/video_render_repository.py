from abc import ABC, abstractmethod

from apps.mindhigh.models.video_render import VideoRender


class VideoRenderRepository(ABC):
    @abstractmethod
    def guardar(self, render: VideoRender) -> VideoRender: ...

    @abstractmethod
    def obtener_por_id(self, render_id: str) -> VideoRender | None: ...

    @abstractmethod
    def listar(self, limit: int = 20) -> list[VideoRender]: ...
