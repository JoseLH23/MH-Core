from abc import ABC, abstractmethod

from apps.mindhigh.models.mindhigh_run import MindHighRun


class RunRepository(ABC):
    @abstractmethod
    def guardar(self, run: MindHighRun) -> MindHighRun: ...

    @abstractmethod
    def obtener_por_id(self, run_id: str) -> MindHighRun | None: ...

    @abstractmethod
    def listar(self, limit: int = 20) -> list[MindHighRun]: ...
