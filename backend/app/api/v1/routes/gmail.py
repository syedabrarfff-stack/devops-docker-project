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
from app.services.outreach.gmail import _is_gmail_configured, send_email_smtp, validate_smtp_credentials
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
async def gmail_status():
    """Is Gmail connected and ready?"""
    configured = _is_gmail_configured()
    valid = False
    validation_error = ""
    if configured:
        valid, validation_error = validate_smtp_credentials()
    return {
        "connected": configured,
        "smtp_validated": valid,
        "address": settings.GMAIL_ADDRESS if configured else None,
        "smtp_host": settings.SMTP_HOST,
        "imap_host": "imap.gmail.com",
        "message": "Gmail operational - SMTP credentials validated." if valid else (validation_error or "Gmail not configured. Add GMAIL_ADDRESS + GMAIL_APP_PASSWORD to .env"),
    }


@router.get("/engine-status")
async def gmail_engine_status(db: AsyncSession = Depends(get_db)):
    """Dashboard-facing production readiness for the outreach email engine."""
    from app.services.outreach.compliance import outreach_compliance

    configured = _is_gmail_configured()
    valid, validation_error = validate_smtp_credentials() if configured else (False, "Gmail not configured")
    return {
        "engine": "gmail_outreach",
        "configured": configured,
        "smtp_validated": valid,
        "daily_cap": outreach_compliance.current_daily_cap(),
        "send_mode": "live" if valid and not settings.OUTREACH_PAUSED else "blocked",
        "outreach_paused": settings.OUTREACH_PAUSED,
        "validation_error": "" if valid else validation_error,
        "safety": {
            "unsubscribe_footer": True,
            "do_not_contact_gate": True,
            "business_hours_gate": True,
            "daily_cap_gate": True,
            "client_language_sanitizer": True,
        },
    }


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
    if not _is_gmail_configured():
        raise HTTPException(status_code=503, detail="Gmail not configured")

    success, error = send_email_smtp(
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

    return {"sent": True, "to": body.to, "subject": body.subject}
