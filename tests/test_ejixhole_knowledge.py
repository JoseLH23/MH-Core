import json
from pathlib import Path

import pytest

from mh_core.knowledge.ejixhole_knowledge import (
    EjixholeKnowledgeLoader,
    KnowledgeConfigurationError,
    KnowledgeIntegrityError,
)


def _write_manifest(base: Path, documents: list[dict], **overrides) -> None:
    manifest = {
        "schema_version": 1,
        "knowledge_version": "test.1",
        "product": "EjiXhole",
        "dynamic_data_policy": {
            "prices": "backend",
            "availability": "backend",
        },
        "documents": documents,
    }
    manifest.update(overrides)
    (base / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )


def test_requiere_ruta_configurada(monkeypatch):
    monkeypatch.delenv("MH_KNOWLEDGE_PATH", raising=False)
    with pytest.raises(KnowledgeConfigurationError):
        EjixholeKnowledgeLoader()


def test_carga_snapshot_y_construye_contexto(tmp_path):
    (tmp_path / "brand.md").write_text("Tono cálido y natural.", encoding="utf-8")
    (tmp_path / "offer.md").write_text("Entrada, camping y hospedaje.", encoding="utf-8")
    _write_manifest(
        tmp_path,
        [
            {"id": "brand", "path": "brand.md", "category": "brand", "required": True},
            {"id": "offer", "path": "offer.md", "category": "business", "required": True},
        ],
    )

    snapshot = EjixholeKnowledgeLoader(tmp_path).load()

    assert snapshot.knowledge_version == "test.1"
    assert snapshot.dynamic_data_policy["prices"] == "backend"
    assert snapshot.by_id("brand").content == "Tono cálido y natural."
    context = snapshot.context(["brand", "offer"])
    assert "MH-Knowledge test.1" in context
    assert "Tono cálido y natural." in context
    assert "Entrada, camping y hospedaje." in context


def test_falla_si_falta_documento_obligatorio(tmp_path):
    _write_manifest(
        tmp_path,
        [{"id": "brand", "path": "missing.md", "category": "brand", "required": True}],
    )

    with pytest.raises(KnowledgeIntegrityError, match="obligatorio ausente"):
        EjixholeKnowledgeLoader(tmp_path).load()


def test_omite_documento_opcional_ausente(tmp_path):
    _write_manifest(
        tmp_path,
        [{"id": "learning", "path": "missing.md", "category": "learning", "required": False}],
    )

    snapshot = EjixholeKnowledgeLoader(tmp_path).load()
    assert snapshot.documents == ()


def test_rechaza_ruta_fuera_del_repositorio(tmp_path):
    _write_manifest(
        tmp_path,
        [{"id": "escape", "path": "../secret.txt", "category": "unsafe", "required": True}],
    )

    with pytest.raises(KnowledgeIntegrityError, match="Ruta fuera"):
        EjixholeKnowledgeLoader(tmp_path).load()


def test_rechaza_ids_duplicados(tmp_path):
    (tmp_path / "one.md").write_text("uno", encoding="utf-8")
    (tmp_path / "two.md").write_text("dos", encoding="utf-8")
    _write_manifest(
        tmp_path,
        [
            {"id": "same", "path": "one.md", "category": "test", "required": True},
            {"id": "same", "path": "two.md", "category": "test", "required": True},
        ],
    )

    with pytest.raises(KnowledgeIntegrityError, match="duplicado"):
        EjixholeKnowledgeLoader(tmp_path).load()


def test_rechaza_version_de_esquema_desconocida(tmp_path):
    _write_manifest(tmp_path, [], schema_version=99)

    with pytest.raises(KnowledgeIntegrityError, match="no soportada"):
        EjixholeKnowledgeLoader(tmp_path).load()


def test_contexto_falla_si_se_pide_documento_inexistente(tmp_path):
    (tmp_path / "brand.md").write_text("marca", encoding="utf-8")
    _write_manifest(
        tmp_path,
        [{"id": "brand", "path": "brand.md", "category": "brand", "required": True}],
    )

    snapshot = EjixholeKnowledgeLoader(tmp_path).load()
    with pytest.raises(KeyError):
        snapshot.context(["missing"])
