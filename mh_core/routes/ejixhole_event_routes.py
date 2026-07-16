"""Webhook privado para eventos firmados enviados por EjiXhole."""
from __future__ import annotations

import os

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from pydantic import ValidationError

from mh_core.integrations.ejixhole_events import (
    EVENT_CONTRACT_VERSION,
    MAX_EVENT_BODY_BYTES,
    EjixholeEventAuthenticationError,
    EjixholeEventConfigurationError,
    EjixholeEventConflictError,
    EjixholeEventEnvelope,
    EjixholeEventReceipt,
    EjixholeEventVerifier,
    SqliteEjixholeEventInbox,
)


router = APIRouter(prefix="/integrations/ejixhole", tags=["Integraciones"])


@router.post(
    "/events",
    response_model=EjixholeEventReceipt,
    status_code=status.HTTP_202_ACCEPTED,
)
async def receive_ejixhole_event(
    request: Request,
    response: Response,
    x_mh_event_id: str | None = Header(default=None, alias="X-MH-Event-Id"),
    x_mh_event_timestamp: str | None = Header(
        default=None, alias="X-MH-Event-Timestamp"
    ),
    x_mh_event_signature: str | None = Header(
        default=None, alias="X-MH-Event-Signature"
    ),
):
    body = await request.body()
    if len(body) > MAX_EVENT_BODY_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="El evento excede el tamaño máximo permitido.",
        )

    try:
        verified_event_id = EjixholeEventVerifier().verify(
            body,
            event_id=x_mh_event_id,
            timestamp=x_mh_event_timestamp,
            signature=x_mh_event_signature,
        )
    except EjixholeEventConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except EjixholeEventAuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    try:
        envelope = EjixholeEventEnvelope.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El contrato del evento es inválido.",
        ) from exc

    if envelope.event_id != verified_event_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-MH-Event-Id no coincide con el cuerpo firmado.",
        )

    try:
        result = SqliteEjixholeEventInbox(
            os.getenv("EJIXHOLE_EVENT_INBOX_PATH")
        ).store(envelope, body)
    except EjixholeEventConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    response.headers["X-MH-Event-Contract"] = EVENT_CONTRACT_VERSION
    response.headers["Cache-Control"] = "no-store"
    return EjixholeEventReceipt(
        event_id=envelope.event_id,
        duplicate=result.duplicate,
    )
