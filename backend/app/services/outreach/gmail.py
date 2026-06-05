"""Gmail integration: SMTP sending plus optional AI personalisation."""
from __future__ import annotations

import logging
import smtplib
from datetime import datetime, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.outreach import OutreachEmail
from app.services.communication.client_language import sanitize_client_text, sanitize_subject_body
from app.services.storage.secure import get_credential

logger = logging.getLogger(__name__)


def _gmail_sender(address: Optional[str] = None) -> str:
    return (address or settings.GMAIL_ADDRESS or settings.GMAIL_USER or settings.EMAIL_USER or "").strip()


def _gmail_app_password(password: Optional[str] = None) -> str:
    """Gmail app passwords are often copied with spaces; SMTP expects plain text."""
    return (password or settings.GMAIL_APP_PASSWORD or settings.EMAIL_PASS or "").replace(" ", "").strip()


def _is_gmail_configured() -> bool:
    return bool(_gmail_sender() and _gmail_app_password())


def _smtp_error_message(exc: Exception) -> str:
    text = str(exc)
    lowered = text.lower()
    if "5.7.8" in text or "badcredentials" in lowered or "username and password not accepted" in lowered:
        return "Google rejected the Gmail SMTP credentials. Generate a fresh app password or connect Gmail OAuth."
    if "timed out" in lowered or "timeout" in lowered:
        return "Gmail SMTP connection timed out."
    if "authentication" in lowered or "auth" in lowered:
        return "Gmail SMTP authentication failed."
    return text.splitlines()[0][:240]


def _validate_password_shape(password: str) -> tuple[bool, str]:
    if not password:
        return False, "Gmail app password is missing."
    try:
        password.encode("ascii")
    except UnicodeEncodeError:
        return False, "Gmail app password contains non-ASCII characters."
    if len(password) != 16:
        return False, "Gmail app password must be the real 16-character Google app password."
    return True, ""


def validate_smtp_credentials(
    gmail_address: Optional[str] = None,
    gmail_password: Optional[str] = None,
) -> tuple[bool, str]:
    """Verify SMTP handshake plus auth without sending a message."""
    sender = _gmail_sender(gmail_address)
    password = _gmail_app_password(gmail_password)
    if not sender:
        return False, "Gmail sender is missing."
    valid_shape, shape_error = _validate_password_shape(password)
    if not valid_shape:
        return False, shape_error
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12) as server:
            server.ehlo()
            if not settings.SMTP_SECURE:
                server.starttls()
                server.ehlo()
            server.login(sender, password)
        return True, ""
    except Exception as exc:
        return False, _smtp_error_message(exc)


def send_email_smtp(
    to: str,
    subject: str,
    body: str,
    to_name: str = "",
    gmail_address: Optional[str] = None,
    gmail_password: Optional[str] = None,
    attachments: Optional[list[dict]] = None,
) -> tuple[bool, str]:
    """Send via Gmail SMTP using an app password. Returns (success, error)."""
    sender = _gmail_sender(gmail_address)
    password = _gmail_app_password(gmail_password)
    if not sender:
        return False, "Gmail not configured - add GMAIL_ADDRESS and GMAIL_APP_PASSWORD."
    valid_shape, shape_error = _validate_password_shape(password)
    if not valid_shape:
        return False, shape_error

    try:
        subject, body = sanitize_subject_body(subject, body)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Aliyar Solutions <{sender}>"
        msg["To"] = f"{to_name} <{to}>" if to_name else to
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(_wrap_html(body), "html"))

        for attachment in attachments or []:
            filename = (attachment.get("filename") or "attachment").strip()
            payload = attachment.get("content") or b""
            if isinstance(payload, str):
                payload = payload.encode("utf-8")
            part = MIMEBase("application", "octet-stream")
            part.set_payload(payload)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment", filename=filename)
            msg.attach(part)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            if not settings.SMTP_SECURE:
                server.starttls()
            server.login(sender, password)
            server.sendmail(sender, to, msg.as_string())

        logger.info("Email sent to %s: %s", to, subject)
        return True, ""
    except Exception as exc:
        error = _smtp_error_message(exc)
        logger.error("SMTP error sending to %s: %s", to, error)
        return False, error


def _wrap_html(body: str) -> str:
    body_html = sanitize_client_text(body).replace("\n", "<br>")
    return f"""
<html><body style="font-family:Arial,sans-serif;color:#222;max-width:600px;margin:0 auto">
  <div style="background:#f8f9fa;padding:24px;border-radius:8px">
    <p>{body_html}</p>
    <hr style="border:none;border-top:1px solid #e0e0e0;margin:20px 0">
    <p style="color:#888;font-size:12px">
      Aliyar Solutions - Operations Consulting &amp; Cloud Services<br>
      <a href="https://aliyarsolutions.com" style="color:#0066cc">aliyarsolutions.com</a>
    </p>
  </div>
</body></html>"""


async def personalise_email(template: str, contact_data: dict) -> str:
    """Use the AI router to personalise an email template with contact context."""
    from app.services.ai.base_provider import Message, TaskType
    from app.services.ai.router import ai_router

    context = "\n".join(f"  {k}: {v}" for k, v in contact_data.items() if v)
    prompt = (
        "Personalise this outreach email for the contact below. "
        "Keep it professional, concise, and human. Do not change the core message. "
        "Max 200 words. Never mention internal systems, AI providers, prompts, routing, or tooling. "
        f"Return only the email body text.\n\nTEMPLATE:\n{template}\n\nCONTACT:\n{context}"
    )
    resp, _ = await ai_router.chat(
        [Message(role="user", content=prompt)],
        task_type=TaskType.FAST,
        force_provider="google",
    )
    return sanitize_client_text(resp.content if not resp.error else template)


async def send_outreach_email(db: AsyncSession, email_id: int) -> bool:
    """Fetch OutreachEmail record, personalise, send, and update status."""
    from sqlalchemy import select

    row = (await db.execute(select(OutreachEmail).where(OutreachEmail.id == email_id))).scalar_one_or_none()
    if not row or row.status not in ("scheduled", "queued"):
        return False

    from app.services.outreach.compliance import outreach_compliance

    if await outreach_compliance.is_outreach_paused(db, row.tenant_id):
        row.status = "skipped"
        row.error = "outreach_paused"
        await db.flush()
        return False
    if await outreach_compliance.is_do_not_contact(db, row.tenant_id, row.to_email):
        row.status = "skipped"
        row.error = "do_not_contact"
        await db.flush()
        return False
    cap = await outreach_compliance.daily_send_cap_status(db, row.tenant_id)
    if not cap["allowed"]:
        row.error = "daily_send_cap_reached"
        if cap.get("reschedule_at"):
            row.scheduled_at = cap["reschedule_at"]
            row.status = "scheduled"
        await db.flush()
        return False

    subject, body = sanitize_subject_body(row.subject or "", row.body or "")
    if settings.OUTREACH_PERSONALIZE_ON_SEND and row.contact_id and not row.personalized:
        from app.models.crm import Contact

        contact = (await db.execute(select(Contact).where(Contact.id == row.contact_id))).scalar_one_or_none()
        if contact:
            body = await personalise_email(
                body,
                {
                    "name": contact.name,
                    "title": contact.title,
                    "company": getattr(contact.company, "name", ""),
                    "country": contact.country,
                },
            )
            row.personalized = True

    body = outreach_compliance.append_footer(body, row.to_email)
    gmail_address = await get_credential(db, "GMAIL_ADDRESS") or await get_credential(db, "GMAIL_USER") or await get_credential(db, "EMAIL_USER")
    gmail_password = await get_credential(db, "GMAIL_APP_PASSWORD") or await get_credential(db, "EMAIL_PASS")
    success, error = send_email_smtp(
        row.to_email,
        subject,
        body,
        row.to_name or "",
        gmail_address=gmail_address,
        gmail_password=gmail_password,
    )
    if success:
        row.status = "sent"
        row.sent_at = datetime.now(timezone.utc)
        row.subject = subject
        row.body = body
    else:
        row.status = "failed"
        row.error = error

    await db.flush()

    try:
        from app.services.notifications.telegram import notify_telegram

        icon = "OK" if success else "FAILED"
        await notify_telegram(f"{icon} Email {'sent' if success else 'failed'}: {row.subject} -> {row.to_email}")
    except Exception:
        pass

    return success
