"""
PredictiveActionEngine — Anticipates Captain's next best moves before he asks.
Revenue triggers, war room briefings, action priority scoring.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal, set_tenant_context
from app.services.ai.base_provider import Message, TaskType
from app.services.ai.router import ai_router

logger = logging.getLogger(__name__)


def _coerce_uuid(val: Any) -> UUID:
    return UUID(str(val)) if not isinstance(val, UUID) else val


def _parse_json_response(text: str) -> Any:
    """Extract first JSON structure from AI response."""
    try:
        match = re.search(r"(\[[\s\S]+\]|\{[\s\S]+\})", text)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    return None


class PredictiveActionEngine:
    """Analyses current state and predicts the highest-leverage actions for Captain."""

    # ─────────────────────────── NEXT ACTION PREDICTION ──────────────────── #

    async def predict_next_actions(self, tenant_id: Any) -> list[dict]:
        """Return top 5 recommended actions ranked by expected business impact."""
        tenant_uuid = _coerce_uuid(tenant_id)
        context = await self._build_pipeline_context(tenant_uuid)

        prompt = f"""You are JARVIS, strategic operations manager for Aliyar Solutions.
Current operational context:
{json.dumps(context, indent=2)}

Analyse this data and return the top 5 highest-leverage actions Captain should take RIGHT NOW.
Return ONLY a valid JSON array with exactly 5 objects, each with:
{{
  "action_type": "string (e.g. FOLLOW_UP_LEAD, SEND_PROPOSAL, LAUNCH_OUTREACH, CLOSE_DEAL, etc.)",
  "priority": 1,
  "expected_impact": "Specific business impact string (revenue, conversion, etc.)",
  "effort_level": "LOW|MEDIUM|HIGH",
  "deadline_suggestion": "ISO date string or null",
  "reasoning": "One sentence strategic rationale"
}}
Priority 1 = most urgent. Sort by priority ascending."""

        try:
            response, _ = await ai_router.chat(
                messages=[Message(role="user", content=prompt)],
                task_type=TaskType.STRATEGY,
                max_tokens=1000,
            )
            if response.error:
                raise ValueError(response.error)
            parsed = _parse_json_response(response.content)
            if isinstance(parsed, list):
                return parsed[:5]
        except Exception as exc:
            logger.warning("Predictive action engine failed: %s", exc)

        # Deterministic fallback
        return self._default_actions(context)

    def _default_actions(self, context: dict) -> list[dict]:
        today = datetime.now(UTC).date().isoformat()
        actions = []

        if context.get("outreach_today", 0) == 0:
            actions.append({
                "action_type": "LAUNCH_OUTREACH_CAMPAIGN",
                "priority": 1,
                "expected_impact": "Direct pipeline injection — 5–15 new conversations within 48 hours",
                "effort_level": "MEDIUM",
                "deadline_suggestion": today,
                "reasoning": "No outreach has been sent today; revenue pipeline requires daily activity.",
            })

        if context.get("stale_warm_leads", 0) > 0:
            actions.append({
                "action_type": "FOLLOW_UP_WARM_LEADS",
                "priority": 2,
                "expected_impact": f"Convert up to {context['stale_warm_leads']} warm prospects before they go cold",
                "effort_level": "LOW",
                "deadline_suggestion": today,
                "reasoning": "Warm leads decay after 72 hours — immediate follow-up has highest conversion rate.",
            })

        while len(actions) < 5:
            actions.append({
                "action_type": "REVIEW_PIPELINE",
                "priority": len(actions) + 1,
                "expected_impact": "Identify next highest-value conversion opportunity",
                "effort_level": "LOW",
                "deadline_suggestion": None,
                "reasoning": "Regular pipeline review ensures no opportunity is lost.",
            })

        return actions[:5]

    # ──────────────────────────── REVENUE TRIGGER ─────────────────────────── #

    async def predict_revenue_trigger(self, tenant_id: Any) -> dict:
        """Identify the single action most likely to generate revenue in the next 7 days."""
        tenant_uuid = _coerce_uuid(tenant_id)
        context = await self._build_pipeline_context(tenant_uuid)

        prompt = f"""You are JARVIS, revenue intelligence layer for Aliyar Solutions.
Operational context:
{json.dumps(context, indent=2)}

Identify the SINGLE action most likely to generate revenue within 7 days.
Return ONLY valid JSON:
{{
  "action": "Specific action string",
  "expected_revenue_range": "e.g. $3,000–$8,000",
  "confidence": 0.75,
  "target_lead_or_client": "name or description or null",
  "time_to_revenue": "e.g. 3–5 days",
  "reasoning": "Strategic rationale string"
}}
confidence must be float 0.0–1.0."""

        try:
            response, _ = await ai_router.chat(
                messages=[Message(role="user", content=prompt)],
                task_type=TaskType.STRATEGY,
                max_tokens=500,
            )
            if response.error:
                raise ValueError(response.error)
            parsed = _parse_json_response(response.content)
            if isinstance(parsed, dict):
                return parsed
        except Exception as exc:
            logger.warning("Revenue trigger prediction failed: %s", exc)

        return {
            "action": "Follow up on warm pipeline leads with a concrete proposal",
            "expected_revenue_range": "$2,000–$10,000",
            "confidence": 0.6,
            "target_lead_or_client": None,
            "time_to_revenue": "5–7 days",
            "reasoning": "Warm leads with no recent touchpoint represent the fastest path to conversion.",
        }

    # ────────────────────────────── WAR ROOM BRIEF ────────────────────────── #

    async def generate_war_room_brief(self, tenant_id: Any) -> dict:
        """Generate a critical-moment situation brief for Captain."""
        tenant_uuid = _coerce_uuid(tenant_id)
        context = await self._build_pipeline_context(tenant_uuid)

        prompt = f"""You are JARVIS, executive command intelligence for Aliyar Solutions.
Operational context:
{json.dumps(context, indent=2)}

Generate a WAR ROOM brief — a strategic snapshot for immediate decision-making.
Return ONLY valid JSON:
{{
  "critical_issues": [
    {{"issue": "string", "severity": "HIGH|CRITICAL", "impact": "string"}}
  ],
  "opportunities": [
    {{"opportunity": "string", "revenue_potential": "string", "window": "string"}}
  ],
  "48h_revenue_potential": "string e.g. $0–$5,000",
  "recommended_sequence": [
    "Step 1: ...",
    "Step 2: ...",
    "Step 3: ..."
  ],
  "war_room_status": "GREEN|YELLOW|RED|CRITICAL",
  "captain_directive": "One powerful sentence — what Captain must do right now"
}}"""

        try:
            response, _ = await ai_router.chat(
                messages=[Message(role="user", content=prompt)],
                task_type=TaskType.STRATEGY,
                max_tokens=900,
            )
            if response.error:
                raise ValueError(response.error)
            parsed = _parse_json_response(response.content)
            if isinstance(parsed, dict):
                parsed["generated_at"] = datetime.now(UTC).isoformat()
                parsed["tenant_id"] = str(tenant_uuid)
                return parsed
        except Exception as exc:
            logger.warning("War room brief generation failed: %s", exc)

        return {
            "critical_issues": [],
            "opportunities": [],
            "48h_revenue_potential": "Unknown — system initialising",
            "recommended_sequence": ["Review pipeline", "Send outreach", "Follow up warm leads"],
            "war_room_status": "YELLOW",
            "captain_directive": "Initiate outreach and follow up on all warm leads today.",
            "generated_at": datetime.now(UTC).isoformat(),
            "tenant_id": str(tenant_uuid),
        }

    # ─────────────────────────── CONTEXT BUILDER ──────────────────────────── #

    async def _build_pipeline_context(self, tenant_uuid: UUID) -> dict:
        """Assemble lightweight pipeline context for AI prompts."""
        try:
            from app.models.lead import Lead  # noqa: PLC0415
            from app.models.outreach import ReplyLog  # noqa: PLC0415

            now = datetime.now(UTC)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            three_days_ago = now - timedelta(days=3)

            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await set_tenant_context(session, str(tenant_uuid))

                    total_leads = await session.scalar(
                        select(func.count()).select_from(Lead).where(Lead.tenant_id == tenant_uuid)
                    ) or 0

                    outreach_today = await session.scalar(
                        select(func.count())
                        .select_from(ReplyLog)
                        .where(ReplyLog.tenant_id == tenant_uuid, ReplyLog.created_at >= today_start)
                    ) or 0

                    stale_warm = await session.scalar(
                        select(func.count())
                        .select_from(ReplyLog)
                        .where(
                            ReplyLog.tenant_id == tenant_uuid,
                            ReplyLog.classification.in_(["INTERESTED", "QUESTION"]),
                            ReplyLog.created_at <= three_days_ago,
                        )
                    ) or 0

            return {
                "total_leads": total_leads,
                "outreach_today": outreach_today,
                "stale_warm_leads": stale_warm,
                "current_date": now.date().isoformat(),
                "company": "Aliyar Solutions",
            }

        except Exception as exc:
            logger.warning("Pipeline context build failed: %s", exc)
            return {
                "total_leads": 0,
                "outreach_today": 0,
                "stale_warm_leads": 0,
                "current_date": datetime.now(UTC).date().isoformat(),
                "company": "Aliyar Solutions",
            }


predictive_action_engine = PredictiveActionEngine()
