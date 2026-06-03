from __future__ import annotations

import asyncio
import email
import imaplib
import logging
import re
import uuid
from datetime import UTC, datetime
from email.header import decode_header
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from html import escape
from typing import Any
from urllib.parse import quote

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.middleware import record_outreach_sent
from app.models.approval import AuditLog
from app.models.lead import Lead, LeadStatus
from app.models.outreach import EmailTracking, OutreachLog, OutreachStatus

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993


class GmailSender:
    async def send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        from_name: str,
        from_email: str,
    ) -> bool:
        if not _gmail_configured():
            await self._audit_failure(
                "gmail_send_not_configured",
                {"to": to, "subject": subject, "reason": "GMAIL_ADDRESS or GMAIL_APP_PASSWORD missing"},
            )
            return False

        message = EmailMessage()
        sender_email = settings.GMAIL_ADDRESS
        reply_to = from_email or settings.GMAIL_ADDRESS
        message["From"] = formataddr((from_name or "Aliyar Solutions", sender_email))
        message["To"] = to
        message["Subject"] = subject
        if reply_to != settings.GMAIL_ADDRESS:
            message["Reply-To"] = reply_to
        message.set_content(_html_to_text(body_html))
        message.add_alternative(body_html, subtype="html")

        try:
            import aiosmtplib

            await aiosmtplib.send(
                message,
                hostname=SMTP_HOST,
                port=SMTP_PORT,
                start_tls=True,
                username=settings.GMAIL_ADDRESS,
                password=settings.GMAIL_APP_PASSWORD,
                timeout=20,
            )
            return True
        except Exception as exc:
            logger.warning("Gmail SMTP send failed for %s: %s", to, exc)
            await self._audit_failure(
                "gmail_send_failed",
                {"to": to, "subject": subject, "error": str(exc)},
            )
            return False

    async def send_outreach(self, outreach: OutreachLog) -> bool:
        if not outreach.tenant_id:
            logger.warning("Outreach send skipped: outreach has no tenant_id")
            return False

        tenant_id = uuid.UUID(str(outreach.tenant_id))
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_id))
                row = await self._load_outreach(session, tenant_id, outreach)
                if not row:
                    return False

                lead = None
                if row.lead_id:
                    lead = await session.scalar(
                        select(Lead).where(Lead.tenant_id == tenant_id, Lead.id == row.lead_id)
                    )
                to_email = (lead.email or lead.contact_email) if lead else None
                if not to_email:
                    row.status = OutreachStatus.BOUNCED
                    await self._audit(
                        session,
                        tenant_id,
                        "outreach_send_missing_recipient",
                        row.id,
                        {"lead_id": str(row.lead_id) if row.lead_id else None},
                    )
                    return False

                body_html = _wrap_html(row.body_text or "", row.id)
                success = await self.send_email(
                    to=to_email,
                    subject=row.subject or "",
                    body_html=body_html,
                    from_name=row.sent_from_persona or "Aliyar Solutions",
                    from_email=settings.GMAIL_ADDRESS or "",
                )

                if success:
                    row.status = OutreachStatus.SENT
                    row.sent_at = datetime.now(UTC)
                    tracking = await session.scalar(
                        select(EmailTracking).where(
                            EmailTracking.tenant_id == tenant_id,
                            EmailTracking.outreach_id == row.id,
                        )
                    )
                    if not tracking:
                        session.add(EmailTracking(tenant_id=tenant_id, outreach_id=row.id))
                    await self._audit(
                        session,
                        tenant_id,
                        "outreach_email_sent",
                        row.id,
                        {
                            "to": to_email,
                            "subject": row.subject,
                            "tracking_pixel": _tracking_pixel_url(row.id),
                        },
                    )
                    record_outreach_sent(row.channel.value if row.channel else "EMAIL", row.sent_from_persona)
                else:
                    row.status = OutreachStatus.BOUNCED
                    await self._audit(
                        session,
                        tenant_id,
                        "outreach_email_send_failed",
                        row.id,
                        {"to": to_email, "subject": row.subject},
                    )
                return success

    async def check_replies(self, tenant_id) -> list[dict]:
        if not _gmail_configured():
            logger.info("Gmail IMAP reply check skipped: Gmail is not configured")
            return []

        tenant_uuid = uuid.UUID(str(tenant_id))
        raw_messages = await asyncio.to_thread(_fetch_unseen_messages)
        replies: list[dict[str, Any]] = []

        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                for raw in raw_messages:
                    from_email = raw["from_email"].lower()
                    lead = await session.scalar(
                        select(Lead).where(
                            Lead.tenant_id == tenant_uuid,
                            func.lower(Lead.email) == from_email,
                        ).limit(1)
                    )
                    if not lead:
                        lead = await session.scalar(
                            select(Lead).where(
                                Lead.tenant_id == tenant_uuid,
                                func.lower(Lead.contact_email) == from_email,
                            ).limit(1)
                        )
                    if not lead:
                        continue

                    lead.status = LeadStatus.REPLIED
                    lead.last_contact = datetime.now(UTC)
                    lead.last_contacted = datetime.now(UTC)
                    latest_outreach = await session.scalar(
                        select(OutreachLog)
                        .where(OutreachLog.tenant_id == tenant_uuid, OutreachLog.lead_id == lead.id)
                        .order_by(OutreachLog.sent_at.desc().nullslast(), OutreachLog.created_at.desc())
                        .limit(1)
                    )
                    if latest_outreach:
                        latest_outreach.status = OutreachStatus.REPLIED
                        tracking = await session.scalar(
                            select(EmailTracking).where(
                                EmailTracking.tenant_id == tenant_uuid,
                                EmailTracking.outreach_id == latest_outreach.id,
                            )
                        )
                        if not tracking:
                            tracking = EmailTracking(tenant_id=tenant_uuid, outreach_id=latest_outreach.id)
                            session.add(tracking)
                        tracking.replied_at = datetime.now(UTC)

                    reply = {
                        "lead_id": str(lead.id),
                        "from_email": from_email,
                        "subject": raw["subject"],
                        "body_preview": raw["body"][:500],
                        "received_at": raw["date"],
                    }
                    replies.append(reply)
                    await self._audit(
                        session,
                        tenant_uuid,
                        "gmail_reply_detected",
                        latest_outreach.id if latest_outreach else lead.id,
                        reply,
                    )

        return replies

    async def _load_outreach(self, session, tenant_id: uuid.UUID, outreach: OutreachLog) -> OutreachLog | None:
        if outreach.id:
            return await session.scalar(
                select(OutreachLog).where(OutreachLog.tenant_id == tenant_id, OutreachLog.id == outreach.id)
            )
        session.add(outreach)
        await session.flush()
        return outreach

    async def _audit(self, session, tenant_id: uuid.UUID, action: str, entity_id: uuid.UUID, details: dict) -> None:
        session.add(
            AuditLog(
                tenant_id=tenant_id,
                action=action,
                entity_type="outreach",
                entity_id=entity_id,
                actor="GmailSender",
                after_json=details,
                details=details,
            )
        )

    async def _audit_failure(self, action: str, details: dict) -> None:
        if not settings.JARVIS_DEFAULT_TENANT_ID:
            return
        tenant_id = uuid.UUID(str(settings.JARVIS_DEFAULT_TENANT_ID))
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_id))
                session.add(
                    AuditLog(
                        tenant_id=tenant_id,
                        action=action,
                        entity_type="gmail",
                        actor="GmailSender",
                        after_json=details,
                        details=details,
                    )
                )


def _gmail_configured() -> bool:
    return bool(settings.GMAIL_ADDRESS and settings.GMAIL_APP_PASSWORD)


def _wrap_html(body_text: str, outreach_id: uuid.UUID | None) -> str:
    body_html = _linkify_body(body_text, outreach_id)
    pixel = ""
    if outreach_id and settings.APP_BASE_URL:
        pixel = (
            f'<img src="{_tracking_pixel_url(outreach_id)}" width="1" height="1" '
            'style="display:none" alt="">'
        )
    return (
        '<html><body style="font-family:Arial,sans-serif;color:#202124;'
        'line-height:1.5;max-width:640px">'
        f"{body_html}{pixel}</body></html>"
    )


def _tracking_pixel_url(outreach_id: uuid.UUID | None) -> str | None:
    if not outreach_id or not settings.APP_BASE_URL:
        return None
    return f"{settings.APP_BASE_URL.rstrip('/')}/api/v1/outreach/track/open/{outreach_id}.gif"


def _click_tracking_url(outreach_id: uuid.UUID, destination: str) -> str | None:
    if not settings.APP_BASE_URL:
        return None
    encoded = quote(destination, safe="")
    return f"{settings.APP_BASE_URL.rstrip('/')}/api/v1/outreach/track/click/{outreach_id}?url={encoded}"


def _linkify_body(body_text: str, outreach_id: uuid.UUID | None) -> str:
    url_pattern = re.compile(r"https?://[^\s<>\"]+")
    pieces: list[str] = []
    cursor = 0
    for match in url_pattern.finditer(body_text or ""):
        pieces.append(escape((body_text or "")[cursor:match.start()]).replace("\n", "<br>"))
        destination = match.group(0).rstrip(".,)")
        trailing = match.group(0)[len(destination):]
        href = _click_tracking_url(outreach_id, destination) if outreach_id else None
        if href:
            pieces.append(f'<a href="{escape(href)}">{escape(destination)}</a>{escape(trailing)}')
        else:
            pieces.append(escape(match.group(0)))
        cursor = match.end()
    pieces.append(escape((body_text or "")[cursor:]).replace("\n", "<br>"))
    return "".join(pieces)


def _html_to_text(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _fetch_unseen_messages() -> list[dict]:
    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    try:
        mail.login(settings.GMAIL_ADDRESS, settings.GMAIL_APP_PASSWORD)
        mail.select("INBOX")
        _, message_ids = mail.search(None, "UNSEEN")
        messages = []
        for message_id in message_ids[0].split():
            _, data = mail.fetch(message_id, "(RFC822)")
            if not data or not data[0]:
                continue
            msg = email.message_from_bytes(data[0][1])
            from_name, from_email = parseaddr(msg.get("From", ""))
            subject = _decode_header(msg.get("Subject", ""))
            body = _extract_body(msg)
            messages.append(
                {
                    "from_name": from_name,
                    "from_email": from_email,
                    "subject": subject,
                    "body": body,
                    "date": msg.get("Date", ""),
                    "message_id": msg.get("Message-ID", ""),
                    "in_reply_to": msg.get("In-Reply-To", ""),
                }
            )
        return messages
    finally:
        try:
            mail.close()
        except Exception:
            pass
        try:
            mail.logout()
        except Exception:
            pass


def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    pieces = []
    for part, encoding in decode_header(value):
        if isinstance(part, bytes):
            pieces.append(part.decode(encoding or "utf-8", errors="replace"))
        else:
            pieces.append(str(part))
    return " ".join(pieces)


def _extract_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in disposition:
                continue
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace")[:5000]
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    return _html_to_text(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))[:5000]
        return ""
    payload = msg.get_payload(decode=True)
    if not payload:
        return ""
    return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")[:5000]


gmail_sender = GmailSender()
