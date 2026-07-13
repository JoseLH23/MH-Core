"""
Memory Engine — Fase "Memory Engine persistente" del roadmap.

Capa de servicio sobre MemoryRepository (hoy: JsonMemoryRepository,
mañana potencialmente Postgres — MemoryEngine no lo sabe ni le
importa). Es lo que Brain/Prediction Engine deberían consultar para
"recordar", no el archivo JSON directamente.
"""
from pathlib import Path
from typing import Optional
from uuid import uuid4

from mh_core.core.config import HISTORY_FILE
from mh_core.database.json_memory_repository import JsonMemoryRepository
from mh_core.database.memory_repository import MemoryRepository
from mh_core.models.memory import Memory
from mh_core.utils.logger import logger


class MemoryEngine:
    def __init__(self, repository: Optional[MemoryRepository] = None):
        # Sin argumento, usa el archivo real del proyecto (mismo que
        # usaba LearningEngine antes) — comportamiento por defecto
        # sin cambios. Inyectar `repository` es lo que permite testear
        # sin tocar ese archivo real.
        self.repository = repository or JsonMemoryRepository(HISTORY_FILE)

    def remember(self, topic: str, decision: dict, patterns: dict) -> Memory:
        """Guarda un recuerdo estructurado. Si ya existe un duplicado evidente
        (mismo tema + misma decisión + misma URL ganadora), no lo vuelve a
        guardar — devuelve el existente y lo registra en el log."""
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
            logger.info(
                f"MemoryEngine: recuerdo duplicado evidente para el tema '{topic}' "
                "(mismo tema+decisión+URL) — no se guarda de nuevo."
            )
            return duplicado

        guardado = self.repository.guardar(memoria)
        logger.info(f"MemoryEngine: recuerdo nuevo guardado para el tema '{topic}'.")
        return guardado

    def recall_by_topic(self, topic: str) -> list[Memory]:
        return self.repository.buscar_por_tema(topic)

    def recent(self, n: int = 10) -> list[Memory]:
        return self.repository.recientes(n)

    def all(self) -> list[Memory]:
        return self.repository.listar()

    def summarize(self) -> dict:
        """Resumen del historial útil para Brain/Prediction Engine —
        misma forma que ya devolvía LearningEngine.summarize_learning(),
        para no romper a quien ya lo consume."""
        from collections import Counter

        memorias = self.all()

        if not memorias:
            return {
                "total_memories": 0,
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
