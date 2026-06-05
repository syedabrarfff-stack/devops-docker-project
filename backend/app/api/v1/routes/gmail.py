"""JARVIS Gmail Operations Center."""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.services.outreach.gmail import gmail_delivery_status, send_client_email
from app.services.outreach.gmail_inbox import fetch_new_emails, get_inbox, get_inbox_stats, mark_read

router = APIRouter(prefix="/gmail", tags=["gmail"])


class SendEmailRequest(BaseModel):
    to: str
    to_name: Optional[str] = None
    subject: str
    body: str


class ReplyRequest(BaseModel):
    message_id: int
    reply_body: str


@router.get("/status")
async def gmail_status(db: AsyncSession = Depends(get_db)):
    """Is Gmail connected and ready?"""
    status = await gmail_delivery_status(db, validate_smtp=True)
    return {
        "connected": status["send_mode"] == "live",
        "oauth_configured": status["oauth_configured"],
        "oauth_connected": status["oauth_connected"],
        "smtp_configured": status["smtp_configured"],
        "smtp_validated": status["smtp_validated"],
        "address": status.get("oauth_email") or settings.GMAIL_ADDRESS,
        "smtp_host": settings.SMTP_HOST,
        "imap_host": "imap.gmail.com",
        "send_method": status["send_method"],
        "send_mode": status["send_mode"],
        "message": "Gmail operational." if status["send_mode"] == "live" else status["validation_error"],
    }


@router.get("/engine-status")
async def gmail_engine_status(db: AsyncSession = Depends(get_db)):
    """Dashboard-facing production readiness for the outreach email engine."""
    return await gmail_delivery_status(db, validate_smtp=True)


@router.post("/fetch")
async def fetch_inbox(db: AsyncSession = Depends(get_db)):
    """Trigger inbox fetch manually; JARVIS reads all new emails."""
    count = await fetch_new_emails(db)
    return {"fetched": count, "message": f"JARVIS processed {count} new emails from inbox."}


@router.get("/inbox")
async def inbox(
    category: Optional[str] = Query(None, description="client_reply, new_inquiry, follow_up, spam, other"),
    needs_action: Optional[bool] = Query(None),
    limit: int = Query(50, le=100),
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
    """Gmail inbox statistics."""
    return await get_inbox_stats(db)


@router.post("/messages/{message_id}/read")
async def read_message(message_id: int, db: AsyncSession = Depends(get_db)):
    """Mark a message as read."""
    await mark_read(db, message_id)
    return {"marked_read": True}


@router.post("/send")
async def send_email(body: SendEmailRequest, db: AsyncSession = Depends(get_db)):
    """Send an email directly from the JARVIS dashboard."""
    success, error, method = await send_client_email(
        db,
        to=body.to,
        subject=body.subject,
        body=body.body,
        to_name=body.to_name or "",
    )
    if not success:
        raise HTTPException(status_code=500, detail=f"Send failed: {error}")

    from app.models.gmail import GmailMessage

    uid = hashlib.md5(f"{body.to}{body.subject}{datetime.now()}".encode()).hexdigest()[:20]
    record = GmailMessage(
        gmail_id=f"sent_{uid}",
        from_email=settings.GMAIL_ADDRESS,
        from_name="Aliyar Solutions",
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
