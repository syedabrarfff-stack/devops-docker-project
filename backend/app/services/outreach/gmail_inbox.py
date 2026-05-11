"""
JARVIS Gmail Inbox Manager
- Reads inbox via IMAP every 15 minutes
- Categorises every email with AI
- Detects client replies, new inquiries, urgent messages
- Updates CRM automatically when a lead replies
- Alerts Captain for anything that needs attention
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

IMAP_HOST = "imap.gmail.com"
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
    return bool(settings.GMAIL_ADDRESS and settings.GMAIL_APP_PASSWORD)


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
    except Exception:
        pass
    return lead_id, contact_id


async def fetch_new_emails(db: AsyncSession) -> int:
    """
    Connect to Gmail via IMAP, fetch unseen emails, process and store them.
    Returns count of new emails processed.
    """
    if not _is_configured():
        logger.warning("Gmail not configured — skipping inbox fetch")
        return 0

    count = 0
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(settings.GMAIL_ADDRESS, settings.GMAIL_APP_PASSWORD)
        mail.select("INBOX")

        # Fetch unseen emails
        _, message_ids = mail.search(None, "UNSEEN")
        ids = message_ids[0].split()

        if not ids:
            mail.logout()
            return 0

        logger.info(f"Gmail: {len(ids)} new emails found")

        for msg_id in ids[-50:]:  # process up to 50 at a time
            try:
                _, msg_data = mail.fetch(msg_id, "(RFC822 UID)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                gmail_uid = msg_id.decode()

                # Skip if already stored
                existing = (await db.execute(
                    select(GmailMessage).where(GmailMessage.gmail_id == gmail_uid)
                )).scalar_one_or_none()
                if existing:
                    continue

                from_raw = _decode_header_value(msg.get("From", ""))
                subject = _decode_header_value(msg.get("Subject", "(no subject)"))
                date_str = msg.get("Date", "")

                # Parse from name and email
                from_name, from_email_addr = "", from_raw
                if "<" in from_raw:
                    parts = from_raw.split("<")
                    from_name = parts[0].strip().strip('"')
                    from_email_addr = parts[1].strip().rstrip(">")

                body_text, body_html = _get_body(msg)
                snippet = body_text[:200].strip()

                # Skip emails we sent to ourselves
                if from_email_addr.lower() == settings.GMAIL_ADDRESS.lower():
                    continue

                # AI categorisation
                ai_result = await _categorise_email(from_email_addr, subject, body_text)

                # Match to CRM
                lead_id, contact_id = await _match_lead_or_contact(db, from_email_addr)

                # Parse date
                received_at = None
                try:
                    from email.utils import parsedate_to_datetime
                    received_at = parsedate_to_datetime(date_str)
                except Exception:
                    received_at = datetime.now(timezone.utc)

                record = GmailMessage(
                    gmail_id=gmail_uid,
                    from_email=from_email_addr.lower(),
                    from_name=from_name or from_email_addr,
                    to_email=settings.GMAIL_ADDRESS,
                    subject=subject,
                    body_text=body_text,
                    body_html=body_html,
                    snippet=snippet,
                    direction="inbound",
                    category=ai_result.get("category", "other"),
                    sentiment=ai_result.get("sentiment", "neutral"),
                    ai_summary=ai_result.get("summary", ""),
                    ai_action=ai_result.get("action", ""),
                    needs_action=ai_result.get("needs_action", False),
                    lead_id=lead_id,
                    contact_id=contact_id,
                    is_read=False,
                    received_at=received_at,
                )
                db.add(record)
                count += 1

                # Update lead status if this is a reply from a known lead
                if lead_id:
                    await _update_lead_on_reply(db, lead_id, from_email_addr, subject)

                # Alert Captain for urgent/high-value emails
                if ai_result.get("needs_action") or ai_result.get("sentiment") == "urgent":
                    await _alert_captain(from_email_addr, from_name, subject, ai_result.get("summary", ""))

            except Exception as e:
                logger.warning(f"Error processing email {msg_id}: {e}")
                continue

        await db.commit()
        mail.logout()
        logger.info(f"Gmail inbox: {count} new emails processed")

    except imaplib.IMAP4.error as e:
        logger.error(f"IMAP connection failed: {e}")
    except Exception as e:
        logger.error(f"Gmail inbox fetch failed: {e}")

    return count


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
    except Exception:
        pass


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
