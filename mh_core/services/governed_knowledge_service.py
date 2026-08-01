from __future__ import annotations

import os
from pathlib import Path
from threading import RLock
from typing import Any

from mh_core.knowledge.governed_bundle import (
    GovernedKnowledgeBundle,
    KnowledgeBundleError,
)


class KnowledgeUnavailableError(RuntimeError):
    """El bundle no está configurado o no supera su validación."""


class GovernedKnowledgeService:
    def __init__(self, bundle_path: str | Path | None = None) -> None:
        self._explicit_path = Path(bundle_path) if bundle_path else None
        self._bundle: GovernedKnowledgeBundle | None = None
        self._loaded_path: Path | None = None
        self._loaded_mtime_ns: int | None = None
        self._last_error: str | None = None
        self._lock = RLock()

    def reset(self) -> None:
        """Limpia la caché para recargar configuración o rotar el bundle."""
        with self._lock:
            self._bundle = None
            self._loaded_path = None
            self._loaded_mtime_ns = None
            self._last_error = None

    def _configured_path(self) -> Path | None:
        if self._explicit_path is not None:
            return self._explicit_path
        raw = os.environ.get("MH_KNOWLEDGE_BUNDLE_PATH", "").strip()
        return Path(raw) if raw else None

    def _load(self) -> GovernedKnowledgeBundle:
        path = self._configured_path()
        if path is None:
            self._last_error = "MH_KNOWLEDGE_BUNDLE_PATH no está configurada."
            raise KnowledgeUnavailableError(self._last_error)

        try:
            resolved = path.expanduser().resolve(strict=True)
            mtime_ns = resolved.stat().st_mtime_ns
        except OSError as exc:
            self._last_error = "El bundle configurado no está disponible."
            raise KnowledgeUnavailableError(self._last_error) from exc

        with self._lock:
            if (
                self._bundle is not None
                and self._loaded_path == resolved
                and self._loaded_mtime_ns == mtime_ns
            ):
                return self._bundle

            try:
                bundle = GovernedKnowledgeBundle.from_file(resolved)
            except KnowledgeBundleError as exc:
                self._last_error = "El bundle configurado no es válido."
                raise KnowledgeUnavailableError(self._last_error) from exc

            self._bundle = bundle
            self._loaded_path = resolved
            self._loaded_mtime_ns = mtime_ns
            self._last_error = None
            return bundle

    def status(self) -> dict[str, Any]:
        path = self._configured_path()
        if path is None:
            return {
                "configured": False,
                "available": False,
                "knowledge_version": None,
                "product": None,
                "documents": 0,
                "error": "MH_KNOWLEDGE_BUNDLE_PATH no está configurada.",
            }

        try:
            bundle = self._load()
        except KnowledgeUnavailableError as exc:
            return {
                "configured": True,
                "available": False,
                "knowledge_version": None,
                "product": None,
                "documents": 0,
                "error": str(exc),
            }

        return {
            "configured": True,
            "available": True,
            "knowledge_version": bundle.knowledge_version,
            "product": bundle.product,
            "documents": len(bundle.list_documents()),
            "error": None,
        }

    def search(
        self,
        query: str,
        *,
        category: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        bundle = self._load()
        return bundle.context(query, category=category, limit=limit)
