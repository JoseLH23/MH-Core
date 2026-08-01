from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class KnowledgeBundleError(ValueError):
    """Indica que un bundle gobernado no es confiable o no cumple el contrato."""


@dataclass(frozen=True)
class ApprovedKnowledgeDocument:
    id: str
    path: str
    category: str
    document_version: str
    citation_id: str
    sensitivity: str
    source_type: str
    source_reference: str
    checksum: str
    review_due_at: str
    content: str

    def as_context(self) -> dict[str, str]:
        return {
            "id": self.id,
            "category": self.category,
            "document_version": self.document_version,
            "citation_id": self.citation_id,
            "source_type": self.source_type,
            "source_reference": self.source_reference,
            "content": self.content,
        }


def git_blob_sha1(content: str) -> str:
    raw = content.encode("utf-8")
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


class GovernedKnowledgeBundle:
    """Carga únicamente conocimiento aprobado, citable e íntegro."""

    REQUIRED_DOCUMENT_FIELDS = {
        "id",
        "path",
        "category",
        "document_version",
        "citation_id",
        "sensitivity",
        "source_type",
        "source_reference",
        "checksum",
        "review_due_at",
        "content",
    }

    def __init__(
        self,
        *,
        knowledge_version: str,
        product: str,
        unknown_fact_behavior: str,
        documents: list[ApprovedKnowledgeDocument],
    ) -> None:
        self.knowledge_version = knowledge_version
        self.product = product
        self.unknown_fact_behavior = unknown_fact_behavior
        self._documents = tuple(documents)
        self._by_id = {document.id: document for document in documents}

    @classmethod
    def from_file(cls, path: str | Path) -> "GovernedKnowledgeBundle":
        bundle_path = Path(path)
        try:
            payload = json.loads(bundle_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise KnowledgeBundleError(f"No se pudo leer el bundle gobernado: {exc}") from exc
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GovernedKnowledgeBundle":
        if not isinstance(payload, dict):
            raise KnowledgeBundleError("El bundle debe ser un objeto JSON.")
        if payload.get("schema_version") != 1:
            raise KnowledgeBundleError("schema_version del bundle debe ser 1.")

        knowledge_version = payload.get("knowledge_version")
        product = payload.get("product")
        if not isinstance(knowledge_version, str) or not knowledge_version.strip():
            raise KnowledgeBundleError("knowledge_version es obligatorio.")
        if not isinstance(product, str) or not product.strip():
            raise KnowledgeBundleError("product es obligatorio.")

        governance = payload.get("governance")
        if not isinstance(governance, dict):
            raise KnowledgeBundleError("governance es obligatorio.")
        if governance.get("citation_required") is not True:
            raise KnowledgeBundleError("El bundle debe exigir citas.")
        if governance.get("unapproved_behavior") != "block":
            raise KnowledgeBundleError("El conocimiento no aprobado debe bloquearse.")
        if governance.get("expired_behavior") != "block":
            raise KnowledgeBundleError("El conocimiento vencido debe bloquearse.")

        raw_documents = payload.get("documents")
        if not isinstance(raw_documents, list) or not raw_documents:
            raise KnowledgeBundleError("documents debe ser una lista no vacía.")

        documents: list[ApprovedKnowledgeDocument] = []
        seen_ids: set[str] = set()
        seen_citations: set[str] = set()

        for index, raw_document in enumerate(raw_documents):
            if not isinstance(raw_document, dict):
                raise KnowledgeBundleError(f"documents[{index}] debe ser un objeto.")
            missing = cls.REQUIRED_DOCUMENT_FIELDS - set(raw_document)
            if missing:
                raise KnowledgeBundleError(
                    f"documents[{index}] carece de: {', '.join(sorted(missing))}."
                )

            values: dict[str, str] = {}
            for field in cls.REQUIRED_DOCUMENT_FIELDS:
                value = raw_document.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise KnowledgeBundleError(
                        f"documents[{index}].{field} debe ser texto no vacío."
                    )
                values[field] = value

            document_path = Path(values["path"])
            if document_path.is_absolute() or ".." in document_path.parts:
                raise KnowledgeBundleError(
                    f"documents[{index}].path contiene una ruta no permitida."
                )
            if "drafts" in {part.casefold() for part in document_path.parts}:
                raise KnowledgeBundleError("El bundle no puede contener borradores.")
            if not values["citation_id"].startswith("mhk"):
                raise KnowledgeBundleError("citation_id debe pertenecer a MH-Knowledge.")
            if values["id"] in seen_ids:
                raise KnowledgeBundleError(f"ID duplicado: {values['id']}.")
            if values["citation_id"] in seen_citations:
                raise KnowledgeBundleError(
                    f"citation_id duplicado: {values['citation_id']}."
                )
            if git_blob_sha1(values["content"]) != values["checksum"].lower():
                raise KnowledgeBundleError(
                    f"Checksum inválido para el documento {values['id']}."
                )

            seen_ids.add(values["id"])
            seen_citations.add(values["citation_id"])
            documents.append(ApprovedKnowledgeDocument(**values))

        return cls(
            knowledge_version=knowledge_version,
            product=product,
            unknown_fact_behavior=str(
                governance.get("unknown_fact_behavior", "POR CONFIRMAR")
            ),
            documents=documents,
        )

    def list_documents(self, category: str | None = None) -> list[ApprovedKnowledgeDocument]:
        if category is None:
            return list(self._documents)
        normalized = category.casefold()
        return [
            document
            for document in self._documents
            if document.category.casefold() == normalized
        ]

    def get(self, document_id: str) -> ApprovedKnowledgeDocument | None:
        return self._by_id.get(document_id)

    def search(
        self,
        query: str,
        *,
        category: str | None = None,
        limit: int = 5,
    ) -> list[ApprovedKnowledgeDocument]:
        if limit < 1 or limit > 50:
            raise ValueError("limit debe estar entre 1 y 50.")
        terms = [term for term in query.casefold().split() if term]
        if not terms:
            return []

        ranked: list[tuple[int, ApprovedKnowledgeDocument]] = []
        for document in self.list_documents(category):
            searchable = " ".join(
                [
                    document.id,
                    document.category,
                    document.source_reference,
                    document.content,
                ]
            ).casefold()
            score = sum(searchable.count(term) for term in terms)
            if score:
                ranked.append((score, document))

        ranked.sort(key=lambda item: (-item[0], item[1].id))
        return [document for _, document in ranked[:limit]]

    def context(
        self,
        query: str,
        *,
        category: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        matches = self.search(query, category=category, limit=limit)
        return {
            "knowledge_version": self.knowledge_version,
            "product": self.product,
            "unknown_fact_behavior": self.unknown_fact_behavior,
            "documents": [document.as_context() for document in matches],
        }
