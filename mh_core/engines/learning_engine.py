from typing import Optional

from mh_core.engines.memory_engine import MemoryEngine
from mh_core.knowledge.knowledge_engine import KnowledgeEngine


class LearningEngine:
    """
    Motor encargado de guardar historial y aprender patrones del historial.

    REFACTOR (fase Memory Engine): antes leía/escribía history.json
    directo con json.load/json.dump. Ahora delega todo el
    almacenamiento en MemoryEngine (que a su vez usa la abstracción
    MemoryRepository) — un solo lugar hace I/O de memorias, no dos.

    La API pública (remember/get_history/summarize_learning) y el
    comportamiento por defecto (sin argumentos, usa el archivo real
    del proyecto) NO cambiaron — research_service.py, dashboard_service.py
    y los tests existentes siguen funcionando igual.
    """

    def __init__(self, memory_engine: Optional[MemoryEngine] = None):
        self.name = "Learning Engine v2"
        self.memory_engine = memory_engine or MemoryEngine()

    def remember(self, topic, decision, patterns):
        memoria = self.memory_engine.remember(topic, decision, patterns)

        knowledge = KnowledgeEngine()
        knowledge.update_topic(topic)
        best_channel = memoria.best_channel
        if best_channel:
            knowledge.update_channel(best_channel)

        return memoria.model_dump()

    def get_history(self):
        return [m.model_dump() for m in self.memory_engine.all()]

    def summarize_learning(self):
        return self.memory_engine.summarize()
