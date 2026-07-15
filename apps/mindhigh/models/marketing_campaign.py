"""Modelos de la primera capa de marketing privado de MindHigh."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CampaignObjective(str, Enum):
    ATRAER_VISITAS = "atraer_visitas"
    IMPULSAR_RESERVAS = "impulsar_reservas"
    LLENAR_HOSPEDAJE = "llenar_hospedaje"
    PROMOVER_CAMPING = "promover_camping"
    INFORMAR = "informar"
    REACTIVAR_CLIENTES = "reactivar_clientes"


class MarketingChannel(str, Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    INSTAGRAM_STORY = "instagram_story"
    WHATSAPP_STATUS = "whatsapp_status"
    GOOGLE_BUSINESS = "google_business"


class CampaignBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=3, max_length=120)
    objective: CampaignObjective
    audience: str = Field(min_length=3, max_length=240)
    main_emotion: str = Field(min_length=3, max_length=80)
    offer_focus: Literal["entrada", "camping", "hospedaje", "experiencia_general"]
    season: str = Field(min_length=2, max_length=80)
    channels: list[MarketingChannel] = Field(min_length=1)
    call_to_action: str = Field(
        default="Consulta la información vigente y solicita tu reservación en el portal oficial.",
        min_length=10,
        max_length=240,
    )
    approved_dynamic_facts: list[str] = Field(default_factory=list)


class ChannelContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: MarketingChannel
    headline: str
    body: str
    call_to_action: str
    hashtags: list[str] = Field(default_factory=list)


class MarketingCampaign(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    objective: CampaignObjective
    audience: str
    main_emotion: str
    offer_focus: str
    season: str
    knowledge_version: str
    requires_human_approval: bool = True
    dynamic_facts_used: tuple[str, ...] = ()
    contents: tuple[ChannelContent, ...]
