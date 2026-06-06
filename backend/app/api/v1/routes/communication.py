from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.communication import CommunicationChannel
from app.services.communication.ledger import communication_counts, recent_events, update_channel_status
from app.services.communication.whatsapp_transport import (
    configure_webhook,
    connect_qr,
    create_instance,
    evolution_status,
    process_inbound_webhook,
    send_media,
    send_text,
)
from app.services.outreach import gmail as email_service

router = APIRouter(tags=["Communication"])
communication_router = APIRouter(prefix="/communication", tags=["Communication"])
webhook_router = APIRouter(prefix="/webhooks", tags=["Communication Webhooks"])

SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


def _resolve_tenant_id(request: Request, tenant_id: Optional[uuid.UUID] = None) -> uuid.UUID:
    header = request.headers.get("x-tenant-id")
    if tenant_id:
        return tenant_id
    if header:
        return uuid.UUID(header)
    if settings.JARVIS_DEFAULT_TENANT_ID:
        return uuid.UUID(str(settings.JARVIS_DEFAULT_TENANT_ID))
    return SYSTEM_TENANT_ID


class WhatsAppTextIn(BaseModel):
    number: str
    text: str
    lead_id: Optional[uuid.UUID] = None


class WhatsAppMediaIn(BaseModel):
    number: str
    media_url: str
    caption: str = ""
    media_type: str = "document"
    lead_id: Optional[uuid.UUID] = None


@communication_router.get("/status")
async def communication_status(
    request: Request,
    tenant_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    resolved = _resolve_tenant_id(request, tenant_id)
    email = await email_service.email_delivery_status(db, validate_provider=True)
    await update_channel_status(
        db,
        tenant_id=resolved,
        channel=CommunicationChannel.EMAIL,
        provider="ses",
        identity=email.get("from_email"),
        configured=bool(email.get("configured")),
        connected=bool(email.get("connected")),
        status=email.get("send_mode") or "unknown",
        blocker_code=email.get("blocker_code"),
        required_action=email.get("required_action"),
        details=email,
    )
    whatsapp = await evolution_status(db, resolved)
    counts = await communication_counts(db, resolved)
    return {
        "tenant_id": str(resolved),
        "constitutional_channels": ["AWS_SES", "BAHRAIN_WHATSAPP_BUSINESS"],
        "pipeline_unchanged": True,
        "architecture_route": {
            "email": "HERALD Outreach Generation -> AWS SES Email Delivery -> Reply Monitoring",
            "whatsapp": "WhatsApp -> Evolution API -> JARVIS -> Digital Twin -> Decision Memory -> Council Awareness -> HIA Persona",
        },
        "ses": email,
        "whatsapp": whatsapp,
        "counts": counts,
        "ready": bool(email.get("connected")) and bool(whatsapp.get("connected")),
    }


@communication_router.get("/events")
async def list_communication_events(
    request: Request,
    tenant_id: Optional[uuid.UUID] = None,
    channel: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    resolved = _resolve_tenant_id(request, tenant_id)
    events = await recent_events(db, resolved, channel=channel, limit=limit)
    return {"tenant_id": str(resolved), "events": events, "count": len(events)}


@communication_router.post("/whatsapp/instance")
async def create_whatsapp_instance() -> dict[str, Any]:
    result = await create_instance()
    webhook = await configure_webhook()
    return {
        "instance": settings.WHATSAPP_INSTANCE_NAME,
        "create": result,
        "webhook": webhook,
        "next_action": "Open QR pairing and scan from Bahrain WhatsApp Business linked devices.",
    }


@communication_router.get("/whatsapp/status")
async def whatsapp_status(
    request: Request,
    tenant_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    resolved = _resolve_tenant_id(request, tenant_id)
    return await evolution_status(db, resolved)


@communication_router.get("/whatsapp/qr")
async def whatsapp_qr() -> dict[str, Any]:
    return await connect_qr()


@communication_router.post("/whatsapp/webhook/configure")
async def whatsapp_configure_webhook() -> dict[str, Any]:
    return await configure_webhook()


@communication_router.post("/whatsapp/send-text")
async def whatsapp_send_text(
    body: WhatsAppTextIn,
    request: Request,
    tenant_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    resolved = _resolve_tenant_id(request, tenant_id)
    if not body.number or not body.text:
        raise HTTPException(status_code=400, detail="number and text are required")
    return await send_text(
        db,
        tenant_id=resolved,
        number=body.number,
        text=body.text,
        lead_id=body.lead_id,
        context={"source": "captain_control_room"},
    )


@communication_router.post("/whatsapp/send-media")
async def whatsapp_send_media(
    body: WhatsAppMediaIn,
    request: Request,
    tenant_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    resolved = _resolve_tenant_id(request, tenant_id)
    if not body.number or not body.media_url:
        raise HTTPException(status_code=400, detail="number and media_url are required")
    return await send_media(
        db,
        tenant_id=resolved,
        number=body.number,
        media_url=body.media_url,
        caption=body.caption,
        media_type=body.media_type,
        lead_id=body.lead_id,
    )


@webhook_router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    payload: dict[str, Any] = Body(default_factory=dict),
    tenant_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    resolved = _resolve_tenant_id(request, tenant_id)
    return await process_inbound_webhook(db, tenant_id=resolved, payload=payload)


router.include_router(communication_router)
router.include_router(webhook_router)
