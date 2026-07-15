from __future__ import annotations

import pytest

from apps.mindhigh.models.marketing_campaign import (
    CampaignBrief,
    CampaignObjective,
    MarketingChannel,
)
from apps.mindhigh.services.marketing_campaign_service import (
    MarketingCampaignService,
    UnsafeMarketingClaimError,
)
from mh_core.knowledge.ejixhole_knowledge import (
    EjixholeKnowledgeSnapshot,
    KnowledgeDocument,
)


def _snapshot(*, include_offer: bool = True) -> EjixholeKnowledgeSnapshot:
    ids = ["brand", "marketing_strategy", "agent_rules"]
    if include_offer:
        ids.append("offer")
    documents = tuple(
        KnowledgeDocument(
            id=document_id,
            category="test",
            path=f"{document_id}.md",
            content=f"Contenido confirmado de {document_id}",
        )
        for document_id in ids
    )
    return EjixholeKnowledgeSnapshot(
        schema_version=1,
        knowledge_version="2026.07.1",
        product="EjiXhole",
        dynamic_data_policy={
            "prices": "backend",
            "availability": "backend",
            "schedules": "backend_or_human_confirmation",
            "promotions": "human_approval_required",
        },
        documents=documents,
    )


def _brief(**changes) -> CampaignBrief:
    values = {
        "name": "Escapada familiar de verano",
        "objective": CampaignObjective.IMPULSAR_RESERVAS,
        "audience": "familias que desean descansar juntas",
        "main_emotion": "tranquilidad y conexión",
        "offer_focus": "experiencia_general",
        "season": "verano",
        "channels": [
            MarketingChannel.FACEBOOK,
            MarketingChannel.INSTAGRAM_STORY,
            MarketingChannel.WHATSAPP_STATUS,
        ],
    }
    values.update(changes)
    return CampaignBrief(**values)


def test_genera_campana_multicanal_con_aprobacion_humana():
    campaign = MarketingCampaignService(_snapshot()).generate(_brief())

    assert campaign.name == "Escapada familiar de verano"
    assert campaign.knowledge_version == "2026.07.1"
    assert campaign.requires_human_approval is True
    assert [content.channel for content in campaign.contents] == [
        MarketingChannel.FACEBOOK,
        MarketingChannel.INSTAGRAM_STORY,
        MarketingChannel.WHATSAPP_STATUS,
    ]
    assert all("EjiXhole" in (content.body + content.headline) for content in campaign.contents)


def test_adapta_el_contenido_al_canal():
    campaign = MarketingCampaignService(_snapshot()).generate(_brief())
    facebook, story, status = campaign.contents

    assert len(facebook.body) > len(story.body)
    assert story.headline == "Tu próxima escapada puede empezar aquí"
    assert status.headline == story.headline


def test_no_inventa_precio_en_el_cta():
    brief = _brief(call_to_action="Reserva hoy por $100 por persona.")

    with pytest.raises(UnsafeMarketingClaimError, match="dinámico no aprobado"):
        MarketingCampaignService(_snapshot()).generate(brief)


def test_permita_dato_dinamico_solo_si_fue_aprobado_y_esta_en_el_texto():
    fact = "Precio $100 confirmado"
    brief = _brief(call_to_action=fact, approved_dynamic_facts=[fact])

    campaign = MarketingCampaignService(_snapshot()).generate(brief)

    assert campaign.dynamic_facts_used == (fact,)
    assert all(content.call_to_action == fact for content in campaign.contents)


def test_un_hecho_aprobado_no_autoriza_otro_precio():
    brief = _brief(
        call_to_action="Reserva hoy por $200.",
        approved_dynamic_facts=["Precio $100 confirmado"],
    )

    with pytest.raises(UnsafeMarketingClaimError):
        MarketingCampaignService(_snapshot()).generate(brief)


def test_requiere_documentos_esenciales_de_mh_knowledge():
    service = MarketingCampaignService(_snapshot(include_offer=False))

    with pytest.raises(KeyError, match="offer"):
        service.generate(_brief())


def test_google_business_no_usa_hashtags_y_remite_a_datos_vigentes():
    campaign = MarketingCampaignService(_snapshot()).generate(
        _brief(channels=[MarketingChannel.GOOGLE_BUSINESS])
    )

    content = campaign.contents[0]
    assert content.hashtags == []
    assert "información vigente" in content.body


def test_modelo_rechaza_campos_no_definidos():
    with pytest.raises(ValueError):
        _brief(campo_inventado="no permitido")
