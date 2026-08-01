import json
from pathlib import Path
from typing import Any

from mh_core.knowledge.governed_bundle import (
    ApprovedKnowledgeDocument,
    GovernedKnowledgeBundle,
)


class KnowledgeEngine:

    def __init__(self):
        self.base_path = Path("mh_core/database/knowledge")
        self._governed_bundle: GovernedKnowledgeBundle | None = None

    def _load(self, filename):
        path = self.base_path / filename

        if not path.exists():
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, filename, data):
        path = self.base_path / filename
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def update_topic(self, topic):

        data = self._load("topics.json")

        data[topic] = data.get(topic, 0) + 1

        self._save("topics.json", data)

    def update_channel(self, channel):

        data = self._load("channels.json")

        data[channel] = data.get(channel, 0) + 1

        self._save("channels.json", data)

    def get_topics(self):
        return self._load("topics.json")

    def get_channels(self):
        return self._load("channels.json")

    def load_governed_bundle(self, path: str | Path) -> GovernedKnowledgeBundle:
        """Carga un bundle aprobado generado por MH-Knowledge."""
        bundle = GovernedKnowledgeBundle.from_file(path)
        self._governed_bundle = bundle
        return bundle

    def clear_governed_bundle(self) -> None:
        self._governed_bundle = None

    def get_governed_document(
        self, document_id: str
    ) -> ApprovedKnowledgeDocument | None:
        if self._governed_bundle is None:
            return None
        return self._governed_bundle.get(document_id)

    def get_governed_context(
        self,
        query: str,
        *,
        category: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Devuelve contexto citable o falla cerrado con POR CONFIRMAR."""
        if self._governed_bundle is None:
            return {
                "knowledge_version": None,
                "product": None,
                "unknown_fact_behavior": "POR CONFIRMAR",
                "documents": [],
            }
        return self._governed_bundle.context(
            query,
            category=category,
            limit=limit,
        )
