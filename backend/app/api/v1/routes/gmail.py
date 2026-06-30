"""JARVIS executive email operations center."""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.api.v1.routes.auth import get_current_captain
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.services.outreach.gmail import email_delivery_status, send_client_email
from app.services.outreach.gmail_inbox import fetch_new_emails, get_inbox, get_inbox_stats, mark_read

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gmail", tags=["gmail"], dependencies=[Depends(get_current_captain)])


class SendEmailRequest(BaseModel):
    to: str = Field(..., max_length=320)
    to_name: Optional[str] = Field(default=None, max_length=200)
    subject: str = Field(..., max_length=998)
    body: str = Field(..., max_length=500_000)


class ReplyRequest(BaseModel):
    message_id: int
    reply_body: str = Field(..., max_length=500_000)


@router.get("/status")
async def gmail_status(db: AsyncSession = Depends(get_db)):
    """Is the executive email stack connected and ready?"""
    status = await email_delivery_status(db, validate_provider=True)
    return {
        "connected": status["send_mode"] == "live",
        "provider": status.get("provider", "ses"),
        "configured": status.get("configured", False),
        "production_access_enabled": status.get("production_access_enabled", False),
        "identity_verified": status.get("identity_verified", False),
        "address": status.get("from_email") or settings.EXECUTIVE_EMAIL_ADDRESS,
        "identity_name": status.get("from_name") or settings.EXECUTIVE_EMAIL_NAME,
        "identity_title": status.get("from_title") or settings.EXECUTIVE_EMAIL_TITLE,
        "ses_region": settings.SES_REGION or settings.AWS_REGION,
        "send_method": status["send_method"],
        "send_mode": status["send_mode"],
        "message": "Executive email operational." if status["send_mode"] == "live" else status["validation_error"],
    }


@router.get("/engine-status")
async def gmail_engine_status(db: AsyncSession = Depends(get_db)):
    """Dashboard-facing production readiness for the outreach email engine."""
    return await email_delivery_status(db, validate_provider=True)


@router.post("/fetch")
@limiter.limit("10/minute")
async def fetch_inbox(request: Request, db: AsyncSession = Depends(get_db)):
    """Trigger inbox fetch manually; JARVIS reads all new emails."""
    count = await fetch_new_emails(db)
    return {"fetched": count, "message": f"JARVIS processed {count} new emails from the inbound queue."}


@router.get("/inbox")
async def inbox(
    category: Optional[str] = Query(None, description="client_reply, new_inquiry, follow_up, spam, other"),
    needs_action: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    """Full inbox; all emails JARVIS has tracked."""
    messages = await get_inbox(db, category=category, needs_action=needs_action, limit=limit, offset=offset)
    stats = await get_inbox_stats(db)
    return {
        "stats": stats,
        "messages": [
            {
                "id": m.id,
                "from_email": m.from_email,
                "from_name": m.from_name,
                "subject": m.subject,
                "snippet": m.snippet,
                "category": m.category,
                "sentiment": m.sentiment,
                "ai_summary": m.ai_summary,
                "ai_action": m.ai_action,
                "needs_action": m.needs_action,
                "is_read": m.is_read,
                "is_replied": m.is_replied,
                "lead_id": m.lead_id,
                "contact_id": m.contact_id,
                "received_at": str(m.received_at) if m.received_at else None,
            }
            for m in messages
        ],
    }


@router.get("/stats")
async def inbox_stats(db: AsyncSession = Depends(get_db)):
    """Executive email inbox statistics."""
    return await get_inbox_stats(db)


@router.post("/messages/{message_id}/read")
@limiter.limit("30/minute")
async def read_message(request: Request, message_id: int, db: AsyncSession = Depends(get_db)):
    """Mark a message as read."""
    await mark_read(db, message_id)
    return {"marked_read": True}


@router.post("/send")
@limiter.limit("10/minute")
async def send_email(request: Request, body: SendEmailRequest, db: AsyncSession = Depends(get_db)):
    """Send an email directly from the JARVIS dashboard."""
    success, error, method = await send_client_email(
        db,
        to=body.to,
        subject=body.subject,
        body=body.body,
        to_name=body.to_name or "",
    )
    if not success:
        logger.error("gmail send_client_email failed: %s", error)
        raise HTTPException(status_code=500, detail="Email delivery failed")

    from app.models.gmail import GmailMessage

    uid = hashlib.md5(f"{body.to}{body.subject}{datetime.now()}".encode()).hexdigest()[:20]
    record = GmailMessage(
        gmail_id=f"sent_{uid}",
        from_email=settings.EXECUTIVE_EMAIL_ADDRESS,
        from_name=settings.EXECUTIVE_EMAIL_NAME,
        to_email=body.to,
        subject=body.subject,
        snippet=body.body[:200],
        direction="outbound",
        category="other",
        is_read=True,
    )
    db.add(record)
    await db.commit()

    return {"sent": True, "to": body.to, "subject": body.subject, "method": method}
