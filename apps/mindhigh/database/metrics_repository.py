from abc import ABC, abstractmethod

from apps.mindhigh.models.metric import Metric


class MetricsRepository(ABC):
    @abstractmethod
    def guardar(self, metrica: Metric) -> Metric: ...

    @abstractmethod
    def por_contenido(self, content_id: str) -> list[Metric]: ...

    @abstractmethod
    def listar(self) -> list[Metric]: ...
