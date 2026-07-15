"""Carga local, versionada y segura de MH-Knowledge.

MH-Core no descarga el repositorio durante una petición ni confía en texto
remoto mutable. El repositorio MH-Knowledge debe estar clonado o montado y su
ruta se configura mediante ``MH_KNOWLEDGE_PATH``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class KnowledgeConfigurationError(RuntimeError):
    """La fuente de conocimiento no está configurada o es inválida."""


class KnowledgeIntegrityError(RuntimeError):
    """El manifiesto referencia contenido ausente o inseguro."""


@dataclass(frozen=True)
class KnowledgeDocument:
    id: str
    category: str
    path: str
    content: str


@dataclass(frozen=True)
class EjixholeKnowledgeSnapshot:
    schema_version: int
    knowledge_version: str
    product: str
    dynamic_data_policy: dict[str, str]
    documents: tuple[KnowledgeDocument, ...]

    def by_id(self, document_id: str) -> KnowledgeDocument:
        for document in self.documents:
            if document.id == document_id:
                return document
        raise KeyError(document_id)

    def context(self, document_ids: list[str] | None = None) -> str:
        selected = self.documents
        if document_ids is not None:
            requested = set(document_ids)
            selected = tuple(doc for doc in self.documents if doc.id in requested)
            missing = requested - {doc.id for doc in selected}
            if missing:
                raise KeyError(", ".join(sorted(missing)))

        sections = [
            f"# MH-Knowledge {self.knowledge_version}",
            f"Producto: {self.product}",
        ]
        for document in selected:
            sections.extend(
                [
                    "",
                    f"## {document.id} ({document.category})",
                    document.content.strip(),
                ]
            )
        return "\n".join(sections).strip()


class EjixholeKnowledgeLoader:
    MANIFEST_NAME = "manifest.json"

    def __init__(self, base_path: str | Path | None = None) -> None:
        configured = base_path or os.getenv("MH_KNOWLEDGE_PATH")
        if not configured:
            raise KnowledgeConfigurationError(
                "MH_KNOWLEDGE_PATH no está configurada. Apunta a un checkout local de MH-Knowledge."
            )
        self.base_path = Path(configured).expanduser().resolve()

    def load(self) -> EjixholeKnowledgeSnapshot:
        manifest_path = self.base_path / self.MANIFEST_NAME
        if not manifest_path.is_file():
            raise KnowledgeConfigurationError(
                f"No existe el manifiesto de conocimiento: {manifest_path}"
            )

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise KnowledgeIntegrityError("manifest.json no es legible o válido") from exc

        self._validate_manifest(manifest)
        documents: list[KnowledgeDocument] = []
        seen_ids: set[str] = set()

        for entry in manifest["documents"]:
            document_id = entry["id"]
            if document_id in seen_ids:
                raise KnowledgeIntegrityError(f"ID de documento duplicado: {document_id}")
            seen_ids.add(document_id)

            relative_path = Path(entry["path"])
            document_path = (self.base_path / relative_path).resolve()
            if not document_path.is_relative_to(self.base_path):
                raise KnowledgeIntegrityError(
                    f"Ruta fuera de MH-Knowledge rechazada: {relative_path}"
                )

            required = bool(entry.get("required", False))
            if not document_path.is_file():
                if required:
                    raise KnowledgeIntegrityError(
                        f"Documento obligatorio ausente: {relative_path}"
                    )
                continue

            documents.append(
                KnowledgeDocument(
                    id=document_id,
                    category=entry["category"],
                    path=relative_path.as_posix(),
                    content=document_path.read_text(encoding="utf-8"),
                )
            )

        return EjixholeKnowledgeSnapshot(
            schema_version=manifest["schema_version"],
            knowledge_version=manifest["knowledge_version"],
            product=manifest["product"],
            dynamic_data_policy=dict(manifest["dynamic_data_policy"]),
            documents=tuple(documents),
        )

    @staticmethod
    def _validate_manifest(manifest: Any) -> None:
        if not isinstance(manifest, dict):
            raise KnowledgeIntegrityError("El manifiesto debe ser un objeto JSON")
        if manifest.get("schema_version") != 1:
            raise KnowledgeIntegrityError("Versión de esquema no soportada")

        for field in (
            "knowledge_version",
            "product",
            "dynamic_data_policy",
            "documents",
        ):
            if field not in manifest:
                raise KnowledgeIntegrityError(f"Campo obligatorio ausente: {field}")

        if not isinstance(manifest["documents"], list):
            raise KnowledgeIntegrityError("documents debe ser una lista")

        for entry in manifest["documents"]:
            if not isinstance(entry, dict):
                raise KnowledgeIntegrityError("Cada documento debe ser un objeto")
            for field in ("id", "path", "category"):
                if not isinstance(entry.get(field), str) or not entry[field].strip():
                    raise KnowledgeIntegrityError(
                        f"Documento con campo inválido o ausente: {field}"
                    )
