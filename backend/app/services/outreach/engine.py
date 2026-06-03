from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from html import escape
from typing import Any

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import ApprovalRequest, ApprovalStatus, AuditLog
from app.models.lead import Lead, LeadStatus
from app.models.outreach import (
    EmailTracking,
    FollowUpQueue,
    FollowUpStatus,
    OutreachChannel,
    OutreachLog,
    OutreachStatus,
)
from app.services.ai.base_provider import Message, TaskType
from app.services.ai.router import ai_router
from app.services.intelligence.jarvis_authority import requires_captain_approval
from app.services.notifications.gmail_sender import gmail_sender

logger = logging.getLogger(__name__)

PERSONAS = {
    "darren_mitchell": {
        "name": "Darren Mitchell",
        "email": "darren.mitchell@aliyarsolutions.com",
        "role": "Client Acquisition Specialist",
        "signature": "Darren Mitchell | Client Acquisition | Aliyar Solutions",
        "style": "Direct, results-focused, professional. Leads with value.",
    }
}

SEQUENCE_DAYS = {1: 0, 2: 3, 3: 7}


class OutreachEngine:
    async def generate_sequence(self, lead: Lead, tenant_id) -> list[OutreachLog]:
        steps = await self._generate_steps_with_ai(lead)
        if not steps:
            steps = _fallback_steps(lead)

        tenant_uuid = uuid.UUID(str(tenant_id))
        persona = PERSONAS["darren_mitchell"]
        return [
            OutreachLog(
                tenant_id=tenant_uuid,
                lead_id=lead.id,
                channel=OutreachChannel.EMAIL,
                subject=step["subject"],
                body_text=step["body"],
                sent_from_persona=persona["name"],
                status=OutreachStatus.SENT,
                sequence_step=step["step"],
            )
            for step in steps
        ]

    async def queue_sequence(self, lead_id, tenant_id) -> None:
        tenant_uuid = uuid.UUID(str(tenant_id))
        lead_uuid = uuid.UUID(str(lead_id))
        now = datetime.now(UTC)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                lead = await self._get_lead(session, tenant_uuid, lead_uuid)
                logs = await self.generate_sequence(lead, tenant_uuid)
                serialized_steps = [_log_to_sequence_step(log) for log in logs]

                lead.assigned_persona = PERSONAS["darren_mitchell"]["name"]
                lead.enrichment_data = {
                    **(lead.enrichment_data or {}),
                    "outreach_sequence": serialized_steps,
                    "outreach_sequence_queued_at": now.isoformat(),
                }

                created = 0
                for log in logs:
                    existing = await session.scalar(
                        select(FollowUpQueue.id)
                        .where(
                            FollowUpQueue.tenant_id == tenant_uuid,
                            FollowUpQueue.lead_id == lead.id,
                            FollowUpQueue.sequence_step == log.sequence_step,
                            FollowUpQueue.status == FollowUpStatus.PENDING,
                        )
                        .limit(1)
                    )
                    if existing:
                        continue
                    session.add(
                        FollowUpQueue(
                            tenant_id=tenant_uuid,
                            lead_id=lead.id,
                            sequence_step=log.sequence_step,
                            scheduled_at=now + timedelta(days=SEQUENCE_DAYS.get(log.sequence_step, 0)),
                            status=FollowUpStatus.PENDING,
                        )
                    )
                    created += 1

                await self._audit(
                    session,
                    tenant_uuid,
                    "outreach_sequence_queued",
                    lead.id,
                    {"queued_items": created, "persona": PERSONAS["darren_mitchell"]["name"]},
                )

    async def execute_due_outreach(self, tenant_id, limit: int = 25, autonomy_stage: str = "outreach_emails") -> int:
        tenant_uuid = uuid.UUID(str(tenant_id))
        now = datetime.now(UTC)
        sent = 0

        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                due_items = (
                    await session.execute(
                        select(FollowUpQueue)
                        .where(
                            FollowUpQueue.tenant_id == tenant_uuid,
                            FollowUpQueue.status == FollowUpStatus.PENDING,
                            FollowUpQueue.scheduled_at <= now,
                        )
                        .order_by(FollowUpQueue.scheduled_at.asc())
                        .limit(limit)
                    )
                ).scalars().all()

                for item in due_items:
                    lead = await self._get_lead(session, tenant_uuid, item.lead_id)
                    email = _email_for_step(lead, item.sequence_step)
                    if not email:
                        logs = await self.generate_sequence(lead, tenant_uuid)
                        lead.enrichment_data = {
                            **(lead.enrichment_data or {}),
                            "outreach_sequence": [_log_to_sequence_step(log) for log in logs],
                        }
                        email = _email_for_step(lead, item.sequence_step)
                    if not email:
                        item.status = FollowUpStatus.FAILED
                        await self._audit(
                            session,
                            tenant_uuid,
                            "outreach_generation_failed",
                            lead.id,
                            {"follow_up_queue_id": str(item.id), "sequence_step": item.sequence_step},
                        )
                        continue

                    if requires_captain_approval(autonomy_stage):
                        await self._queue_captain_approval(session, tenant_uuid, lead, item, email, autonomy_stage)
                        item.status = FollowUpStatus.SKIPPED
                        item.executed_at = now
                        continue

                    if not lead.email and not lead.contact_email:
                        item.status = FollowUpStatus.FAILED
                        item.executed_at = now
                        await self._audit(
                            session,
                            tenant_uuid,
                            "outreach_missing_email",
                            lead.id,
                            {"sequence_step": item.sequence_step},
                        )
                        continue

                    to_email = lead.email or lead.contact_email
                    success = await gmail_sender.send_email(
                        to=to_email,
                        subject=email["subject"],
                        body_html=_body_html(email["body"]),
                        from_name=PERSONAS["darren_mitchell"]["name"],
                        from_email=PERSONAS["darren_mitchell"]["email"],
                    )
                    if not success:
                        item.status = FollowUpStatus.FAILED
                        item.executed_at = now
                        await self._audit(
                            session,
                            tenant_uuid,
                            "outreach_send_failed",
                            lead.id,
                            {"sequence_step": item.sequence_step},
                        )
                        continue

                    outreach = OutreachLog(
                        tenant_id=tenant_uuid,
                        lead_id=lead.id,
                        channel=OutreachChannel.EMAIL,
                        subject=email["subject"],
                        body_text=email["body"],
                        sent_from_persona=PERSONAS["darren_mitchell"]["name"],
                        sent_at=now,
                        status=OutreachStatus.SENT,
                        sequence_step=item.sequence_step,
                    )
                    session.add(outreach)
                    await session.flush()
                    session.add(EmailTracking(tenant_id=tenant_uuid, outreach_id=outreach.id))
                    item.status = FollowUpStatus.EXECUTED
                    item.executed_at = now
                    lead.status = LeadStatus.CONTACTED
                    lead.outreach_sent = True
                    lead.outreach_count = (lead.outreach_count or 0) + 1
                    lead.last_contact = now
                    lead.last_contacted = now
                    sent += 1
                    await self._audit(
                        session,
                        tenant_uuid,
                        "outreach_email_sent",
                        lead.id,
                        {
                            "sequence_step": item.sequence_step,
                            "subject": email["subject"],
                            "persona": PERSONAS["darren_mitchell"]["name"],
                        },
                    )

        return sent

    async def stats(self, tenant_id) -> dict:
        tenant_uuid = uuid.UUID(str(tenant_id))
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                pending = await session.scalar(
                    select(func.count()).select_from(FollowUpQueue).where(
                        FollowUpQueue.tenant_id == tenant_uuid,
                        FollowUpQueue.status == FollowUpStatus.PENDING,
                    )
                ) or 0
                executed = await session.scalar(
                    select(func.count()).select_from(FollowUpQueue).where(
                        FollowUpQueue.tenant_id == tenant_uuid,
                        FollowUpQueue.status == FollowUpStatus.EXECUTED,
                    )
                ) or 0
                failed = await session.scalar(
                    select(func.count()).select_from(FollowUpQueue).where(
                        FollowUpQueue.tenant_id == tenant_uuid,
                        FollowUpQueue.status == FollowUpStatus.FAILED,
                    )
                ) or 0
                sent = await session.scalar(
                    select(func.count()).select_from(OutreachLog).where(
                        OutreachLog.tenant_id == tenant_uuid,
                        OutreachLog.status == OutreachStatus.SENT,
                        OutreachLog.sent_at.is_not(None),
                    )
                ) or 0
                linkedin_drafts = await session.scalar(
                    select(func.count()).select_from(OutreachLog).where(
                        OutreachLog.tenant_id == tenant_uuid,
                        OutreachLog.channel == OutreachChannel.LINKEDIN,
                        OutreachLog.sent_at.is_(None),
                    )
                ) or 0

        return {
            "pending_followups": int(pending),
            "executed_followups": int(executed),
            "failed_followups": int(failed),
            "sent_outreach": int(sent),
            "prepared_linkedin_drafts": int(linkedin_drafts),
            "active_persona": PERSONAS["darren_mitchell"],
        }

    async def _generate_steps_with_ai(self, lead: Lead) -> list[dict]:
        prompt = _sequence_prompt(lead)
        try:
            response, _ = await ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=TaskType.SALES,
                force_provider="anthropic",
                force_model="claude-opus-4-7",
                max_tokens=1400,
            )
            if response.error:
                logger.warning("AI outreach sequence failed: %s", response.error)
                return []
            steps = _parse_steps(response.content)
            return _clean_steps(steps, lead)
        except Exception as exc:
            logger.warning("AI outreach sequence generation failed: %s", exc)
            return []

    async def _get_lead(self, session, tenant_id: uuid.UUID, lead_id: uuid.UUID | None) -> Lead:
        if not lead_id:
            raise ValueError("Lead id is required")
        lead = await session.scalar(
            select(Lead).where(Lead.tenant_id == tenant_id, Lead.id == lead_id)
        )
        if not lead:
            raise ValueError("Lead not found")
        return lead

    async def _queue_captain_approval(
        self,
        session,
        tenant_id: uuid.UUID,
        lead: Lead,
        item: FollowUpQueue,
        email: dict,
        action_type: str,
    ) -> None:
        approval = ApprovalRequest(
            tenant_id=tenant_id,
            title=f"Approve outreach email: {lead.company_name or lead.company or lead.email}",
            action_type=action_type,
            summary=f"Outreach step {item.sequence_step} is ready but requires Captain approval.",
            risk_level="MEDIUM",
            status=ApprovalStatus.PENDING,
            raised_by="OutreachEngine",
            payload={
                "lead_id": str(lead.id),
                "follow_up_queue_id": str(item.id),
                "subject": email["subject"],
                "body": email["body"],
                "persona": PERSONAS["darren_mitchell"],
            },
        )
        session.add(approval)
        await self._audit(
            session,
            tenant_id,
            "outreach_approval_requested",
            lead.id,
            {"approval_title": approval.title, "sequence_step": item.sequence_step},
        )

    async def _audit(self, session, tenant_id: uuid.UUID, action: str, lead_id: uuid.UUID, payload: dict) -> None:
        session.add(
            AuditLog(
                tenant_id=tenant_id,
                action=action,
                entity_type="lead",
                entity_id=lead_id,
                actor="OutreachEngine",
                after_json=payload,
                details=payload,
            )
        )


def _sequence_prompt(lead: Lead) -> str:
    company = lead.company_name or lead.company or "the company"
    contact = lead.contact_name or "there"
    industry = lead.industry or "their market"
    pain_points = ", ".join(lead.pain_points or []) or "manual coordination, missed follow-ups, slow operations"
    website = lead.website or lead.company_website or "unknown"
    return f"""
Write a 3-step cold outreach sequence for Aliyar Solutions as Darren Mitchell.

Lead:
- Company: {company}
- Contact: {contact}
- Industry: {industry}
- Website: {website}
- Known pain points: {pain_points}
- Opportunity type: {lead.opportunity_type or "operations improvement"}

Rules:
- Return only valid JSON array with 3 objects.
- Each object must have: step, subject, body.
- Step 1 is day 1: specific observation, one concrete likely problem, soft CTA for 15 minutes.
- Step 2 is day 4: reference the earlier note, one quantified result example, offer to show the approach.
- Step 3 is day 8: acknowledge timing, final value statement, easy out.
- Do not reveal pricing.
- Do not mention AI, bots, Claude, prompts, or internal systems.
- Do not use first-person singular language. Avoid "I", "me", "my", "we hope", and generic pleasantries.
- Use "our team", "Aliyar Solutions", or named specialist team language.
- Keep each body under 120 words.
""".strip()


def _fallback_steps(lead: Lead) -> list[dict]:
    company = lead.company_name or lead.company or "your team"
    first_name = (lead.contact_name or "there").split()[0]
    industry = lead.industry or "your sector"
    pain = _first_pain(lead)
    return [
        {
            "step": 1,
            "subject": f"Quick question about {company}'s operations",
            "body": (
                f"Hi {first_name},\n\n"
                f"Aliyar Solutions reviewed {company}'s public footprint and noticed a likely operations gap around {pain}.\n\n"
                "Our operations team helps businesses reduce manual work, tighten customer response time, and make delivery easier to manage as volume grows.\n\n"
                "Would a 15-minute conversation this week make sense?"
                "\n\nDarren Mitchell | Client Acquisition | Aliyar Solutions"
            ),
        },
        {
            "step": 2,
            "subject": f"Results for similar {industry} teams",
            "body": (
                f"Hi {first_name},\n\n"
                "Following up on the earlier note. Our team has helped similar operators cut repetitive admin by 60-70% while improving follow-up consistency.\n\n"
                f"For {company}, the first useful step would be mapping the current customer and operations flow, then showing exactly where the fastest gains sit.\n\n"
                "Would it be useful to see the approach?"
                "\n\nDarren Mitchell | Client Acquisition | Aliyar Solutions"
            ),
        },
        {
            "step": 3,
            "subject": f"Last note, {first_name}",
            "body": (
                f"Hi {first_name},\n\n"
                "Timing may not be right, so this will be the final note for now.\n\n"
                f"The reason {company} stood out is that the visible workflow signals suggest there may be avoidable manual effort, slower response times, or lost follow-up opportunities.\n\n"
                "If improving that becomes a priority, Aliyar Solutions can show a practical path in one short call."
                "\n\nDarren Mitchell | Client Acquisition | Aliyar Solutions"
            ),
        },
    ]


def _parse_steps(text: str) -> list[dict]:
    clean = text.strip()
    if "```" in clean:
        parts = clean.split("```")
        clean = next((part for part in parts if "[" in part and "]" in part), clean)
        clean = clean.removeprefix("json").strip()
    start = clean.find("[")
    end = clean.rfind("]")
    if start >= 0 and end > start:
        clean = clean[start:end + 1]
    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _clean_steps(steps: list[dict], lead: Lead) -> list[dict]:
    fallback = _fallback_steps(lead)
    cleaned = []
    for index in range(3):
        candidate = steps[index] if index < len(steps) else {}
        step = int(candidate.get("step") or index + 1)
        subject = str(candidate.get("subject") or fallback[index]["subject"]).strip()
        body = str(candidate.get("body") or fallback[index]["body"]).strip()
        if _has_blocked_client_language(subject) or _has_blocked_client_language(body):
            subject = fallback[index]["subject"]
            body = fallback[index]["body"]
        cleaned.append({"step": step, "subject": subject, "body": body})
    return cleaned


def _has_blocked_client_language(text: str) -> bool:
    lowered = f" {text.lower()} "
    blocked = [
        " ai ",
        " bot ",
        " claude ",
        " prompt ",
        " gpt ",
        " pricing ",
        " price is ",
        " cost is ",
        " i ",
        " me ",
        " my ",
    ]
    return any(term in lowered for term in blocked)


def _log_to_sequence_step(log: OutreachLog) -> dict:
    return {
        "step": log.sequence_step,
        "subject": log.subject,
        "body": log.body_text,
        "persona": log.sent_from_persona,
    }


def _email_for_step(lead: Lead, step: int) -> dict | None:
    sequence = (lead.enrichment_data or {}).get("outreach_sequence") or []
    for item in sequence:
        if int(item.get("step") or 0) == int(step):
            return {"subject": item.get("subject") or "", "body": item.get("body") or ""}
    return None


def _body_html(body_text: str) -> str:
    return escape(body_text).replace("\n", "<br>")


def _first_pain(lead: Lead) -> str:
    if lead.pain_points:
        return str(lead.pain_points[0]).lower()
    return "manual follow-up and customer coordination"


outreach_engine = OutreachEngine()
