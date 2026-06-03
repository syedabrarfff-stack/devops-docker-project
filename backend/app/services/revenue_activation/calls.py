from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.lead import Lead, LeadStatus
from app.models.outreach import FollowUpQueue, FollowUpStatus
from app.services.agents.liaison import client_liaison_service
from app.services.outreach.engine import PERSONAS
from app.services.revenue_activation.teaching_engine import teaching_engine

CALL_FOLLOW_UP_STEP = 91


class CallRoomService:
    async def pre_brief(self, lead_id, tenant_id=None) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        lead = await self._load_lead(tenant_uuid, lead_id)
        agent_slug = _agent_for_lead(lead)
        liaison_packet = await client_liaison_service.prepare_call(
            agent_slug,
            tenant_uuid,
            lead_id=lead.id,
            call_topic="first revenue discovery call",
            call_objective="confirm the real pain, secure case-study context, and earn permission to send a tailored demo path",
        )
        confidence = _confidence_score(lead, liaison_packet)
        pre_brief = {
            "lead_id": str(lead.id),
            "company": lead.company_name or lead.company,
            "assigned_liaison": liaison_packet["agent"],
            "client_context": liaison_packet["briefing_document"].get("client_context", {}),
            "known_issues": liaison_packet["briefing_document"].get("known_issues", []),
            "what_to_say": liaison_packet["approved_script"],
            "what_not_to_say": liaison_packet["what_to_avoid"],
            "pricing_anchor": _pricing_anchor(lead),
            "objection_handlers": liaison_packet["objection_handlers"],
            "jarvis_confidence_score": confidence,
            "council_briefing_gate": liaison_packet["council_briefing_gate"],
        }
        await self._audit(tenant_uuid, "call_pre_brief_generated", lead.id, pre_brief)
        return pre_brief

    async def live_support(self, lead_id, tenant_id=None) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        lead = await self._load_lead(tenant_uuid, lead_id)
        company = lead.company_name or lead.company or "the prospect"
        pain = lead.pain_points or ["manual follow-up", "slow reporting", "limited workflow visibility"]
        return {
            "lead_id": str(lead.id),
            "company": company,
            "questions_to_ask": [
                "Where does the customer or internal request slow down most often?",
                "Which handoff still depends on memory, spreadsheets, or manual checking?",
                "What would improve first if that workflow became visible in one place?",
                "Who needs to trust the system before your team changes the process?",
                "Would a short case-study style demo around that exact workflow be relevant?",
            ],
            "danger_phrases_to_avoid": [
                "This is powered by AI.",
                "We can automate everything.",
                "Here is the price.",
                "Just book a call.",
                "It is easy.",
            ],
            "how_to_close": [
                f"Confirm the one pain point that matters most for {company}: {pain[0] if pain else 'workflow friction'}.",
                "Ask for the missing context needed to prepare a realistic case-study demo.",
                "Close on the next practical step: permission to send the tailored demo path or schedule a focused review.",
            ],
            "objection_responses": [
                {
                    "objection": "We already have tools.",
                    "response": "That helps. The question is not whether tools exist, but where the current flow still leaks time or follow-up.",
                },
                {
                    "objection": "We are not ready to spend.",
                    "response": "That is fair. Our team can keep this at the case-study stage first so there is no scope discussion until the value is clear.",
                },
            ],
            "jarvis_confidence_score": round(min(95.0, 55.0 + float(lead.score or 0) * 0.35), 2),
        }

    async def debrief(
        self,
        *,
        lead_id,
        call_outcome: str,
        notes: str,
        tenant_id=None,
        next_action: str | None = None,
    ) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        outcome = (call_outcome or "follow-up").lower().strip()
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                lead = await session.scalar(
                    select(Lead).where(Lead.tenant_id == tenant_uuid, Lead.id == uuid.UUID(str(lead_id)))
                )
                if not lead:
                    raise ValueError("Lead not found")
                lead.status = _status_for_outcome(outcome)
                resolved_next_action = next_action or _next_action_for_outcome(outcome)
                lead.notes = _append_note(lead.notes, f"Call debrief ({outcome}): {notes}")
                lead.enrichment_data = {
                    **(lead.enrichment_data or {}),
                    "last_call_debrief": {
                        "outcome": outcome,
                        "notes": notes,
                        "next_action": resolved_next_action,
                        "recorded_at": datetime.now(UTC).isoformat(),
                    },
                }
                if outcome in {"follow-up", "won"}:
                    await self._schedule_next_action(session, tenant_uuid, lead, resolved_next_action)
                session.add(
                    AuditLog(
                        tenant_id=tenant_uuid,
                        action="call_debrief_recorded",
                        entity_type="lead",
                        entity_id=lead.id,
                        actor="CallRoomService",
                        details={
                            "outcome": outcome,
                            "notes": notes[:1000],
                            "next_action": resolved_next_action,
                        },
                        after_json={
                            "status": lead.status.value,
                            "next_action": resolved_next_action,
                        },
                    )
                )
                await session.flush()
                lead_snapshot = lead

        learning = await teaching_engine.learn_from_call_debrief(
            tenant_id=tenant_uuid,
            lead=lead_snapshot,
            call_outcome=outcome,
            notes=notes,
            next_action=resolved_next_action,
        )
        return {
            "lead_id": str(lead_snapshot.id),
            "status": lead_snapshot.status.value,
            "outcome": outcome,
            "next_action": resolved_next_action,
            "learning": learning,
        }

    async def _load_lead(self, tenant_uuid, lead_id) -> Lead:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                lead = await session.scalar(
                    select(Lead).where(Lead.tenant_id == tenant_uuid, Lead.id == uuid.UUID(str(lead_id)))
                )
                if not lead:
                    raise ValueError("Lead not found")
                return lead

    async def _schedule_next_action(self, session, tenant_uuid, lead: Lead, next_action: str) -> None:
        sequence = list((lead.enrichment_data or {}).get("outreach_sequence") or [])
        sequence = [item for item in sequence if int(item.get("step") or 0) != CALL_FOLLOW_UP_STEP]
        sequence.append(
            {
                "step": CALL_FOLLOW_UP_STEP,
                "subject": "Next step from our call",
                "body": (
                    f"Hi {(lead.contact_name or 'there').split()[0]} - thank you for sharing the context around {lead.company_name or lead.company or 'your team'}. "
                    f"Our team noted the next useful step: {next_action}. "
                    "Would this be relevant enough for Aliyar Solutions to prepare the case-study path? "
                    "Darren Mitchell, Client Acquisition Specialist, Aliyar Solutions."
                ),
                "persona": PERSONAS["darren_mitchell"]["name"],
                "source": "call_debrief",
            }
        )
        lead.enrichment_data = {**(lead.enrichment_data or {}), "outreach_sequence": sequence}
        existing = await session.scalar(
            select(FollowUpQueue.id)
            .where(
                FollowUpQueue.tenant_id == tenant_uuid,
                FollowUpQueue.lead_id == lead.id,
                FollowUpQueue.sequence_step == CALL_FOLLOW_UP_STEP,
                FollowUpQueue.status == FollowUpStatus.PENDING,
            )
            .limit(1)
        )
        if not existing:
            session.add(
                FollowUpQueue(
                    tenant_id=tenant_uuid,
                    lead_id=lead.id,
                    sequence_step=CALL_FOLLOW_UP_STEP,
                    scheduled_at=datetime.now(UTC) + timedelta(hours=18),
                    status=FollowUpStatus.PENDING,
                )
            )

    async def _audit(self, tenant_uuid, action: str, lead_id, details: dict) -> None:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                session.add(
                    AuditLog(
                        tenant_id=tenant_uuid,
                        action=action,
                        entity_type="lead",
                        entity_id=lead_id,
                        actor="CallRoomService",
                        details=details,
                        after_json=details,
                    )
                )


def _agent_for_lead(lead: Lead) -> str:
    text = " ".join(
        str(value or "").lower()
        for value in [lead.industry, lead.opportunity_type, lead.notes, " ".join(lead.pain_points or [])]
    )
    if any(term in text for term in ["security", "compliance", "gdpr", "hipaa"]):
        return "daniel_brooks"
    if any(term in text for term in ["cloud", "aws", "devops", "deployment", "infrastructure"]):
        return "david_carter"
    if any(term in text for term in ["crm", "sales", "revenue", "pipeline"]):
        return "emma_collins"
    if any(term in text for term in ["onboarding", "retention", "support", "client"]):
        return "olivia_bennett"
    if any(term in text for term in ["software", "api", "integration", "dashboard"]):
        return "nathan_scott"
    return "sophia_reynolds"


def _pricing_anchor(lead: Lead) -> dict[str, Any]:
    score = float(lead.score or 0.0)
    if score >= 85:
        tier = "Growth or Enterprise"
        range_text = "$3,000-$12,000+ after discovery"
    elif score >= 65:
        tier = "Pilot or Growth"
        range_text = "$1,500-$5,000 after discovery"
    else:
        tier = "Pilot only"
        range_text = "Scope after fit confirmation"
    return {
        "internal_only": True,
        "tier_hint": tier,
        "range": range_text,
        "rule": "Do not reveal pricing unless the client asks directly or Captain approves proposal pricing.",
    }


def _confidence_score(lead: Lead, liaison_packet: dict[str, Any]) -> float:
    relationship = float(lead.score or 0.0)
    council_score = float(liaison_packet.get("council_briefing_gate", {}).get("confidence_score") or 0.0)
    base = max(relationship, 60.0)
    if council_score > 0:
        base = (base * 0.7) + (council_score * 0.3)
    return round(min(95.0, base), 2)


def _status_for_outcome(outcome: str) -> LeadStatus:
    if outcome == "won":
        return LeadStatus.WON
    if outcome == "lost":
        return LeadStatus.LOST
    return LeadStatus.NURTURE


def _next_action_for_outcome(outcome: str) -> str:
    if outcome == "won":
        return "Prepare proposal, implementation plan, and Captain approval package."
    if outcome == "lost":
        return "Store objection pattern and stop active follow-up unless the client re-engages."
    return "Send a concise follow-up with case-study questions and demo path."


def _append_note(existing: str | None, addition: str) -> str:
    if not existing:
        return addition
    return f"{existing}\n\n{addition}"


def _tenant_uuid(value=None) -> uuid.UUID:
    raw = value or settings.JARVIS_DEFAULT_TENANT_ID
    if not raw:
        raise ValueError("tenant_id is required")
    return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))


call_room_service = CallRoomService()

