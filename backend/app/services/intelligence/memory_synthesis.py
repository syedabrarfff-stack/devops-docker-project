"""
JARVIS Memory Synthesis Engine — converts raw interactions into structured memories,
synthesises daily learnings, and surfaces recurring strategic patterns.
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID, uuid4

from app.core.database import AsyncSessionLocal, set_tenant_context

logger = logging.getLogger(__name__)

# ── Interaction → memory templates ───────────────────────────────────────────

_INTERACTION_SCHEMAS: dict[str, dict[str, Any]] = {
    "lead_scored": {
        "memory_type": "lead_intelligence",
        "importance_base": 4,
        "tags": ["lead", "scoring", "pipeline"],
    },
    "email_sent": {
        "memory_type": "outreach_pattern",
        "importance_base": 3,
        "tags": ["outreach", "email", "communication"],
    },
    "reply_received": {
        "memory_type": "engagement_signal",
        "importance_base": 7,
        "tags": ["reply", "engagement", "prospect"],
    },
    "proposal_sent": {
        "memory_type": "deal_intelligence",
        "importance_base": 8,
        "tags": ["proposal", "deal", "pricing"],
    },
    "client_onboarded": {
        "memory_type": "client_success",
        "importance_base": 9,
        "tags": ["onboarding", "client", "revenue"],
    },
    "deal_lost": {
        "memory_type": "loss_analysis",
        "importance_base": 8,
        "tags": ["loss", "objection", "learning"],
    },
    "objection_handled": {
        "memory_type": "sales_technique",
        "importance_base": 6,
        "tags": ["objection", "sales", "technique"],
    },
    "system_error": {
        "memory_type": "system_health",
        "importance_base": 7,
        "tags": ["error", "system", "reliability"],
    },
}

_DEFAULT_SCHEMA = {
    "memory_type": "general_learning",
    "importance_base": 3,
    "tags": ["general"],
}


def _extract_content(interaction_type: str, data: dict[str, Any]) -> str:
    """Build a concise human-readable memory content string."""
    if interaction_type == "lead_scored":
        return (
            f"Lead '{data.get('company', data.get('company_name', 'Unknown'))}' scored "
            f"{data.get('score', 0)}/100. Industry: {data.get('industry', 'Unknown')}. "
            f"Pain points: {', '.join(str(p) for p in (data.get('pain_points') or [])[:3])}."
        )
    if interaction_type == "email_sent":
        return (
            f"Outreach email sent to {data.get('recipient', 'unknown')} "
            f"via persona {data.get('persona', 'Unknown')}. "
            f"Subject: {data.get('subject', 'N/A')[:80]}."
        )
    if interaction_type == "reply_received":
        return (
            f"Reply received from {data.get('sender', 'unknown')}. "
            f"Sentiment: {data.get('sentiment', 'neutral')}. "
            f"Intent: {data.get('intent', 'unknown')}. "
            f"Key phrases: {str(data.get('key_phrases', []))[:120]}."
        )
    if interaction_type == "proposal_sent":
        return (
            f"Proposal sent to {data.get('company', 'Unknown')} for "
            f"${data.get('value', 0):,.0f} ({data.get('tier', 'GROWTH')} tier). "
            f"Service: {data.get('service_type', 'Unknown')}."
        )
    if interaction_type == "client_onboarded":
        return (
            f"New client onboarded: {data.get('company', 'Unknown')}. "
            f"MRR: ${data.get('mrr', 0):,.0f}/mo. "
            f"Services: {data.get('services', 'N/A')}. "
            f"Source: {data.get('source', 'unknown')}."
        )
    if interaction_type == "deal_lost":
        return (
            f"Deal lost: {data.get('company', 'Unknown')}. "
            f"Reason: {data.get('reason', 'Unknown')}. "
            f"Deal value: ${data.get('value', 0):,.0f}. "
            f"Loss stage: {data.get('stage', 'proposal')}."
        )
    return f"Interaction recorded: {interaction_type}. Data: {json.dumps(data)[:200]}."


def _calculate_importance(base: int, data: dict[str, Any]) -> int:
    """Adjust importance score based on deal value, score, and outcome signals."""
    score = base
    value = float(data.get("value", 0) or data.get("mrr", 0) or 0)
    if value >= 10_000:
        score = min(10, score + 2)
    elif value >= 5_000:
        score = min(10, score + 1)
    if data.get("sentiment") in ("positive", "interested"):
        score = min(10, score + 1)
    if data.get("reason") and "price" in str(data.get("reason", "")).lower():
        score = min(10, score + 1)
    return max(1, min(10, score))


def _extract_tags(interaction_type: str, data: dict[str, Any], base_tags: list[str]) -> list[str]:
    tags = list(base_tags)
    if data.get("industry"):
        tags.append(str(data["industry"]).lower().replace(" ", "_"))
    if data.get("country"):
        tags.append(str(data["country"]).lower().replace(" ", "_"))
    if data.get("tier"):
        tags.append(str(data["tier"]).lower())
    if data.get("persona"):
        tags.append(str(data["persona"]).lower().replace(" ", "_"))
    return list(set(tags))


class MemorySynthesisEngine:
    """Converts interactions into structured memories and surfaces patterns."""

    def synthesize_from_interaction(
        self,
        tenant_id: Any,
        interaction_type: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Synthesise a single interaction into a structured memory record."""
        schema = _INTERACTION_SCHEMAS.get(interaction_type, _DEFAULT_SCHEMA)
        content = _extract_content(interaction_type, data)
        importance = _calculate_importance(schema["importance_base"], data)
        tags = _extract_tags(interaction_type, data, schema["tags"])

        relationships: list[str] = []
        if data.get("lead_id"):
            relationships.append(f"lead:{data['lead_id']}")
        if data.get("client_id"):
            relationships.append(f"client:{data['client_id']}")
        if data.get("persona"):
            relationships.append(f"persona:{data['persona']}")

        return {
            "id": str(uuid4()),
            "tenant_id": str(tenant_id),
            "memory_type": schema["memory_type"],
            "content": content,
            "importance": importance,
            "tags": tags,
            "source": interaction_type,
            "relationships": relationships,
            "raw_data_summary": {k: str(v)[:100] for k, v in data.items() if k not in ("body", "html")},
            "synthesized_at": datetime.now(timezone.utc).isoformat(),
        }

    async def synthesize_daily_learnings(self, tenant_id: UUID) -> list[dict[str, Any]]:
        """
        Synthesise all today's AI audit events into distilled memory records.
        Runs nightly via scheduler.
        """
        from sqlalchemy import select
        memories: list[dict[str, Any]] = []

        async with AsyncSessionLocal() as session:
            await set_tenant_context(session, str(tenant_id))
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            try:
                from app.models.ai_audit import AIAuditLog  # type: ignore[attr-defined]
                from sqlalchemy import text as sa_text
                result = await session.execute(
                    select(AIAuditLog).where(
                        AIAuditLog.tenant_id == tenant_id,
                        AIAuditLog.created_at >= cutoff,
                    ).limit(200)
                )
                logs = result.scalars().all()
                if logs:
                    task_counter: Counter = Counter()
                    for log in logs:
                        task_type = getattr(log, "task_type", "unknown")
                        task_counter[task_type] += 1
                    summary = f"Daily AI activity: {len(logs)} calls. Top tasks: {dict(task_counter.most_common(3))}."
                    memories.append(self.synthesize_from_interaction(
                        tenant_id, "email_sent",
                        {"recipient": "system", "subject": summary, "persona": "JARVIS"}
                    ))
            except Exception as exc:
                logger.debug("Daily synthesis audit query skipped: %s", exc)

            # Synthesise lead activity
            try:
                from app.models.lead import Lead
                new_leads_result = await session.execute(
                    select(Lead).where(
                        Lead.tenant_id == tenant_id,
                        Lead.created_at >= cutoff,
                    ).limit(50)
                )
                new_leads = new_leads_result.scalars().all()
                for lead in new_leads:
                    memories.append(self.synthesize_from_interaction(
                        tenant_id, "lead_scored",
                        {
                            "company": lead.company_name or lead.company,
                            "industry": lead.industry,
                            "score": lead.score,
                            "pain_points": lead.pain_points or [],
                        }
                    ))
            except Exception as exc:
                logger.debug("Lead synthesis skipped: %s", exc)

        return memories

    async def get_strategic_patterns(self, tenant_id: UUID) -> dict[str, Any]:
        """
        Identifies high-value recurring patterns across stored memories.
        Returns pattern summary and actionable insights.
        """
        async with AsyncSessionLocal() as session:
            await set_tenant_context(session, str(tenant_id))
            try:
                from app.models.memory import Memory  # type: ignore[attr-defined]
                from sqlalchemy import select, func
                result = await session.execute(
                    select(Memory).where(Memory.tenant_id == tenant_id).limit(500)
                )
                memories = result.scalars().all()
            except Exception:
                memories = []

        if not memories:
            return {
                "patterns": [],
                "top_industries": [],
                "effective_personas": [],
                "insight_count": 0,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            }

        # Aggregate tags to surface patterns
        all_tags: list[str] = []
        for m in memories:
            tags = getattr(m, "tags", []) or []
            if isinstance(tags, list):
                all_tags.extend(tags)
            elif isinstance(tags, str):
                try:
                    all_tags.extend(json.loads(tags))
                except Exception:
                    pass

        tag_freq = Counter(all_tags)
        top_tags = [{"tag": t, "frequency": c} for t, c in tag_freq.most_common(10)]

        industries = [t for t in all_tags if t not in (
            "lead", "email", "reply", "proposal", "client", "outreach",
            "engagement", "scoring", "pipeline", "deal", "revenue"
        )]
        industry_freq = Counter(industries)
        top_industries = [{"industry": i, "frequency": c} for i, c in industry_freq.most_common(5)]

        patterns: list[dict[str, str]] = []
        if tag_freq.get("reply", 0) > 10:
            patterns.append({
                "pattern": "High outreach reply volume",
                "insight": "Email sequences are generating engagement — double down on volume",
                "priority": "medium",
            })
        if tag_freq.get("loss", 0) > tag_freq.get("client", 0):
            patterns.append({
                "pattern": "Loss rate exceeds client wins",
                "insight": "Review proposal positioning and pricing — loss rate is above industry average",
                "priority": "high",
            })
        if tag_freq.get("proposal", 0) > 5 and tag_freq.get("client", 0) == 0:
            patterns.append({
                "pattern": "Proposals not converting",
                "insight": "Proposals are being sent but not closing — strengthen follow-up sequence",
                "priority": "critical",
            })

        return {
            "patterns": patterns,
            "top_tags": top_tags,
            "top_industries": top_industries,
            "total_memories": len(memories),
            "insight_count": len(patterns),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }


memory_synthesis_engine = MemorySynthesisEngine()
