from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.lead import Lead, LeadStatus
from app.models.outreach import (
    FollowUpQueue,
    FollowUpStatus,
    ReplyClassification,
    ReplyLog,
)
from app.services.ai.base_provider import Message, TaskType
from app.services.ai.router import ai_router
from app.services.memory.human_intelligence import human_intelligence_context
from app.services.notifications import notify_business_event
from app.services.outreach.engine import PERSONAS

logger = logging.getLogger(__name__)

REPLY_CLASSIFICATIONS = [
    "INTERESTED",
    "QUESTION",
    "NOT_NOW",
    "NO",
    "OUT_OF_OFFICE",
    "UNKNOWN",
]


class ReplyHandler:
    async def classify_reply(self, reply_text: str) -> tuple[str, float]:
        prompt = _classification_prompt(reply_text)
        try:
            response, _ = await ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=TaskType.SALES,
                force_provider="anthropic",
                force_model="claude-opus-4-7",
                max_tokens=300,
            )
            if response.error or response.demo:
                return _heuristic_classification(reply_text)
            return _parse_classification(response.content) or _heuristic_classification(reply_text)
        except Exception as exc:
            logger.warning("Reply classification failed, using heuristic fallback: %s", exc)
            return _heuristic_classification(reply_text)

    async def process_reply(self, lead_id, reply_text: str, tenant_id) -> dict:
        tenant_uuid = uuid.UUID(str(tenant_id))
        lead_uuid = uuid.UUID(str(lead_id))
        classification, confidence = await self.classify_reply(reply_text)
        lead = await self._load_lead(tenant_uuid, lead_uuid)
        if not lead:
            return {
                "lead_id": str(lead_uuid),
                "classification": classification,
                "confidence_score": confidence,
                "action_taken": "lead_not_found",
            }

        response_draft = None
        if classification in {"INTERESTED", "QUESTION"}:
            response_draft = await self.generate_response(reply_text, lead, classification)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                live_lead = await session.scalar(
                    select(Lead).where(Lead.tenant_id == tenant_uuid, Lead.id == lead_uuid)
                )
                if not live_lead:
                    return {
                        "lead_id": str(lead_uuid),
                        "classification": classification,
                        "confidence_score": confidence,
                        "action_taken": "lead_not_found",
                    }

                action_taken = await self._apply_classification(
                    session,
                    tenant_uuid,
                    live_lead,
                    classification,
                )
                session.add(
                    ReplyLog(
                        tenant_id=tenant_uuid,
                        lead_id=live_lead.id,
                        from_email=live_lead.email or live_lead.contact_email,
                        subject=None,
                        body_text=reply_text or "",
                        classification=ReplyClassification(classification),
                        confidence_score=confidence,
                        action_taken=action_taken,
                        response_draft=response_draft,
                        processed_at=datetime.now(UTC),
                    )
                )
                await self._audit(
                    session,
                    tenant_uuid,
                    "reply_processed",
                    live_lead.id,
                    {
                        "classification": classification,
                        "confidence_score": confidence,
                        "action_taken": action_taken,
                    },
                )
                from app.services.civilization import civilization_ledger

                await civilization_ledger.append_event(
                    session,
                    tenant_uuid,
                    event_type="first_reply_received",
                    title="First reply received",
                    description=(
                        f"JARVIS processed a prospect reply from "
                        f"{live_lead.company_name or live_lead.company or live_lead.email}."
                    ),
                    impact="revenue",
                    actors=["ReplyHandler", "JARVIS"],
                    data_snapshot={
                        "lead_id": str(live_lead.id),
                        "classification": classification,
                        "confidence_score": confidence,
                        "action_taken": action_taken,
                    },
                    milestone=True,
                    dedupe=True,
                )

        if classification == "INTERESTED":
            await notify_business_event(
                "interested_reply",
                f"Interested reply: {lead.company_name or lead.company or lead.email}",
                "A prospect is ready for the next step. Follow-up sequence paused and demo status set.",
            )

        return {
            "lead_id": str(lead_uuid),
            "classification": classification,
            "confidence_score": confidence,
            "action_taken": action_taken,
            "lead_status": _status_for_classification(classification),
            "response_draft": response_draft,
        }

    async def generate_response(self, reply_text: str, lead: Lead, classification: str) -> str:
        prompt = _response_prompt(reply_text, lead, classification)
        try:
            response, _ = await ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=TaskType.SALES,
                force_provider="anthropic",
                force_model="claude-opus-4-7",
                max_tokens=650,
            )
            if response.error or response.demo or not response.content.strip():
                return _fallback_response(lead, classification)
            return _clean_client_response(response.content, lead, classification)
        except Exception as exc:
            logger.warning("Reply response generation failed, using fallback: %s", exc)
            return _fallback_response(lead, classification)

    async def _load_lead(self, tenant_id: uuid.UUID, lead_id: uuid.UUID) -> Lead | None:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_id))
                return await session.scalar(
                    select(Lead).where(Lead.tenant_id == tenant_id, Lead.id == lead_id)
                )

    async def _apply_classification(
        self,
        session,
        tenant_id: uuid.UUID,
        lead: Lead,
        classification: str,
    ) -> str:
        now = datetime.now(UTC)
        if classification == "INTERESTED":
            lead.status = LeadStatus.DEMO
            lead.last_contact = now
            lead.last_contacted = now
            await _pause_followups(session, tenant_id, lead.id)
            return "demo_ready"

        if classification == "QUESTION":
            lead.status = LeadStatus.REPLIED
            lead.last_contact = now
            lead.last_contacted = now
            return "response_drafted"

        if classification == "NOT_NOW":
            lead.status = LeadStatus.NURTURE
            lead.last_contact = now
            lead.last_contacted = now
            await _pause_followups(session, tenant_id, lead.id)
            session.add(
                FollowUpQueue(
                    tenant_id=tenant_id,
                    lead_id=lead.id,
                    sequence_step=30,
                    scheduled_at=now + timedelta(days=30),
                    status=FollowUpStatus.PENDING,
                )
            )
            return "nurture_scheduled"

        if classification == "NO":
            lead.status = LeadStatus.LOST
            lead.last_contact = now
            lead.last_contacted = now
            await _pause_followups(session, tenant_id, lead.id)
            return "opted_out"

        if classification == "OUT_OF_OFFICE":
            lead.status = LeadStatus.REPLIED
            lead.last_contact = now
            lead.last_contacted = now
            return "out_of_office_logged"

        lead.status = LeadStatus.REPLIED
        lead.last_contact = now
        lead.last_contacted = now
        return "manual_review"

    async def _audit(
        self,
        session,
        tenant_id: uuid.UUID,
        action: str,
        lead_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> None:
        session.add(
            AuditLog(
                tenant_id=tenant_id,
                action=action,
                entity_type="lead",
                entity_id=lead_id,
                actor="ReplyHandler",
                after_json=payload,
                details=payload,
            )
        )


async def _pause_followups(session, tenant_id: uuid.UUID, lead_id: uuid.UUID) -> None:
    await session.execute(
        update(FollowUpQueue)
        .where(
            FollowUpQueue.tenant_id == tenant_id,
            FollowUpQueue.lead_id == lead_id,
            FollowUpQueue.status == FollowUpStatus.PENDING,
        )
        .values(status=FollowUpStatus.SKIPPED)
    )


def _classification_prompt(reply_text: str) -> str:
    labels = ", ".join(REPLY_CLASSIFICATIONS)
    return f"""
Classify this prospect reply for Aliyar Solutions.

Allowed labels: {labels}

Definitions:
- INTERESTED: wants a call, demo, meeting, more details, or next step.
- QUESTION: asks about pricing, process, timeline, services, implementation, or proof.
- NOT_NOW: postpones, says later, next quarter, not the right time.
- NO: hard rejection, unsubscribe, remove, do not contact.
- OUT_OF_OFFICE: automatic reply, vacation, away from office.
- UNKNOWN: unclear.

Return only JSON:
{{"classification":"INTERESTED","confidence":0.0}}

Reply:
{reply_text[:4000]}
""".strip()


def _response_prompt(reply_text: str, lead: Lead, classification: str) -> str:
    company = lead.company_name or lead.company or "your team"
    contact = (lead.contact_name or "there").split()[0]
    pain_points = ", ".join(lead.pain_points or []) or "operations, response time, and workflow bottlenecks"
    calendar = _calendar_line()
    return f"""
Write a client-facing reply as Darren Mitchell from Aliyar Solutions.

Human intelligence M2:
{human_intelligence_context(max_chars=1200)}

Lead:
- Company: {company}
- Contact first name: {contact}
- Industry: {lead.industry or "unknown"}
- Known pain points: {pain_points}
- Classification: {classification}

Rules:
- Natural, human, warm, and concise.
- Use "our team" or "Aliyar Solutions"; do not use first-person singular.
- Never mention AI, bots, Claude, prompts, automation internals, or internal systems.
- Do not reveal pricing. If pricing is requested, say our team can scope it accurately after a short call.
- For INTERESTED: offer the calendar link or ask for a convenient time.
- For QUESTION: answer directly and invite a short call for specifics.
- Mention demo/case-study review as the next practical step where useful.
- Keep under 150 words.
- Return only the email body.

Calendar:
{calendar}

Prospect reply:
{reply_text[:4000]}
""".strip()


def _parse_classification(text: str) -> tuple[str, float] | None:
    clean = text.strip()
    if "```" in clean:
        clean = next((part for part in clean.split("```") if "classification" in part), clean)
        clean = clean.removeprefix("json").strip()
    start = clean.find("{")
    end = clean.rfind("}")
    if start >= 0 and end > start:
        clean = clean[start:end + 1]
    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        return None
    classification = str(parsed.get("classification", "")).upper().strip()
    if classification not in REPLY_CLASSIFICATIONS:
        return None
    try:
        confidence = float(parsed.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    return classification, max(0.0, min(1.0, confidence))


def _heuristic_classification(reply_text: str) -> tuple[str, float]:
    text = f" {reply_text.lower()} "
    if any(term in text for term in ["out of office", "auto-reply", "automatic reply", "on vacation", "away from"]):
        return "OUT_OF_OFFICE", 0.9
    if any(term in text for term in ["unsubscribe", "remove me", "do not contact", "not interested", "no thanks"]):
        return "NO", 0.88
    if any(term in text for term in ["not now", "later", "next quarter", "next month", "too busy", "bad time"]):
        return "NOT_NOW", 0.82
    if any(term in text for term in ["yes", "interested", "tell me more", "schedule", "call", "demo", "meeting"]):
        return "INTERESTED", 0.84
    if any(term in text for term in ["price", "pricing", "cost", "timeline", "how long", "process", "question"]) or "?" in text:
        return "QUESTION", 0.76
    return "UNKNOWN", 0.45


def _fallback_response(lead: Lead, classification: str) -> str:
    contact = (lead.contact_name or "there").split()[0]
    calendar = _calendar_line()
    if classification == "INTERESTED":
        return (
            f"Hi {contact},\n\n"
            "That makes sense. Our team can walk through the likely improvement areas, show the demo path, "
            "and confirm where the fastest operational gain sits.\n\n"
            f"{calendar}\n\n"
            "Darren Mitchell\nAliyar Solutions"
        )
    return (
        f"Hi {contact},\n\n"
        "Good question. The exact answer depends on the current workflow, volume, and where the handoff breaks down. "
        "Our team can review that quickly and map the practical fix before discussing scope.\n\n"
        f"{calendar}\n\n"
        "Darren Mitchell\nAliyar Solutions"
    )


def _clean_client_response(text: str, lead: Lead, classification: str) -> str:
    body = text.strip()
    body = re.sub(r"(?i)\bI\b", "our team", body)
    blocked = ["AI agent", "bot", "Claude", "GPT", "prompt", "internal system"]
    if any(term.lower() in body.lower() for term in blocked):
        return _fallback_response(lead, classification)
    if classification in {"INTERESTED", "QUESTION"} and "pricing" in body.lower() and "after a short call" not in body.lower():
        return _fallback_response(lead, classification)
    return body


def _calendar_line() -> str:
    persona = PERSONAS["darren_mitchell"]
    return (
        "If useful, a 15-minute call this week would be the clean next step. "
        f"{persona['name']} can coordinate the time from Aliyar Solutions."
    )


def _status_for_classification(classification: str) -> str:
    return {
        "INTERESTED": LeadStatus.DEMO.value,
        "QUESTION": LeadStatus.REPLIED.value,
        "NOT_NOW": LeadStatus.NURTURE.value,
        "NO": LeadStatus.LOST.value,
        "OUT_OF_OFFICE": LeadStatus.REPLIED.value,
        "UNKNOWN": LeadStatus.REPLIED.value,
    }[classification]


reply_handler = ReplyHandler()
