from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.lead import Lead
from app.models.outreach import OutreachChannel, OutreachLog, OutreachStatus
from app.services.outreach.engine import PERSONAS


class LinkedInOutreachService:
    async def prepare_message(self, tenant_id, lead_id, message_type: int) -> dict[str, Any]:
        tenant_uuid = _coerce_uuid(tenant_id)
        lead_uuid = _coerce_uuid(lead_id)
        normalized_type = 2 if int(message_type or 1) == 2 else 1

        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                lead = await session.scalar(
                    select(Lead).where(Lead.tenant_id == tenant_uuid, Lead.id == lead_uuid)
                )
                if not lead:
                    raise ValueError("Lead not found")

                linkedin_url = _linkedin_url(lead)
                message = _message_for_type(lead, normalized_type)
                subject = (
                    "LinkedIn connection request"
                    if normalized_type == 1
                    else "LinkedIn follow-up after connection"
                )

                existing = await session.scalar(
                    select(OutreachLog)
                    .where(
                        OutreachLog.tenant_id == tenant_uuid,
                        OutreachLog.lead_id == lead.id,
                        OutreachLog.channel == OutreachChannel.LINKEDIN,
                        OutreachLog.sequence_step == normalized_type,
                        OutreachLog.body_text == message,
                    )
                    .limit(1)
                )
                if existing:
                    outreach = existing
                else:
                    outreach = OutreachLog(
                        tenant_id=tenant_uuid,
                        lead_id=lead.id,
                        channel=OutreachChannel.LINKEDIN,
                        subject=subject,
                        body_text=message,
                        sent_from_persona=PERSONAS["darren_mitchell"]["name"],
                        sent_at=None,
                        status=OutreachStatus.SENT,
                        sequence_step=normalized_type,
                    )
                    session.add(outreach)
                    await session.flush()

                enrichment = dict(lead.enrichment_data or {})
                messages = list(enrichment.get("linkedin_messages") or [])
                if not any(item.get("message_type") == normalized_type for item in messages):
                    messages.append(
                        {
                            "message_type": normalized_type,
                            "message": message,
                            "outreach_log_id": str(outreach.id),
                            "prepared_at": datetime.now(UTC).isoformat(),
                        }
                    )
                enrichment.update(
                    {
                        "linkedin_sequence_ready": bool(linkedin_url),
                        "linkedin_url": linkedin_url or enrichment.get("linkedin_url"),
                        "linkedin_last_message_type": normalized_type,
                        "linkedin_messages": messages,
                    }
                )
                lead.enrichment_data = enrichment

                audit_payload = {
                    "lead_id": str(lead.id),
                    "message_type": normalized_type,
                    "linkedin_sequence_ready": bool(linkedin_url),
                    "outreach_log_id": str(outreach.id),
                }
                session.add(
                    AuditLog(
                        tenant_id=tenant_uuid,
                        action="linkedin_outreach_message_prepared",
                        entity_type="lead",
                        entity_id=lead.id,
                        actor="LinkedInOutreachService",
                        after_json=audit_payload,
                        details=audit_payload,
                    )
                )

        return {
            "lead_id": str(lead_uuid),
            "company": _company_name(lead),
            "linkedin_url": linkedin_url,
            "linkedin_sequence_ready": bool(linkedin_url),
            "message_type": normalized_type,
            "message": message,
            "char_count": len(message),
            "max_chars": 300 if normalized_type == 1 else 500,
            "outreach_log_id": str(outreach.id),
            "delivery_status": "draft_logged",
        }


linkedin_outreach_service = LinkedInOutreachService()


def _message_for_type(lead: Lead, message_type: int) -> str:
    company = _company_name(lead)
    contact = _first_name(lead)
    industry = lead.industry or lead.opportunity_type or "operations"
    pain = _primary_pain(lead)

    if message_type == 1:
        message = (
            f"Hi {contact}, Aliyar Solutions noticed {company} may be scaling {industry} workflows. "
            f"Our team helps reduce {pain} without adding admin. Open to connecting?"
        )
        return _limit(message, 300)

    message = (
        f"Thanks for connecting, {contact}. Our team was reviewing {company}'s visible {industry} workflow "
        f"and the pressure around {pain}. What is the biggest bottleneck right now: lead follow-up, reporting, "
        "or handoffs?"
    )
    return _limit(message, 500)


def _linkedin_url(lead: Lead) -> str:
    payloads = [lead.enrichment_data or {}, lead.metadata_ or {}]
    keys = (
        "linkedin_url",
        "decision_maker_linkedin",
        "contact_linkedin",
        "company_linkedin",
    )
    for payload in payloads:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        person = payload.get("person")
        if isinstance(person, dict):
            value = person.get("linkedin_url") or person.get("linkedin")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _company_name(lead: Lead) -> str:
    return lead.company_name or lead.company or "your team"


def _first_name(lead: Lead) -> str:
    name = (lead.contact_name or "").strip()
    if not name:
        return "there"
    return name.split()[0]


def _primary_pain(lead: Lead) -> str:
    if lead.pain_points:
        first = str(lead.pain_points[0]).strip()
        if first:
            return first[:90]
    enrichment = lead.enrichment_data or {}
    for key in ("pain_point", "primary_pain", "opportunity"):
        value = enrichment.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:90]
    return "manual follow-up and operational handoffs"


def _limit(value: str, max_chars: int) -> str:
    clean = " ".join(value.split())
    if len(clean) <= max_chars:
        return clean
    clipped = clean[: max_chars - 1].rsplit(" ", 1)[0].rstrip(" ,.;:")
    return clipped if len(clipped) >= max_chars - 25 else clean[:max_chars].rstrip()


def _coerce_uuid(value) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
