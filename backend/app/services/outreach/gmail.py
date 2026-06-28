"""Executive email transport for outreach and proposals.

This module preserves the legacy import path used across the codebase while the
runtime is migrated to AWS SES as the sovereign outbound provider.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.communication import CommunicationChannel, CommunicationDirection
from app.models.outreach import OutreachEmail
from app.services.communication.client_language import sanitize_client_text
from app.services.communication.ledger import record_communication_event
from app.services.outreach.compliance import outreach_compliance
from app.services.outreach.email_transport import (
    get_executive_identity,
    get_outbound_email_status,
    send_outbound_email,
)

logger = logging.getLogger(__name__)
SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


def _default_tenant_id() -> uuid.UUID:
    if settings.JARVIS_DEFAULT_TENANT_ID:
        return uuid.UUID(str(settings.JARVIS_DEFAULT_TENANT_ID))
    return SYSTEM_TENANT_ID


async def _record_email_event(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    to: str,
    subject: str,
    body: str,
    to_name: str = "",
    contact_id: int | None = None,
    status: str,
    method: str,
    error: str = "",
) -> None:
    identity = get_executive_identity()
    await record_communication_event(
        db,
        tenant_id=tenant_id,
        channel=CommunicationChannel.EMAIL,
        direction=CommunicationDirection.OUTBOUND,
        transport="ses",
        from_address=identity.email,
        to_address=to,
        contact_name=to_name or None,
        contact_id=contact_id,
        subject=subject,
        body_text=body,
        status=status,
        hia_persona=identity.name,
        processing_summary={
            "method": method,
            "error": error,
            "architecture_route": [
                "HERALD Outreach Generation",
                "AWS SES Email Delivery",
                "Communication Ledger",
                "Decision Memory",
                "Client Digital Twin",
                "Institutional Wisdom",
            ],
        },
        raw_payload={"error": error} if error else {},
        processed_at=datetime.now(timezone.utc),
    )


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
    return sanitize_client_text((resp.content or "").strip() if not resp.error and resp.content else template)


async def validate_smtp_credentials(
    gmail_address: Optional[str] = None,
    gmail_password: Optional[str] = None,
) -> tuple[bool, str]:
    """Compatibility wrapper for legacy callers.

    The runtime now validates AWS SES instead of legacy SMTP.
    """
    status = await get_outbound_email_status(validate_provider=True)
    return bool(status.get("connected")), status.get("validation_error", "")


async def send_email_smtp(
    to: str,
    subject: str,
    body: str,
    to_name: str = "",
    gmail_address: Optional[str] = None,
    gmail_password: Optional[str] = None,
    attachments: Optional[list[dict]] = None,
) -> tuple[bool, str]:
    """Compatibility wrapper that now sends via AWS SES."""
    success, error, _ = await send_outbound_email(
        to,
        subject,
        body,
        to_name=to_name,
        attachments=attachments,
    )
    return success, error


async def send_outbound_message(
    to: str,
    subject: str,
    body: str,
    to_name: str = "",
    attachments: Optional[list[dict]] = None,
) -> tuple[bool, str, str]:
    return await send_outbound_email(to, subject, body, to_name=to_name, attachments=attachments)


async def send_client_email(
    db: AsyncSession,
    to: str,
    subject: str,
    body: str,
    to_name: str = "",
    attachments: Optional[list[dict]] = None,
) -> tuple[bool, str, str]:
    """Legacy compatibility wrapper used by outreach and proposal flows."""
    success, error, method = await send_outbound_email(to, subject, body, to_name=to_name, attachments=attachments)
    await _record_email_event(
        db,
        tenant_id=_default_tenant_id(),
        to=to,
        subject=subject,
        body=body,
        to_name=to_name,
        status="sent" if success else "failed",
        method=method,
        error=error,
    )
    return success, error, method


async def send_outreach_email(db: AsyncSession, email_id: int) -> bool:
    """Fetch OutreachEmail record, personalise, send, and update status."""
    from sqlalchemy import select

    row = (await db.execute(select(OutreachEmail).where(OutreachEmail.id == email_id))).scalar_one_or_none()
    if not row or row.status not in ("scheduled", "queued"):
        return False

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

    subject = row.subject or ""
    body = row.body or ""
    if row.contact_id and not row.personalized:
        from sqlalchemy import select
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
    success, error, method = await send_outbound_email(
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
    else:
        row.status = "failed"
        row.error = error

    await db.flush()
    await _record_email_event(
        db,
        tenant_id=row.tenant_id,
        to=row.to_email or "",
        subject=subject,
        body=body,
        to_name=row.to_name or "",
        contact_id=row.contact_id,
        status="sent" if success else "failed",
        method=method,
        error=error,
    )

    try:
        from app.services.notifications.telegram import notify_telegram

        icon = "OK" if success else "FAILED"
        await notify_telegram(f"{icon} Email {'sent' if success else 'failed'}: {row.subject} -> {row.to_email}")
    except Exception as exc:
        logger.warning("Telegram email dispatch notification failed for %s: %s", row.to_email, exc)

    return success


async def gmail_delivery_status(db: AsyncSession, validate_smtp: bool = True) -> dict:
    """Legacy status endpoint kept for compatibility.

    The response now reflects AWS SES rather than Gmail.
    """
    status = await get_outbound_email_status(validate_provider=validate_smtp)
    cap = {"sent_today": 0, "cap": outreach_compliance.current_daily_cap()}
    if settings.JARVIS_DEFAULT_TENANT_ID:
        try:
            cap = await outreach_compliance.daily_send_cap_status(db, uuid.UUID(str(settings.JARVIS_DEFAULT_TENANT_ID)))
        except Exception as exc:
            logger.warning("daily_send_cap_status check failed: %s", exc)
    return {
        **status,
        "daily_cap": outreach_compliance.current_daily_cap(),
        "outreach_paused": bool(status.get("outreach_paused")),
        "configured": bool(status.get("configured")),
        "validation_error": status.get("validation_error", ""),
        "daily_cap_remaining": max(0, int(cap.get("cap") or 0) - int(cap.get("sent_today") or 0)),
    }


async def email_delivery_status(db: AsyncSession, validate_provider: bool = True) -> dict:
    """Preferred name for callers moving off the legacy Gmail wording."""
    return await gmail_delivery_status(db, validate_smtp=validate_provider)
