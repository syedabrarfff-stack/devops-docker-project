from __future__ import annotations

import asyncio
import uuid
import logging
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query, Request
from app.api.v1.routes.auth import get_current_captain
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.models.communication import CommunicationChannel
from app.services.communication.ledger import communication_counts, recent_events, update_channel_status
from app.services.communication.whatsapp_transport import (
    configure_webhook,
    connect_qr,
    create_instance,
    evolution_status,
    logout_instance,
    process_inbound_webhook,
    restart_instance,
    send_media,
    send_text,
)
from app.services.outreach import gmail as email_service

router = APIRouter(tags=["Communication"], dependencies=[Depends(get_current_captain)])
communication_router = APIRouter(prefix="/communication", tags=["Communication"])
webhook_router = APIRouter(prefix="/webhooks", tags=["Communication Webhooks"])
logger = logging.getLogger(__name__)

SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
STATUS_TIMEOUT_SECONDS = 10.0


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
    number: str = Field(..., max_length=20)
    text: str = Field(..., min_length=1, max_length=4_096)
    lead_id: Optional[uuid.UUID] = None


class WhatsAppMediaIn(BaseModel):
    number: str = Field(..., max_length=20)
    media_url: str = Field(..., max_length=2_000)
    caption: str = Field(default="", max_length=1_024)
    media_type: str = Field(default="document", max_length=20)
    lead_id: Optional[uuid.UUID] = None


@communication_router.get("/status")
async def communication_status(
    request: Request,
    tenant_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    resolved = _resolve_tenant_id(request, tenant_id)
    email = await _email_status_with_timeout(db)
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
    whatsapp = await _whatsapp_status_with_timeout(db, resolved)
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
    return await _whatsapp_status_with_timeout(db, resolved)


@communication_router.get("/whatsapp/qr")
async def whatsapp_qr(number: Optional[str] = Query(None)) -> dict[str, Any]:
    return await connect_qr(number)


@communication_router.post("/whatsapp/instance/reset")
async def reset_whatsapp_instance() -> dict[str, Any]:
    """Log out and restart the Evolution instance to clear a stuck
    connectionState (e.g. hung in "connecting" from a half-completed QR
    handshake) so the next QR/pairing attempt starts from a clean slate."""
    logout_result = await logout_instance()
    restart_result = await restart_instance()
    return {
        "instance": settings.WHATSAPP_INSTANCE_NAME,
        "logout": logout_result,
        "restart": restart_result,
        "next_action": "Wait ~10 seconds, then request a fresh QR code or pairing code.",
    }


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
    background_tasks: BackgroundTasks,
    payload: dict[str, Any] = Body(default_factory=dict),
    tenant_id: Optional[uuid.UUID] = None,
) -> dict[str, Any]:
    resolved = _resolve_tenant_id(request, tenant_id)
    background_tasks.add_task(_process_whatsapp_webhook_background, resolved, payload)
    return {
        "accepted": True,
        "queued": True,
        "action": "queued_existing_pipeline",
        "architecture_route": [
            "WhatsApp",
            "Evolution API",
            "JARVIS webhook acknowledgement",
            "background Digital Twin / Decision Memory / Council / HIA processing",
        ],
    }


async def _process_whatsapp_webhook_background(
    tenant_id: uuid.UUID,
    payload: dict[str, Any],
) -> None:
    try:
        async with AsyncSessionLocal() as db:
            await process_inbound_webhook(db, tenant_id=tenant_id, payload=payload)
            await db.commit()
    except Exception:
        logger.exception("WhatsApp webhook background processing failed")


async def _email_status_with_timeout(db: AsyncSession) -> dict[str, Any]:
    try:
        return await asyncio.wait_for(
            email_service.email_delivery_status(db, validate_provider=True),
            timeout=STATUS_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("SES status check timed out")
        return {
            "engine": "ses_outreach",
            "provider": "ses",
            "configured": True,
            "connected": False,
            "send_method": "ses_raw_email",
            "send_mode": "blocked",
            "validation_error": "AWS SES status check timed out.",
            "blocker_code": "ses_status_timeout",
            "human_message": "AWS SES did not answer quickly enough for the dashboard.",
            "required_action": "Re-check SES from the AWS console or retry after AWS responds.",
            "setup_steps": [],
            "safety": {
                "unsubscribe_footer": True,
                "do_not_contact_gate": True,
                "business_hours_gate": True,
                "daily_cap_gate": True,
                "client_language_sanitizer": True,
            },
        }


async def _whatsapp_status_with_timeout(
    db: AsyncSession | None,
    tenant_id: uuid.UUID | None,
) -> dict[str, Any]:
    try:
        return await asyncio.wait_for(
            evolution_status(db, tenant_id),
            timeout=STATUS_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("WhatsApp Evolution status check timed out")
        return {
            "provider": "evolution",
            "instance": settings.WHATSAPP_INSTANCE_NAME or "jarvis-main",
            "configured": bool(settings.WHATSAPP_ENABLED and settings.EVOLUTION_API_KEY),
            "connected": False,
            "status": "blocked",
            "blocker_code": "evolution_status_timeout",
            "required_action": "Evolution API did not answer quickly enough; retry status or inspect the Evolution container.",
            "api_url": settings.EVOLUTION_API_URL,
            "public_url": settings.EVOLUTION_PUBLIC_URL,
            "webhook_url": settings.EVOLUTION_WEBHOOK_URL,
            "auto_reply_enabled": bool(settings.WHATSAPP_AUTO_REPLY_ENABLED),
            "auto_reply_min_confidence": float(settings.WHATSAPP_AUTO_REPLY_MIN_CONFIDENCE),
            "identity": settings.WHATSAPP_DISPLAY_IDENTITY or "Joseph David",
            "raw": {"ok": False, "status": "timeout"},
        }


router.include_router(communication_router)
# webhook_router is registered separately in app/api/v1/__init__.py, deliberately
# NOT nested under this module's `router` — that has
# dependencies=[Depends(get_current_captain)], and FastAPI merges a parent
# router's constructor-level dependencies into every route added via
# include_router, even nested ones. Evolution API's inbound webhook call
# (EVOLUTION_WEBHOOK_URL in docker-compose.yml) sends no auth headers at all,
# so nesting it here meant every real inbound WhatsApp message was being
# rejected with 401 — the endpoint was unreachable by its only legitimate
# caller.
#
# This endpoint has NO application-level auth of its own. It is only safe
# because nginx.conf explicitly blocks public access to this exact path
# (`location = /api/v1/webhooks/whatsapp { return 404; }`, ahead of the
# general /api/v1/webhooks/ proxy block) — an earlier version of this
# comment claimed nginx "never" proxied this path externally, which turned
# out to be false once nginx.conf grew a general webhook passthrough for
# Stripe/SES. Evolution reaches this route directly, container-to-container
# (http://backend:8000/...), never through nginx, so the block costs nothing.
# If that nginx location is ever removed, this endpoint MUST get real
# verification (shared secret header, IP allowlist, etc.) before that happens.
