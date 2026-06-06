from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.middleware import record_outreach_sent
from app.models.approval import AuditLog
from app.models.lead import Lead, LeadStatus
from app.models.outreach import EmailTracking, OutreachLog, OutreachStatus
from app.services.outreach.email_transport import get_outbound_email_status, send_outbound_email

logger = logging.getLogger(__name__)


class GmailSender:
    """Legacy class name retained for compatibility.

    Internally this now uses AWS SES for outbound email and does not connect
    to Gmail or IMAP.
    """

    def __init__(self) -> None:
        self._connection_cache = {"checked_at": 0.0, "result": False}

    async def test_connection(self, *, force: bool = False, ttl_seconds: int = 300) -> bool:
        status = await get_outbound_email_status(validate_provider=True)
        connected = bool(status.get("connected"))
        self._connection_cache = {"checked_at": datetime.now().timestamp(), "result": connected}
        if not connected:
            await self._audit_failure(
                "email_connection_test_failed",
                {
                    "from_email": status.get("from_email"),
                    "error": status.get("validation_error") or status.get("human_message"),
                    "provider": status.get("provider"),
                },
            )
        return connected

    async def send_email(
        self,
        to: str,
        subject: str,
        body_html: str | None = None,
        from_name: str = "",
        from_email: str = "",
        body: str | None = None,
    ) -> bool:
        body_html = body_html if body_html is not None else (body or "")
        success, error, _ = await send_outbound_email(
            to=to,
            subject=subject,
            body=body_html,
            to_name="",
            reply_to=from_email or None,
        )
        if not success:
            await self._audit_failure(
                "email_send_failed",
                {"to": to, "subject": subject, "error": error, "provider": "ses"},
            )
        return success

    async def send_outreach(self, outreach: OutreachLog) -> bool:
        if not outreach.tenant_id:
            logger.warning("Outreach send skipped: outreach has no tenant_id")
            return False

        tenant_id = UUID(str(outreach.tenant_id))
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
                    from_name=row.sent_from_persona or settings.EXECUTIVE_EMAIL_NAME,
                    from_email=settings.SES_FROM_EMAIL or settings.EXECUTIVE_EMAIL_ADDRESS,
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
                        {"to": to_email, "subject": row.subject, "provider": "ses"},
                    )
                    record_outreach_sent(row.channel.value if row.channel else "EMAIL", row.sent_from_persona)
                else:
                    row.status = OutreachStatus.BOUNCED
                    await self._audit(
                        session,
                        tenant_id,
                        "outreach_email_send_failed",
                        row.id,
                        {"to": to_email, "subject": row.subject, "provider": "ses"},
                    )
                return success

    async def check_replies(self, tenant_id) -> list[dict]:
        logger.info("Inbound email is not yet wired to SES. Reply checks are currently disabled.")
        return []

    async def _load_outreach(self, session, tenant_id: UUID, outreach: OutreachLog) -> OutreachLog | None:
        if outreach.id:
            return await session.scalar(
                select(OutreachLog).where(OutreachLog.tenant_id == tenant_id, OutreachLog.id == outreach.id)
            )
        session.add(outreach)
        await session.flush()
        return outreach

    async def _audit(self, session, tenant_id: UUID, action: str, entity_id: UUID, details: dict) -> None:
        session.add(
            AuditLog(
                tenant_id=tenant_id,
                action=action,
                entity_type="outreach",
                entity_id=entity_id,
                actor="ExecutiveEmailSender",
                after_json=details,
                details=details,
            )
        )

    async def _audit_failure(self, action: str, details: dict) -> None:
        if not settings.JARVIS_DEFAULT_TENANT_ID:
            return
        tenant_id = UUID(str(settings.JARVIS_DEFAULT_TENANT_ID))
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_id))
                session.add(
                    AuditLog(
                        tenant_id=tenant_id,
                        action=action,
                        entity_type="email",
                        actor="ExecutiveEmailSender",
                        after_json=details,
                        details=details,
                    )
                )


def _wrap_html(body_text: str, outreach_id: UUID | None) -> str:
    from app.services.outreach.gmail_inbox import _linkify_body, _tracking_pixel_url

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


gmail_sender = GmailSender()

