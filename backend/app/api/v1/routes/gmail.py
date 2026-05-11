"""
JARVIS Gmail Operations Center
Full inbox monitoring, reply tracking, CRM sync, outreach sending
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.outreach.gmail_inbox import (
    fetch_new_emails, get_inbox, get_inbox_stats, mark_read,
)
from app.services.outreach.gmail import send_email_smtp, _is_gmail_configured
from app.core.config import settings

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
    return {
        "connected": configured,
        "address": settings.GMAIL_ADDRESS if configured else None,
        "smtp_host": "smtp.gmail.com",
        "imap_host": "imap.gmail.com",
        "message": "Gmail operational — JARVIS has full email access." if configured else "Gmail not configured. Add GMAIL_ADDRESS + GMAIL_APP_PASSWORD to .env"
    }


@router.post("/fetch")
async def fetch_inbox(db: AsyncSession = Depends(get_db)):
    """Trigger inbox fetch manually — JARVIS reads all new emails."""
    count = await fetch_new_emails(db)
    return {
        "fetched": count,
        "message": f"JARVIS processed {count} new emails from inbox."
    }


@router.get("/inbox")
async def inbox(
    category: Optional[str] = Query(None, description="client_reply, new_inquiry, follow_up, spam, other"),
    needs_action: Optional[bool] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    """Full inbox — all emails JARVIS has tracked."""
    messages = await get_inbox(db, category=category, needs_action=needs_action, limit=limit, offset=offset)
    stats = await get_inbox_stats(db)
    return {
        "stats": stats,
        "messages": [{
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
        } for m in messages]
    }


@router.get("/stats")
async def inbox_stats(db: AsyncSession = Depends(get_db)):
    """Gmail inbox statistics."""
    stats = await get_inbox_stats(db)
    return stats


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

    # Log as outbound message
    from app.models.gmail import GmailMessage
    from datetime import datetime, timezone
    import hashlib
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
