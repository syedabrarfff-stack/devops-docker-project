"""SES Inbound Email Processing Service.

Handles SNS notifications from AWS SES receipt rules.
When a client replies to an outreach email, SES fires an SNS notification
to this endpoint, which processes the reply through:
  1. Communication Ledger (record event)
  2. Lead matching (find the lead by sender email)
  3. Reply Handler (classify + generate response)
  4. Orchestration Cortex (fire LEAD_INTERESTED or EMAIL_REPLY_RECEIVED cascade)
  5. Digital Twin (update client profile)
  6. Decision Memory (create decision object)
  7. Captain Notification (if INTERESTED)

AWS Setup required:
  - SES receipt rule: route emails to SNS topic
  - SNS topic subscription: HTTP endpoint POST /api/v1/webhooks/email/inbound
  - SES must be out of sandbox (or use verified email for testing)
"""
from __future__ import annotations

import base64
import email as email_lib
import json
import logging
import uuid
from datetime import UTC, datetime
from email.header import decode_header
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.communication import CommunicationChannel, CommunicationDirection
from app.models.lead import Lead
from app.services.aionx.orchestration_cortex import fire_event
from app.services.communication.ledger import record_communication_event
from app.services.memory.manager import store_memory
from app.services.outreach.reply_handler import reply_handler

logger = logging.getLogger(__name__)

SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


def _default_tenant() -> uuid.UUID:
    if settings.JARVIS_DEFAULT_TENANT_ID:
        return uuid.UUID(str(settings.JARVIS_DEFAULT_TENANT_ID))
    return SYSTEM_TENANT_ID


def _decode_header_value(value: str) -> str:
    if not value:
        return ""
    try:
        parts = decode_header(value)
        decoded = []
        for part, enc in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(enc or "utf-8", errors="replace"))
            else:
                decoded.append(str(part))
        return " ".join(decoded).strip()
    except Exception:
        return str(value).strip()


def _extract_body(msg) -> tuple[str, str]:
    plain, html = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            if "attachment" in disposition:
                continue
            try:
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                charset = part.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
                if ct == "text/plain" and not plain:
                    plain = decoded
                elif ct == "text/html" and not html:
                    html = decoded
            except Exception:
                continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                plain = payload.decode(charset, errors="replace")
        except Exception:
            pass
    return plain, html


def _extract_reply_text(plain: str, html: str) -> str:
    text = plain or html
    if not text:
        return ""
    lines = text.splitlines()
    clean = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(">") or stripped.startswith("On ") and "wrote:" in stripped:
            break
        clean.append(line)
    result = "\n".join(clean).strip()
    return result[:4000] if result else text[:4000]


async def _confirm_sns_subscription(subscribe_url: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.get(subscribe_url)
        logger.info("SNS subscription confirmed")
    except Exception as exc:
        logger.warning("SNS subscription confirmation failed: %s", exc)


async def _find_lead(db: AsyncSession, tenant_id: uuid.UUID, email_addr: str) -> Lead | None:
    normalized = (email_addr or "").lower().strip()
    if not normalized:
        return None
    result = await db.execute(
        select(Lead).where(
            Lead.tenant_id == tenant_id,
            Lead.email == normalized,
        ).limit(1)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        result = await db.execute(
            select(Lead).where(
                Lead.tenant_id == tenant_id,
                Lead.contact_email == normalized,
            ).limit(1)
        )
        lead = result.scalar_one_or_none()
    return lead


async def process_ses_sns_notification(raw_body: bytes) -> dict[str, Any]:
    """Entry point for SNS HTTP/HTTPS endpoint.

    Handles:
      - SubscriptionConfirmation  (one-time setup)
      - Notification              (actual email delivery event)
    """
    tenant_id = _default_tenant()

    try:
        body = json.loads(raw_body)
    except Exception:
        return {"accepted": False, "error": "invalid_json"}

    msg_type = body.get("Type", "")

    # SNS subscription confirmation — auto-confirm
    if msg_type == "SubscriptionConfirmation":
        sub_url = body.get("SubscribeURL")
        if sub_url:
            await _confirm_sns_subscription(sub_url)
        return {"accepted": True, "action": "subscription_confirmed"}

    if msg_type != "Notification":
        return {"accepted": True, "action": "ignored", "type": msg_type}

    # Parse the SES notification
    try:
        message = json.loads(body.get("Message", "{}"))
    except Exception:
        return {"accepted": False, "error": "invalid_ses_message"}

    notification_type = message.get("notificationType") or message.get("eventType", "")

    # Bounce / Complaint — add to do-not-contact
    if notification_type in ("Bounce", "Complaint"):
        return await _handle_bounce_or_complaint(tenant_id, notification_type, message)

    # Inbound email delivery via SES receipt rule
    receipt = message.get("receipt") or {}
    mail = message.get("mail") or {}

    raw_email_content = ""
    content_obj = message.get("content") or ""
    if isinstance(content_obj, str):
        raw_email_content = content_obj
    elif receipt.get("action", {}).get("type") == "S3":
        # Email stored in S3 — would need S3 fetch here (future)
        raw_email_content = ""

    from_addresses = (mail.get("source") or "").split(",")
    from_email = (from_addresses[0] if from_addresses else "").strip().lower()
    headers_list = mail.get("headers") or mail.get("commonHeaders") or {}
    subject = ""
    if isinstance(headers_list, dict):
        subject = headers_list.get("subject") or headers_list.get("Subject") or ""
    elif isinstance(headers_list, list):
        for h in headers_list:
            if isinstance(h, dict) and h.get("name", "").lower() == "subject":
                subject = h.get("value", "")
                break

    plain_text, html_text = "", ""
    if raw_email_content:
        try:
            parsed = email_lib.message_from_string(raw_email_content)
            if not subject:
                subject = _decode_header_value(parsed.get("Subject") or "")
            if not from_email:
                from_email = _decode_header_value(parsed.get("From") or "")
            plain_text, html_text = _extract_body(parsed)
        except Exception as exc:
            logger.warning("SES inbound email parse error: %s", exc)

    reply_text = _extract_reply_text(plain_text, html_text)

    if not from_email:
        return {"accepted": True, "action": "ignored_no_sender"}

    async with AsyncSessionLocal() as db:
        async with db.begin():
            await set_tenant_context(db, str(tenant_id))
            lead = await _find_lead(db, tenant_id, from_email)
            lead_id = lead.id if lead else None

            event = await record_communication_event(
                db,
                tenant_id=tenant_id,
                channel=CommunicationChannel.EMAIL,
                direction=CommunicationDirection.INBOUND,
                transport="ses_inbound",
                from_address=from_email,
                to_address=settings.EXECUTIVE_EMAIL_ADDRESS or "",
                contact_name=(lead.contact_name if lead else None),
                lead_id=lead_id,
                subject=subject[:500] if subject else None,
                body_text=reply_text[:4000] if reply_text else None,
                status="received",
                hia_persona=settings.EXECUTIVE_EMAIL_NAME or "Joseph David",
                processing_summary={
                    "notification_type": notification_type,
                    "lead_matched": bool(lead_id),
                    "architecture_route": [
                        "AWS SES Receipt Rule",
                        "SNS Notification",
                        "JARVIS Inbound Endpoint",
                        "Communication Ledger",
                        "Reply Handler",
                        "Orchestration Cortex",
                        "Digital Twin",
                        "Decision Memory",
                    ],
                },
                raw_payload=message,
                processed_at=datetime.now(UTC),
            )

    processing: dict[str, Any] = {
        "event_id": str(event.id),
        "from_email": from_email,
        "subject": subject,
        "lead_matched": bool(lead_id),
        "reply_text_length": len(reply_text),
    }

    if lead_id and reply_text:
        reply_result = await reply_handler.process_reply(lead_id, reply_text, tenant_id)
        processing["reply_handler"] = reply_result

        async with AsyncSessionLocal() as db:
            async with db.begin():
                await store_memory(
                    db,
                    content=(
                        f"Email reply from {lead.company_name or lead.company or from_email}: "
                        f"{reply_text[:700]}"
                    ),
                    memory_type="episodic",
                    importance=0.80,
                    tags=["email_reply", "ses_inbound", "client_digital_twin", "decision_memory"],
                    key=f"ses_inbound:{lead_id}:{event.id}",
                )
                await fire_event(
                    db,
                    "EMAIL_REPLY_RECEIVED",
                    {
                        "event_type": "EMAIL_REPLY_RECEIVED",
                        "event_id": str(event.id),
                        "client_id": str(lead_id),
                        "lead_id": str(lead_id),
                        "interaction_type": "EMAIL_REPLY",
                        "summary": reply_text[:500],
                        "problem": f"Email reply from {lead.company_name or from_email} — classify and respond.",
                        "category": "OUTREACH",
                        "confidence": reply_result.get("confidence_score", 0.7),
                    },
                )
    elif lead_id:
        # Has lead but no extractable text — record the event only
        processing["action"] = "event_recorded_no_text"
    else:
        # Unknown sender — log for Captain review
        processing["action"] = "unknown_sender_logged"
        logger.info("SES inbound from unknown sender: %s subject=%s", from_email, subject)

    return {"accepted": True, "processing": processing}


async def _handle_bounce_or_complaint(
    tenant_id: uuid.UUID,
    notification_type: str,
    message: dict[str, Any],
) -> dict[str, Any]:
    from app.services.outreach.compliance import outreach_compliance

    affected_emails: list[str] = []
    if notification_type == "Bounce":
        bounce = message.get("bounce") or {}
        recipients = bounce.get("bouncedRecipients") or []
        for r in recipients:
            addr = (r.get("emailAddress") or "").lower().strip()
            if addr:
                affected_emails.append(addr)
    elif notification_type == "Complaint":
        complaint = message.get("complaint") or {}
        recipients = complaint.get("complainedRecipients") or []
        for r in recipients:
            addr = (r.get("emailAddress") or "").lower().strip()
            if addr:
                affected_emails.append(addr)

    added = 0
    async with AsyncSessionLocal() as db:
        async with db.begin():
            for addr in affected_emails:
                try:
                    await outreach_compliance.add_do_not_contact(
                        db,
                        tenant_id,
                        addr,
                        reason=notification_type.lower(),
                        source="ses_inbound",
                        notes=f"Automatic DNC from SES {notification_type} notification.",
                    )
                    added += 1
                except Exception as exc:
                    logger.warning("DNC add failed for %s: %s", addr, exc)

    return {
        "accepted": True,
        "action": f"dnc_added_{notification_type.lower()}",
        "emails_suppressed": added,
        "addresses": affected_emails,
    }
