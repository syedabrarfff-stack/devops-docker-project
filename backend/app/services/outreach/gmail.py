"""
Gmail integration — SMTP sending (app password) + Gemini AI personalisation.
For full OAuth: set GMAIL_CLIENT_ID + GMAIL_CLIENT_SECRET (Phase 3).
"""
import smtplib
import logging
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.outreach import OutreachEmail
from app.services.communication.client_language import sanitize_client_text, sanitize_subject_body
from app.services.storage.secure import get_credential

logger = logging.getLogger(__name__)

def _gmail_app_password(password: Optional[str] = None) -> str:
    """Gmail app passwords are often copied with spaces; SMTP expects plain text."""
    return (password or settings.GMAIL_APP_PASSWORD or settings.EMAIL_PASS or "").replace(" ", "").strip()


def _smtp_error_message(exc: Exception) -> str:
    text = str(exc)
    lowered = text.lower()
    if "5.7.8" in text or "badcredentials" in lowered or "username and password not accepted" in lowered:
        return "Google rejected the Gmail SMTP credentials (535 BadCredentials). Generate a fresh app password for the sender account or connect Gmail OAuth."
    if "timed out" in lowered or "timeout" in lowered:
        return "Gmail SMTP connection timed out."
    if "authentication" in lowered or "auth" in lowered:
        return "Gmail SMTP authentication failed."
    return text.splitlines()[0][:240]


def send_email_smtp(to: str, subject: str, body: str,
                    to_name: str = "",
                    gmail_address: Optional[str] = None,
                    gmail_password: Optional[str] = None,
                    attachments: Optional[list[dict]] = None) -> tuple[bool, str]:
    """Send via Gmail SMTP using app password. Returns (success, error)."""
    sender = (gmail_address or settings.GMAIL_ADDRESS or settings.GMAIL_USER or settings.EMAIL_USER or "").strip()
    password = _gmail_app_password(gmail_password)
    if not (sender and password):
        return False, "Gmail not configured — add GMAIL_ADDRESS + GMAIL_APP_PASSWORD to .env"
    try:
        password.encode("ascii")
    except UnicodeEncodeError:
        return False, "GMAIL_APP_PASSWORD contains non-ASCII characters. Replace it with the 16-character Gmail app password."
    if len(password) != 16:
        return False, "GMAIL_APP_PASSWORD must be the real 16-character Google app password."
    try:
        subject, body = sanitize_subject_body(subject, body)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"Aliyar Solutions <{sender}>"
        msg["To"]      = f"{to_name} <{to}>" if to_name else to

        text_part = MIMEText(body, "plain")
        html_part = MIMEText(_wrap_html(body, to_name), "html")
        msg.attach(text_part)
        msg.attach(html_part)

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

        logger.info(f"Email sent to {to}: {subject}")
        return True, ""
    except Exception as e:
        error = _smtp_error_message(e)
        logger.error("SMTP error sending to %s: %s", to, error)
        return False, error


def validate_smtp_credentials(
    gmail_address: Optional[str] = None,
    gmail_password: Optional[str] = None,
) -> tuple[bool, str]:
    """Verify SMTP handshake + auth without sending a message."""
    sender = (gmail_address or settings.GMAIL_ADDRESS or settings.GMAIL_USER or settings.EMAIL_USER or "").strip()
    password = _gmail_app_password(gmail_password)
    if not (sender and password):
        return False, "Gmail sender or app password is missing."
    try:
        password.encode("ascii")
    except UnicodeEncodeError:
        return False, "Gmail app password contains non-ASCII characters."
    if len(password) != 16:
        return False, "Gmail app password must be 16 characters."
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


def _wrap_html(body: str, name: str) -> str:
    body = sanitize_client_text(body)
    body_html = body.replace("\n", "<br>")
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
    """Use Gemini to personalise an email template with contact context."""
    from app.services.ai.router import ai_router
    from app.services.ai.base_provider import Message, TaskType

    context = "\n".join(f"  {k}: {v}" for k, v in contact_data.items() if v)
    prompt = (
        f"Personalise this outreach email for the contact below. "
        f"Keep it professional, concise, and human. Don't change the core message. "
        f"Max 200 words. Never mention JARVIS, AI tools, agents, prompts, providers, routing, or internal infrastructure. "
        f"Return only the email body text.\n\n"
        f"TEMPLATE:\n{template}\n\nCONTACT:\n{context}"
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

    subject, body = sanitize_subject_body(row.subject or "", row.body or "")
    if row.contact_id and not row.personalized:
        from app.models.crm import Contact
        contact = (await db.execute(select(Contact).where(Contact.id == row.contact_id))).scalar_one_or_none()
        if contact:
            body = await personalise_email(body, {
                "name": contact.name, "title": contact.title,
                "company": getattr(contact.company, "name", ""),
                "country": contact.country,
            })
            row.personalized = True

    try:
        from app.services.auth.gmail_oauth import send_via_gmail_api

        success, error = await send_via_gmail_api(
            db,
            row.to_email,
            subject,
            body,
            row.to_name or "",
        )
        if success:
            row.status = "sent"
            row.sent_at = datetime.now(timezone.utc)
            row.subject = subject
            row.body = body
            await db.flush()
            return True
        if "No valid Gmail OAuth token" not in error:
            logger.warning("Gmail API send failed; falling back to SMTP: %s", error)
    except Exception as exc:
        logger.warning("Gmail API send path unavailable; falling back to SMTP: %s", exc)

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
        row.body = body  # save personalised version
    else:
        row.status = "failed"
        row.error = error

    await db.flush()

    # Telegram alert
    try:
        from app.services.notifications.telegram import notify_telegram
        icon = "✅" if success else "❌"
        await notify_telegram(f"{icon} Email {'sent' if success else 'failed'}: {row.subject} → {row.to_email}")
    except Exception:
        pass

    return success
