from __future__ import annotations

import json
from datetime import date

import pytest

from mh_core.knowledge.governed_bundle import (
    GovernedKnowledgeBundle,
    KnowledgeBundleError,
    git_blob_sha1,
)
from mh_core.knowledge.knowledge_engine import KnowledgeEngine


def _document(
    document_id: str,
    content: str,
    *,
    category: str = "sales",
    path: str | None = None,
) -> dict[str, str]:
    return {
        "id": document_id,
        "path": path or f"04-sales-and-service/{document_id}.md",
        "category": category,
        "document_version": "1.0.0",
        "citation_id": f"mhk://ejixhole/{document_id}/2026.07.3",
        "sensitivity": "internal",
        "source_type": "owner_approved",
        "source_reference": "fuente aprobada de prueba",
        "checksum": git_blob_sha1(content),
        "review_due_at": "2027-01-19",
        "content": content,
    }


def _bundle(*documents: dict[str, str]) -> dict:
    return {
        "schema_version": 1,
        "knowledge_version": "2026.07.3",
        "product": "EjiXhole",
        "governance": {
            "citation_required": True,
            "unknown_fact_behavior": "POR CONFIRMAR",
            "unapproved_behavior": "block",
            "expired_behavior": "block",
        },
        "documents": list(documents),
    }


def test_carga_busca_y_conserva_citas(tmp_path):
    payload = _bundle(
        _document("faq", "Camping disponible según fechas y capacidad."),
        _document(
            "brand",
            "La comunicación debe ser cercana, clara y honesta.",
            category="brand",
            path="01-brand/EJIXHOLE-BRAND-BIBLE.md",
        ),
    )
    bundle_path = tmp_path / "approved-bundle.json"
    bundle_path.write_text(json.dumps(payload), encoding="utf-8")

    engine = KnowledgeEngine()
    loaded = engine.load_governed_bundle(bundle_path)
    context = engine.get_governed_context("camping capacidad")

    assert loaded.knowledge_version == "2026.07.3"
    assert context["product"] == "EjiXhole"
    assert len(context["documents"]) == 1
    assert context["documents"][0]["id"] == "faq"
    assert context["documents"][0]["citation_id"].startswith("mhk://")
    assert engine.get_governed_document("brand") is not None


def test_falla_cerrado_si_no_hay_bundle():
    context = KnowledgeEngine().get_governed_context("horarios")

    assert context["documents"] == []
    assert context["unknown_fact_behavior"] == "POR CONFIRMAR"


def test_rechaza_borradores_y_contenido_alterado():
    draft = _document("draft", "Texto no aprobado", path="drafts/FAQ.md")
    with pytest.raises(KnowledgeBundleError, match="borradores"):
        GovernedKnowledgeBundle.from_dict(_bundle(draft))

    altered = _document("faq", "Contenido original")
    altered["content"] = "Contenido modificado"
    with pytest.raises(KnowledgeBundleError, match="Checksum"):
        GovernedKnowledgeBundle.from_dict(_bundle(altered))


def test_rechaza_gobierno_permisivo():
    payload = _bundle(_document("faq", "Contenido aprobado"))
    payload["governance"]["unapproved_behavior"] = "allow"

    with pytest.raises(KnowledgeBundleError, match="no aprobado"):
        GovernedKnowledgeBundle.from_dict(payload)


def test_rechaza_documento_con_revision_vencida():
    document = _document("faq", "Contenido aprobado")
    document["review_due_at"] = "2026-01-01"

    with pytest.raises(KnowledgeBundleError, match="requiere revisión"):
        GovernedKnowledgeBundle.from_dict(
            _bundle(document),
            today=date(2026, 8, 1),
        )


def test_rechaza_bundle_no_utf8(tmp_path):
    bundle_path = tmp_path / "approved-bundle.json"
    bundle_path.write_bytes(b"\xff\xfe")

    with pytest.raises(KnowledgeBundleError, match="No se pudo leer"):
        GovernedKnowledgeBundle.from_file(bundle_path)


def test_contadores_anteriores_siguen_funcionando(tmp_path):
    engine = KnowledgeEngine()
    engine.base_path = tmp_path

    engine.update_topic("camping")
    engine.update_topic("camping")
    engine.update_channel("facebook")

    assert engine.get_topics() == {"camping": 2}
    assert engine.get_channels() == {"facebook": 1}
