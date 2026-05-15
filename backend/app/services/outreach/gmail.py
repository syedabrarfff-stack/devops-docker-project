"""
Gmail integration — SMTP sending (app password) + Gemini AI personalisation.
For full OAuth: set GMAIL_CLIENT_ID + GMAIL_CLIENT_SECRET (Phase 3).
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.outreach import OutreachEmail
from app.services.storage.secure import get_credential

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _gmail_app_password(password: Optional[str] = None) -> str:
    """Gmail app passwords are often copied with spaces; SMTP expects plain text."""
    return (password or settings.GMAIL_APP_PASSWORD or "").replace(" ", "").strip()


def send_email_smtp(to: str, subject: str, body: str,
                    to_name: str = "",
                    gmail_address: Optional[str] = None,
                    gmail_password: Optional[str] = None) -> tuple[bool, str]:
    """Send via Gmail SMTP using app password. Returns (success, error)."""
    sender = (gmail_address or settings.GMAIL_ADDRESS or "").strip()
    password = _gmail_app_password(gmail_password)
    if not (sender and password):
        return False, "Gmail not configured — add GMAIL_ADDRESS + GMAIL_APP_PASSWORD to .env"
    try:
        password.encode("ascii")
    except UnicodeEncodeError:
        return False, "GMAIL_APP_PASSWORD contains non-ASCII characters. Replace it with the 16-character Gmail app password."
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"Aliyar Solutions <{sender}>"
        msg["To"]      = f"{to_name} <{to}>" if to_name else to

        text_part = MIMEText(body, "plain")
        html_part = MIMEText(_wrap_html(body, to_name), "html")
        msg.attach(text_part)
        msg.attach(html_part)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, to, msg.as_string())

        logger.info(f"Email sent to {to}: {subject}")
        return True, ""
    except Exception as e:
        logger.error(f"SMTP error sending to {to}: {e}")
        return False, str(e)


def _wrap_html(body: str, name: str) -> str:
    body_html = body.replace("\n", "<br>")
    return f"""
<html><body style="font-family:Arial,sans-serif;color:#222;max-width:600px;margin:0 auto">
  <div style="background:#f8f9fa;padding:24px;border-radius:8px">
    <p>{body_html}</p>
    <hr style="border:none;border-top:1px solid #e0e0e0;margin:20px 0">
    <p style="color:#888;font-size:12px">
      Aliyar Solutions — AI Automation &amp; Cloud Consulting<br>
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
        f"Max 200 words. Return only the email body text.\n\n"
        f"TEMPLATE:\n{template}\n\nCONTACT:\n{context}"
    )
    resp, _ = await ai_router.chat(
        [Message(role="user", content=prompt)],
        task_type=TaskType.FAST,
        force_provider="google",
    )
    return resp.content if not resp.error else template


async def send_outreach_email(db: AsyncSession, email_id: int) -> bool:
    """Fetch OutreachEmail record, personalise, send, and update status."""
    from sqlalchemy import select
    row = (await db.execute(select(OutreachEmail).where(OutreachEmail.id == email_id))).scalar_one_or_none()
    if not row or row.status not in ("scheduled", "queued"):
        return False

    body = row.body or ""
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

    gmail_address = await get_credential(db, "GMAIL_ADDRESS")
    gmail_password = await get_credential(db, "GMAIL_APP_PASSWORD")
    success, error = send_email_smtp(
        row.to_email,
        row.subject or "",
        body,
        row.to_name or "",
        gmail_address=gmail_address,
        gmail_password=gmail_password,
    )
    if success:
        row.status = "sent"
        row.sent_at = datetime.now(timezone.utc)
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
