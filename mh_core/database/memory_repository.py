"""
Contrato abstracto de almacenamiento de memorias — Fase Memory Engine.

Decisión de arquitectura (confirmada): JSON se mantiene como
almacenamiento local por ahora, pero MemoryEngine solo conoce esta
interfaz, nunca el detalle de "es un archivo JSON". Así, sustituir
JSON por PostgreSQL más adelante significa escribir una nueva clase
que implemente este mismo contrato (ej. PostgresMemoryRepository),
sin tocar MemoryEngine ni nada que lo use.

No se conecta con la base de datos de Ejixhole ni ninguna otra — MH-Core
permanece desacoplado, tal como se pidió.
"""
from abc import ABC, abstractmethod

from mh_core.models.memory import Memory


class MemoryRepository(ABC):
    @abstractmethod
    def guardar(self, memoria: Memory) -> Memory:
        """Persiste un recuerdo nuevo y lo devuelve (puede completar campos, ej. id)."""

    @abstractmethod
    def listar(self) -> list[Memory]:
        """Todos los recuerdos guardados, en el orden en que se guardaron."""

    @abstractmethod
    def buscar_por_tema(self, tema: str) -> list[Memory]:
        """Recuerdos cuyo `topic` coincide (comparación flexible, no exacta-mayúsculas)."""

    @abstractmethod
    def recientes(self, n: int = 10) -> list[Memory]:
        """Los `n` recuerdos más recientes, más nuevo primero."""

    @abstractmethod
    def buscar_duplicado(self, memoria: Memory) -> Memory | None:
        """Si ya existe un recuerdo con la misma clave_duplicado(), lo devuelve; si no, None."""
