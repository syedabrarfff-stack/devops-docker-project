from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.lead import Lead
from app.models.memory import MemoryGraphNode
from app.models.outreach import OutreachLog, ReplyLog
from app.models.revenue import Client
from app.services.agents.liaison_profiles import LIAISON_AGENTS, get_liaison_agent, normalize_agent_name
from app.services.ai.council import intelligence_council
from app.services.memory.graph import _upsert_node, search_memory_graph
from app.services.memory.human_intelligence import human_intelligence_context


class ClientLiaisonService:
    async def seed_agents(self, tenant_id=None) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        nodes_created = 0

        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                for slug, profile in LIAISON_AGENTS.items():
                    _, created = await _upsert_node(
                        session,
                        tenant_uuid,
                        node_type="client_liaison_agent",
                        title=profile["name"],
                        content=_profile_content(profile),
                        source_table="liaison_agents",
                        source_id=slug,
                        metadata={
                            "role": profile["role"],
                            "domain": profile["domain"],
                            "department": profile["department"],
                            "elevenlabs_voice_env": profile["elevenlabs_voice_env"],
                        },
                    )
                    nodes_created += int(created)

                session.add(
                    AuditLog(
                        tenant_id=tenant_uuid,
                        action="liaison_agents_seeded",
                        entity_type="liaison_agents",
                        actor="ClientLiaisonService",
                        details={"agents": len(LIAISON_AGENTS), "nodes_created": nodes_created},
                    )
                )

        return {
            "liaison_agents_ready": True,
            "agents": len(LIAISON_AGENTS),
            "nodes_created": nodes_created,
            "agent_names": [profile["name"] for profile in LIAISON_AGENTS.values()],
        }

    def list_agents(self) -> dict[str, Any]:
        return {
            "count": len(LIAISON_AGENTS),
            "agents": [
                {
                    "slug": slug,
                    **profile,
                    "elevenlabs_voice_id": _voice_id(profile),
                    "pre_call_protocol": PRE_CALL_PROTOCOL,
                    "post_call_protocol": POST_CALL_PROTOCOL,
                }
                for slug, profile in LIAISON_AGENTS.items()
            ],
        }

    async def prepare_call(
        self,
        agent_name: str,
        tenant_id,
        *,
        lead_id=None,
        client_id=None,
        call_topic: str | None = None,
        call_objective: str | None = None,
    ) -> dict[str, Any]:
        started = time.monotonic()
        tenant_uuid = _tenant_uuid(tenant_id)
        slug = normalize_agent_name(agent_name)
        profile = get_liaison_agent(slug)
        if not profile:
            raise ValueError(f"Unknown liaison agent: {agent_name}")
        if not lead_id and not client_id:
            raise ValueError("lead_id or client_id is required")

        target = await self._load_target(tenant_uuid, lead_id=lead_id, client_id=client_id)
        if not target:
            raise ValueError("Lead or client not found")

        target_summary = _target_summary(target)
        relationship_context = await self._relationship_context(tenant_uuid, target)
        memory_evidence = await self._memory_evidence(tenant_uuid, profile, target_summary, call_topic)
        briefing_document = _build_briefing_document(
            profile=profile,
            target_summary=target_summary,
            relationship_context=relationship_context,
            memory_evidence=memory_evidence,
            call_topic=call_topic,
            call_objective=call_objective,
        )
        council_gate = await self._council_briefing_gate(
            tenant_uuid=tenant_uuid,
            profile=profile,
            target_summary=target_summary,
            relationship_context=relationship_context,
            briefing_document=briefing_document,
        )
        approved_script = _approved_script(profile, target_summary, relationship_context, council_gate)
        what_to_avoid = _avoid_list(profile, target_summary, relationship_context)
        objection_handlers = _objection_handlers(profile, target_summary, relationship_context)

        prepared = {
            "agent": {
                "slug": slug,
                "name": profile["name"],
                "role": profile["role"],
                "department": profile["department"],
                "domain": profile["domain"],
                "elevenlabs_voice_id": _voice_id(profile),
                "voice_persona": profile["voice_persona"],
                "communication_style": profile["communication_style"],
            },
            "target": target_summary,
            "pre_call_intelligence_protocol": {
                "sla_seconds": 60,
                "status": "complete",
                "pulled": [
                    "client history",
                    "outreach and reply records",
                    "score and status",
                    "known issues",
                    "open opportunities",
                    "memory evidence",
                ],
            },
            "council_briefing_gate": council_gate,
            "briefing_document": briefing_document,
            "approved_script": approved_script,
            "what_to_avoid": what_to_avoid,
            "objection_handlers": objection_handlers,
            "post_call_protocol": POST_CALL_PROTOCOL,
            "prepared_in_ms": int((time.monotonic() - started) * 1000),
            "generated_at": datetime.now(UTC).isoformat(),
        }

        await self._record_preparation(tenant_uuid, slug, target_summary, prepared)
        return prepared

    async def _load_target(self, tenant_uuid, *, lead_id=None, client_id=None) -> Lead | Client | None:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                if lead_id:
                    return await session.scalar(
                        select(Lead).where(Lead.tenant_id == tenant_uuid, Lead.id == uuid.UUID(str(lead_id)))
                    )
                return await session.scalar(
                    select(Client).where(Client.tenant_id == tenant_uuid, Client.id == uuid.UUID(str(client_id)))
                )

    async def _relationship_context(self, tenant_uuid, target: Lead | Client) -> dict[str, Any]:
        if isinstance(target, Client):
            return {
                "relationship_score": 85 if target.status.value == "ACTIVE" else 55,
                "history": [
                    f"Client status is {target.status.value}.",
                    f"Package tier: {target.package_tier or 'not recorded'}.",
                    f"MRR: ${float(target.mrr_usd or 0):,.0f}.",
                ],
                "recent_outreach": [],
                "recent_replies": [],
                "issues": ["No open issue record found in the current client table."],
                "opportunities": ["Review onboarding, retention, and expansion potential."],
            }

        lead_id = target.id
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                outreach_rows = (
                    await session.execute(
                        select(OutreachLog)
                        .where(OutreachLog.tenant_id == tenant_uuid, OutreachLog.lead_id == lead_id)
                        .order_by(OutreachLog.created_at.desc())
                        .limit(5)
                    )
                ).scalars().all()
                reply_rows = (
                    await session.execute(
                        select(ReplyLog)
                        .where(ReplyLog.tenant_id == tenant_uuid, ReplyLog.lead_id == lead_id)
                        .order_by(ReplyLog.created_at.desc())
                        .limit(5)
                    )
                ).scalars().all()

        enrichment = target.enrichment_data or {}
        pain_points = target.pain_points or enrichment.get("pain_points") or []
        if isinstance(pain_points, str):
            pain_points = [pain_points]
        issues = pain_points or ["Manual handoffs, response delays, or visibility gaps need confirmation."]
        opportunities = enrichment.get("automation_opportunities") or enrichment.get("opportunities") or []
        if isinstance(opportunities, str):
            opportunities = [opportunities]
        if not opportunities:
            opportunities = [
                "Use discovery to identify one high-friction workflow that can be improved quickly.",
                "Convert the conversation into a practical demo or case-study review.",
            ]

        score = float(target.score or 0.0)
        if reply_rows:
            score = min(100.0, score + 10.0)
        if target.status.value in {"DEMO", "PROPOSAL", "REPLIED"}:
            score = min(100.0, score + 8.0)

        return {
            "relationship_score": round(score, 2),
            "history": [
                f"Lead status is {target.status.value}.",
                f"Lead score is {float(target.score or 0.0):.1f}.",
                f"Source: {target.source or 'unknown'}.",
                f"Assigned persona: {target.assigned_persona or 'not assigned'}.",
            ],
            "recent_outreach": [
                {
                    "channel": row.channel.value,
                    "step": row.sequence_step,
                    "subject": row.subject,
                    "status": row.status.value,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in outreach_rows
            ],
            "recent_replies": [
                {
                    "classification": row.classification.value,
                    "confidence": row.confidence_score,
                    "subject": row.subject,
                    "body_preview": (row.body_text or "")[:240],
                    "processed_at": row.processed_at.isoformat() if row.processed_at else None,
                }
                for row in reply_rows
            ],
            "issues": issues[:5],
            "opportunities": opportunities[:5],
        }

    async def _memory_evidence(
        self,
        tenant_uuid,
        profile: dict[str, Any],
        target_summary: dict[str, Any],
        call_topic: str | None,
    ) -> list[dict[str, Any]]:
        query = " ".join(
            [
                profile["domain"],
                target_summary.get("company_name") or "",
                target_summary.get("industry") or "",
                call_topic or "",
                "client pain opportunity service demo",
            ]
        )
        try:
            result = await search_memory_graph(query, tenant_uuid, limit=5)
            return result.get("results", [])
        except Exception:
            return []

    async def _council_briefing_gate(
        self,
        *,
        tenant_uuid,
        profile: dict[str, Any],
        target_summary: dict[str, Any],
        relationship_context: dict[str, Any],
        briefing_document: dict[str, Any],
    ) -> dict[str, Any]:
        context = {
            "agent": profile["name"],
            "role": profile["role"],
            "target": target_summary,
            "relationship_context": relationship_context,
            "briefing": briefing_document,
            "m2_human_intelligence": human_intelligence_context(max_chars=1200),
        }
        question = (
            f"Approve a client discovery call briefing for {profile['name']} with "
            f"{target_summary.get('company_name', 'the client')}. Return risk, confidence, and the safest talk track."
        )
        try:
            result = await asyncio.wait_for(
                intelligence_council.convene(question, context, council_type="client_liaison_call", tenant_id=tenant_uuid),
                timeout=45,
            )
            return {
                "status": "approved" if result.decision in {"APPROVE", "CAPTAIN_REVIEW"} else "hold",
                "decision": result.decision,
                "confidence_score": result.score,
                "reasoning": result.reasoning,
                "session_id": result.session_id,
                "quorum_met": result.quorum_met,
                "responses_count": result.responses_count,
                "cost_estimate_usd": result.cost_estimate_usd,
            }
        except Exception as exc:
            return {
                "status": "fallback_approved",
                "decision": "CONSERVATIVE_SCRIPT",
                "confidence_score": 62.0,
                "reasoning": f"Council unavailable during call prep. Using conservative discovery script. Error: {exc}",
                "session_id": None,
                "quorum_met": False,
                "responses_count": 0,
                "cost_estimate_usd": 0.0,
            }

    async def _record_preparation(
        self,
        tenant_uuid,
        slug: str,
        target_summary: dict[str, Any],
        prepared: dict[str, Any],
    ) -> None:
        source_id = f"{slug}:{target_summary['target_type']}:{target_summary['id']}:call_brief"
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                node, _ = await _upsert_node(
                    session,
                    tenant_uuid,
                    node_type="liaison_call_brief",
                    title=f"{prepared['agent']['name']} call brief for {target_summary['company_name']}",
                    content=json.dumps(
                        {
                            "target": target_summary,
                            "briefing": prepared["briefing_document"],
                            "script": prepared["approved_script"],
                            "avoid": prepared["what_to_avoid"],
                        },
                        sort_keys=True,
                        default=str,
                    ),
                    source_table="liaison_call_briefs",
                    source_id=source_id,
                    metadata={
                        "agent": prepared["agent"]["name"],
                        "target_type": target_summary["target_type"],
                        "target_id": target_summary["id"],
                    },
                )
                session.add(
                    AuditLog(
                        tenant_id=tenant_uuid,
                        action="liaison_call_prepared",
                        entity_type="liaison_call_brief",
                        entity_id=node.id if isinstance(node, MemoryGraphNode) else None,
                        actor=prepared["agent"]["name"],
                        details={
                            "target": target_summary,
                            "council_decision": prepared["council_briefing_gate"].get("decision"),
                            "prepared_in_ms": prepared["prepared_in_ms"],
                        },
                    )
                )


PRE_CALL_PROTOCOL = [
    "Pull client history, reports, score, issues, and opportunities within 60 seconds.",
    "Read M2 human intelligence before any client-facing interaction.",
    "Ask the Council for a briefing gate before using a script.",
    "Use one clear next step, never pricing-first language.",
]

POST_CALL_PROTOCOL = [
    "Create call notes with client pain, exact questions, commitments, risks, and next action.",
    "Update lead or client status and relationship score.",
    "Store transcript summary and action items in memory.",
    "Raise a Captain approval if regulated scope, pricing, spend, or risk exceeds authority.",
]


def _profile_content(profile: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Name: {profile['name']}",
            f"Role: {profile['role']}",
            f"Department: {profile['department']}",
            f"Domain: {profile['domain']}",
            f"Voice persona: {profile['voice_persona']}",
            "Style: " + " ".join(profile["communication_style"]),
            "Expertise: " + ", ".join(profile["expertise"]),
        ]
    )


def _voice_id(profile: dict[str, Any]) -> str:
    configured = os.getenv(profile["elevenlabs_voice_env"])
    if configured:
        return configured
    if settings.ELEVENLABS_API_KEY and settings.ELEVENLABS_VOICE_ID:
        return settings.ELEVENLABS_VOICE_ID
    return "not_configured"


def _target_summary(target: Lead | Client) -> dict[str, Any]:
    if isinstance(target, Client):
        return {
            "target_type": "client",
            "id": str(target.id),
            "company_name": target.company_name or "Unknown client",
            "contact_name": target.contact_name,
            "email": target.email,
            "industry": None,
            "country": None,
            "status": target.status.value,
            "score": None,
            "package_tier": target.package_tier,
            "mrr_usd": float(target.mrr_usd or 0.0),
        }
    return {
        "target_type": "lead",
        "id": str(target.id),
        "company_name": target.company_name or target.company or "Unknown company",
        "contact_name": target.contact_name,
        "email": target.email or target.contact_email,
        "industry": target.industry or target.opportunity_type,
        "country": target.country,
        "status": target.status.value,
        "score": float(target.score or 0.0),
        "source": target.source,
        "website": target.website or target.company_website,
        "notes": target.notes,
    }


def _build_briefing_document(
    *,
    profile: dict[str, Any],
    target_summary: dict[str, Any],
    relationship_context: dict[str, Any],
    memory_evidence: list[dict[str, Any]],
    call_topic: str | None,
    call_objective: str | None,
) -> dict[str, Any]:
    company = target_summary.get("company_name") or "the client"
    issues = relationship_context.get("issues") or []
    opportunities = relationship_context.get("opportunities") or []
    evidence_refs = [
        {
            "title": item.get("title"),
            "node_type": item.get("node_type"),
            "score": item.get("score"),
            "source": f"{item.get('source_table')}:{item.get('source_id')}",
        }
        for item in memory_evidence
    ]
    return {
        "objective": call_objective or f"Confirm {company}'s highest-friction workflow and decide if a demo is relevant.",
        "topic": call_topic or profile["domain"],
        "opening_position": (
            f"{profile['name']} should lead with one observed operational concern, "
            "then ask discovery questions before proposing any scope."
        ),
        "client_context": {
            "company": company,
            "industry": target_summary.get("industry"),
            "country": target_summary.get("country"),
            "relationship_score": relationship_context.get("relationship_score"),
            "status": target_summary.get("status"),
        },
        "known_issues": issues,
        "open_opportunities": opportunities,
        "recent_history": relationship_context.get("history", []),
        "evidence_references": evidence_refs,
        "success_condition": "Client agrees to share case-study context, answer discovery questions, or review a tailored demo.",
    }


def _approved_script(
    profile: dict[str, Any],
    target_summary: dict[str, Any],
    relationship_context: dict[str, Any],
    council_gate: dict[str, Any],
) -> dict[str, Any]:
    company = target_summary.get("company_name") or "your team"
    contact = (target_summary.get("contact_name") or "there").split()[0]
    issue = (relationship_context.get("issues") or ["manual follow-up and visibility gaps"])[0]
    opportunity = (relationship_context.get("opportunities") or ["identify the fastest operational improvement"])[0]
    return {
        "status": "approved_by_council_gate" if council_gate.get("status") != "hold" else "hold_for_captain",
        "opening": (
            f"Hi {contact}, our team reviewed {company}'s public workflow signals and the main concern appears to be {issue}."
        ),
        "discovery_questions": [
            "Where does work slow down most often between enquiry, response, and delivery?",
            "Which manual handoff creates the most follow-up pressure for your team?",
            "If one workflow became faster this month, what result would matter most?",
            "What tools are currently holding the customer record, tasks, and reporting?",
            "Would a focused demo around that workflow be relevant after we confirm the details?",
        ],
        "value_statement": (
            f"Aliyar Solutions can help {company} turn that area into a more reliable operating flow, "
            f"with the first target being {opportunity}."
        ),
        "close": "If useful, our team can turn your answers into a short case-study style demo path before discussing scope.",
    }


def _avoid_list(
    profile: dict[str, Any],
    target_summary: dict[str, Any],
    relationship_context: dict[str, Any],
) -> list[str]:
    return [
        "Do not mention model names, prompts, bots, or internal automation mechanics.",
        "Do not reveal pricing until the client asks directly or Captain approves a proposal.",
        f"Do not over-prescribe the {profile['domain']} plan before {target_summary.get('company_name', 'the client')} confirms the real workflow.",
    ]


def _objection_handlers(
    profile: dict[str, Any],
    target_summary: dict[str, Any],
    relationship_context: dict[str, Any],
) -> list[dict[str, str]]:
    company = target_summary.get("company_name") or "your team"
    return [
        {
            "objection": "We already have tools for this.",
            "response": (
                f"That is useful context. Our team would not replace tools blindly; the first step is to see where {company}'s "
                "current tools stop supporting the workflow cleanly."
            ),
        },
        {
            "objection": "We are not ready to spend right now.",
            "response": (
                "That is completely fair. The useful next step is a short case-study review so your team can see whether "
                "there is a real operational gain before any scope or pricing conversation."
            ),
        },
    ]


def _tenant_uuid(value=None) -> uuid.UUID:
    raw = value or settings.JARVIS_DEFAULT_TENANT_ID
    if not raw:
        raise ValueError("tenant_id is required")
    return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))


client_liaison_service = ClientLiaisonService()

