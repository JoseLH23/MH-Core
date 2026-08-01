"""Generación determinista y segura de campañas para EjiXhole.

Esta v1 no publica, no llama a modelos externos y no inventa precios,
disponibilidad, horarios ni promociones. Prepara borradores para aprobación humana.
"""

from __future__ import annotations

import re
from typing import Any

from apps.mindhigh.models.marketing_campaign import (
    CampaignBrief,
    ChannelContent,
    MarketingCampaign,
    MarketingChannel,
)
from mh_core.knowledge.ejixhole_knowledge import EjixholeKnowledgeSnapshot
from mh_core.knowledge.governed_bundle import GovernedKnowledgeBundle


class UnsafeMarketingClaimError(ValueError):
    """El contenido contiene un dato comercial dinámico no aprobado."""


class MissingMarketingEvidenceError(RuntimeError):
    """La campaña no puede demostrar qué conocimiento aprobado utilizó."""


class MarketingCampaignService:
    REQUIRED_DOCUMENT_IDS = ("brand", "marketing_strategy", "offer", "agent_rules")

    DYNAMIC_CLAIM_PATTERN = re.compile(
        r"(?:\$\s?\d|\b\d+(?:[.,]\d+)?\s?%|\b(?:precio|descuento|promoci[oó]n|"
        r"disponibilidad|disponible|horario|costo)\b)",
        re.IGNORECASE,
    )

    _FOCUS_MESSAGES = {
        "entrada": "vive un día entre naturaleza, agua y aventura",
        "camping": "convierte una escapada en una noche especial bajo el cielo de EjiXhole",
        "hospedaje": "descansa cerca de la naturaleza y disfruta la experiencia con más calma",
        "experiencia_general": "haz una pausa de la rutina y comparte una experiencia en la naturaleza",
    }

    def __init__(
        self,
        knowledge: EjixholeKnowledgeSnapshot | GovernedKnowledgeBundle,
        *,
        require_citations: bool = False,
    ) -> None:
        self.knowledge = knowledge
        self.require_citations = require_citations

    def _required_documents(self) -> tuple[Any, ...]:
        documents: list[Any] = []
        for document_id in self.REQUIRED_DOCUMENT_IDS:
            if isinstance(self.knowledge, GovernedKnowledgeBundle):
                document = self.knowledge.get(document_id)
                if document is None:
                    raise KeyError(document_id)
            else:
                document = self.knowledge.by_id(document_id)
            documents.append(document)
        return tuple(documents)

    def generate(self, brief: CampaignBrief) -> MarketingCampaign:
        evidence = self._required_documents()
        citations = tuple(
            citation
            for document in evidence
            if isinstance((citation := getattr(document, "citation_id", None)), str)
            and citation
        )
        if self.require_citations and len(citations) != len(evidence):
            raise MissingMarketingEvidenceError(
                "La campaña requiere una cita válida por cada documento esencial."
            )

        contents = tuple(self._content_for(channel, brief) for channel in brief.channels)
        self._validate_dynamic_claims(contents, brief.approved_dynamic_facts)

        return MarketingCampaign(
            name=brief.name,
            objective=brief.objective,
            audience=brief.audience,
            main_emotion=brief.main_emotion,
            offer_focus=brief.offer_focus,
            season=brief.season,
            knowledge_version=self.knowledge.knowledge_version,
            knowledge_document_ids=self.REQUIRED_DOCUMENT_IDS,
            knowledge_citations=citations,
            requires_human_approval=True,
            dynamic_facts_used=tuple(brief.approved_dynamic_facts),
            contents=contents,
        )

    def _content_for(self, channel: MarketingChannel, brief: CampaignBrief) -> ChannelContent:
        message = self._FOCUS_MESSAGES[brief.offer_focus]
        headline = self._headline(channel, brief)
        body = self._body(channel, brief, message)
        hashtags = [] if channel == MarketingChannel.GOOGLE_BUSINESS else [
            "#EjiXhole",
            "#Naturaleza",
            "#HuastecaPotosina",
        ]
        return ChannelContent(
            channel=channel,
            headline=headline,
            body=body,
            call_to_action=brief.call_to_action,
            hashtags=hashtags,
        )

    @staticmethod
    def _headline(channel: MarketingChannel, brief: CampaignBrief) -> str:
        if channel in {MarketingChannel.INSTAGRAM_STORY, MarketingChannel.WHATSAPP_STATUS}:
            return "Tu próxima escapada puede empezar aquí"
        if brief.offer_focus == "camping":
            return "Una noche diferente, rodeada de naturaleza"
        if brief.offer_focus == "hospedaje":
            return "Descansa, respira y disfruta EjiXhole"
        return "Hay lugares que te ayudan a salir de la rutina"

    @staticmethod
    def _body(channel: MarketingChannel, brief: CampaignBrief, message: str) -> str:
        if channel in {MarketingChannel.INSTAGRAM_STORY, MarketingChannel.WHATSAPP_STATUS}:
            return (
                f"En EjiXhole, {message}. Una idea para {brief.audience} "
                f"que buscan {brief.main_emotion}."
            )
        if channel == MarketingChannel.GOOGLE_BUSINESS:
            return (
                f"Descubre EjiXhole y {message}. Consulta en el portal oficial la información "
                "vigente antes de organizar tu visita."
            )
        return (
            f"A veces solo hace falta cambiar el ruido por naturaleza. En EjiXhole puedes {message}. "
            f"Esta campaña está pensada para {brief.audience} que buscan {brief.main_emotion}."
        )

    def _validate_dynamic_claims(
        self,
        contents: tuple[ChannelContent, ...],
        approved_facts: list[str],
    ) -> None:
        approved = [fact.casefold() for fact in approved_facts]
        for content in contents:
            combined = " ".join((content.headline, content.body, content.call_to_action))
            combined_folded = combined.casefold()
            for match in self.DYNAMIC_CLAIM_PATTERN.finditer(combined):
                claim = match.group(0).casefold()
                supported = any(claim in fact and fact in combined_folded for fact in approved)
                if not supported:
                    raise UnsafeMarketingClaimError(
                        f"Dato comercial dinámico no aprobado: {match.group(0)}"
                    )
