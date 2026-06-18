"""
Legacy inbound email manager.

Inbound email processing is currently disabled until SES inbound routing is
wired. The helpers in this module remain only for compatibility with stored
records and future inbound processing.
"""
import imaplib
import email
import logging
from email.header import decode_header
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.models.gmail import GmailMessage

logger = logging.getLogger(__name__)

# Placeholder only. Legacy Gmail IMAP is retired; SES inbound will replace it.
IMAP_HOST = None
IMAP_PORT = 993

CATEGORISE_PROMPT = """
Analyse this email and return a JSON response with these fields:
- category: one of [client_reply, new_inquiry, follow_up, spam, notification, other]
- sentiment: one of [positive, neutral, negative, urgent]
- summary: one sentence describing what this email is about
- action: what JARVIS should do next (e.g. "Reply with proposal", "Update CRM", "Ignore", "Alert Captain")
- needs_action: true or false

Email from: {from_email}
Subject: {subject}
Body: {body}

Return valid JSON only. No markdown.
"""


def _is_configured() -> bool:
    return False


def _decode_header_value(value: str) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(str(part))
    return " ".join(decoded)


def _get_body(msg) -> tuple[str, str]:
    """Extract plain text and HTML body from email message."""
    text, html = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if "attachment" in cd:
                continue
            if ct == "text/plain":
                try:
                    text = part.get_payload(decode=True).decode("utf-8", errors="replace")
                except Exception:
                    pass
            elif ct == "text/html":
                try:
                    html = part.get_payload(decode=True).decode("utf-8", errors="replace")
                except Exception:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                text = payload.decode("utf-8", errors="replace")
        except Exception:
            pass
    return text[:3000], html[:5000]


async def _categorise_email(from_email: str, subject: str, body: str) -> dict:
    """Use AI to categorise an incoming email."""
    try:
        from app.services.ai.router import ai_router
        import json
        prompt = CATEGORISE_PROMPT.format(
            from_email=from_email,
            subject=subject[:200],
            body=body[:800]
        )
        resp = await ai_router.chat(
            messages=[{"role": "user", "content": prompt}],
            task_type="FAST",
            max_tokens=200,
        )
        content = resp.get("content", "").strip()
        # strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        logger.warning(f"Email categorisation failed: {e}")
        return {
            "category": "other",
            "sentiment": "neutral",
            "summary": subject[:100],
            "action": "Review manually",
            "needs_action": False,
        }


async def _match_lead_or_contact(db: AsyncSession, from_email: str) -> tuple[Optional[int], Optional[int]]:
    """Try to match incoming email to a known lead or CRM contact."""
    lead_id = None
    contact_id = None
    try:
        from app.models.lead import Lead
        lead = (await db.execute(
            select(Lead).where(Lead.email == from_email.lower()).limit(1)
        )).scalar_one_or_none()
        if lead:
            lead_id = lead.id

        from app.models.crm import Contact
        contact = (await db.execute(
            select(Contact).where(Contact.email == from_email.lower()).limit(1)
        )).scalar_one_or_none()
        if contact:
            contact_id = contact.id
    except Exception as exc:
        logger.warning("Lead/contact match failed for email %s: %s", from_email, exc)
    return lead_id, contact_id


async def fetch_new_emails(db: AsyncSession) -> int:
    """
    Inbound SES processing is not wired yet, so this is currently a no-op.
    Returns count of new emails processed.
    """
    logger.info("Inbound SES processing is not configured yet; skipping inbox fetch.")
    return 0


async def _update_lead_on_reply(db: AsyncSession, lead_id: int, from_email: str, subject: str) -> None:
    """When a lead replies, update their status in CRM."""
    try:
        from app.models.lead import Lead
        lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
        if lead and lead.status in ("contacted", "cold", "new"):
            lead.status = "replied"
            await db.flush()
            logger.info(f"Lead {lead_id} status updated to 'replied' — email from {from_email}")
    except Exception as e:
        logger.warning(f"Lead update on reply failed: {e}")


async def _alert_captain(from_email: str, from_name: str, subject: str, summary: str) -> None:
    """Notify Captain when an important email arrives."""
    try:
        from app.services.notifications.telegram import notify_telegram
        msg = (
            f"📧 New email needs attention\n"
            f"From: {from_name} ({from_email})\n"
            f"Subject: {subject[:100]}\n"
            f"JARVIS: {summary}"
        )
        await notify_telegram(msg)
    except Exception as exc:
        logger.warning("Telegram inbox notification failed for email from %s: %s", from_email, exc)


async def get_inbox(
    db: AsyncSession,
    category: Optional[str] = None,
    needs_action: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[GmailMessage]:
    q = select(GmailMessage).where(
        GmailMessage.direction == "inbound"
    ).order_by(GmailMessage.received_at.desc()).limit(limit).offset(offset)

    if category:
        q = q.where(GmailMessage.category == category)
    if needs_action is not None:
        q = q.where(GmailMessage.needs_action == needs_action)

    return list((await db.execute(q)).scalars().all())


async def mark_read(db: AsyncSession, message_id: int) -> None:
    msg = (await db.execute(select(GmailMessage).where(GmailMessage.id == message_id))).scalar_one_or_none()
    if msg:
        msg.is_read = True
        await db.commit()


async def get_inbox_stats(db: AsyncSession) -> dict:
    from sqlalchemy import func as sqlfunc
    total = await db.scalar(select(sqlfunc.count()).select_from(GmailMessage).where(GmailMessage.direction == "inbound")) or 0
    unread = await db.scalar(select(sqlfunc.count()).select_from(GmailMessage).where(GmailMessage.is_read == False).where(GmailMessage.direction == "inbound")) or 0
    needs_action = await db.scalar(select(sqlfunc.count()).select_from(GmailMessage).where(GmailMessage.needs_action == True)) or 0
    client_replies = await db.scalar(select(sqlfunc.count()).select_from(GmailMessage).where(GmailMessage.category == "client_reply")) or 0
    new_inquiries = await db.scalar(select(sqlfunc.count()).select_from(GmailMessage).where(GmailMessage.category == "new_inquiry")) or 0
    return {
        "total": total,
        "unread": unread,
        "needs_action": needs_action,
        "client_replies": client_replies,
        "new_inquiries": new_inquiries,
    }
