"""
Memory Engine — Fase "Memory Engine persistente" del roadmap.

Capa de servicio sobre MemoryRepository. La implementación se selecciona por
configuración y los consumidores no conocen si usa JSON o SQL.
"""
from typing import Optional
from uuid import uuid4

from mh_core.core.config import HISTORY_FILE
from mh_core.database.memory_repository import MemoryRepository
from mh_core.database.memory_repository_factory import create_memory_repository
from mh_core.memory.vector_store import VectorMemoryStore
from mh_core.models.memory import Memory
from mh_core.utils.logger import logger


class MemoryEngine:
    def __init__(self, repository: Optional[MemoryRepository] = None):
        self.repository = repository or create_memory_repository(HISTORY_FILE)

    def remember(self, topic: str, decision: dict, patterns: dict) -> Memory:
        best = (decision or {}).get("best_opportunity") or {}
        memoria = Memory(
            id=str(uuid4()),
            topic=topic,
            decision=decision.get("decision") if decision else None,
            reason=decision.get("reason") if decision else None,
            best_video=best.get("title"),
            best_channel=best.get("channel"),
            best_url=best.get("url"),
            mh_score=best.get("mh_score"),
            old_score=best.get("old_score"),
            priority=best.get("priority"),
            opportunity_level=(patterns or {}).get("opportunity_level"),
            dominant_channel=(patterns or {}).get("dominant_channel"),
            patterns=patterns or {},
        )
        duplicado = self.repository.buscar_duplicado(memoria)
        if duplicado is not None:
            logger.info(f"MemoryEngine: recuerdo duplicado evidente para el tema '{topic}'.")
            return duplicado
        guardado = self.repository.guardar(memoria)
        logger.info(f"MemoryEngine: recuerdo nuevo guardado para el tema '{topic}'.")
        return guardado

    def recall_by_topic(self, topic: str) -> list[Memory]:
        return self.repository.buscar_por_tema(topic)

    def recall_by_similarity(self, consulta: str, k: int = 5) -> list[tuple[Memory, float]]:
        memorias = self.all()
        if not memorias:
            return []
        documentos = {m.id or str(i): (m.topic or "") for i, m in enumerate(memorias)}
        indice = VectorMemoryStore(documentos)
        resultados = indice.buscar_similares(consulta, k=k)
        memorias_por_id = {(m.id or str(i)): m for i, m in enumerate(memorias)}
        return [(memorias_por_id[doc_id], score) for doc_id, score in resultados]

    def recent(self, n: int = 10) -> list[Memory]:
        return self.repository.recientes(n)

    def all(self) -> list[Memory]:
        return self.repository.listar()

    def summarize(self) -> dict:
        from collections import Counter

        memorias = self.all()
        if not memorias:
            return {
                "total_memories": 0,
                "most_common_topics": [],
                "most_common_decisions": [],
                "most_common_channels": [],
                "most_common_priorities": [],
                "most_common_opportunity_levels": [],
                "average_mh_score": 0,
                "message": "Todavía no hay historial suficiente para aprender.",
            }
        topics = [m.topic for m in memorias if m.topic]
        decisions = [m.decision for m in memorias if m.decision]
        channels = [m.best_channel for m in memorias if m.best_channel]
        priorities = [m.priority for m in memorias if m.priority]
        opportunity_levels = [m.opportunity_level for m in memorias if m.opportunity_level]
        scores = [m.mh_score for m in memorias if isinstance(m.mh_score, (int, float))]
        return {
            "total_memories": len(memorias),
            "most_common_topics": Counter(topics).most_common(5),
            "most_common_decisions": Counter(decisions).most_common(5),
            "most_common_channels": Counter(channels).most_common(5),
            "most_common_priorities": Counter(priorities).most_common(5),
            "most_common_opportunity_levels": Counter(opportunity_levels).most_common(5),
            "average_mh_score": round(sum(scores) / len(scores), 2) if scores else 0,
        }
