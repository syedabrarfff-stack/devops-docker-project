"""
CaptainIntelligenceBridge — Tony Stark layer for Captain Syed Abrar.
Processes raw input, brain dumps, email threads, and generates situation reports.
"""
from __future__ import annotations

import asyncio
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


def _parse_json_response(text: str) -> dict:
    """Extract JSON block from AI response, falling back to empty dict."""
    try:
        match = re.search(r"\{[\s\S]+\}", text)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    return {}


class CaptainIntelligenceBridge:
    """Primary intelligence bridge between Captain and all JARVIS operational systems."""

    # ─────────────────────────────── LEAD INTAKE ──────────────────────────── #

    async def process_captain_lead_intake(self, tenant_id: Any, raw_input: str) -> dict:
        """Parse any raw text Captain types into structured lead data."""
        tenant_uuid = _coerce_uuid(tenant_id)

        # Pre-pass: regex extraction of obvious entities
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", raw_input)
        url_match = re.search(r"https?://[^\s]+", raw_input)
        phone_match = re.search(r"\+?[\d\s\-().]{7,15}", raw_input)

        prompt = f"""You are JARVIS, intelligence layer of Aliyar Solutions.
Captain has provided this raw lead input. Extract structured data from it.

RAW INPUT:
{raw_input}

Return ONLY valid JSON with these exact keys:
{{
  "company_name": "string or null",
  "contact_name": "string or null",
  "email": "string or null",
  "phone": "string or null",
  "industry": "string or null",
  "pain_points": ["list", "of", "pain points"],
  "notes": "string summarising the lead",
  "urgency_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "lead_source": "LINKEDIN|EMAIL|REFERRAL|INBOUND|VOICE_NOTE|MANUAL|UNKNOWN",
  "estimated_value": "string or null (e.g. $5,000/month)"
}}"""

        try:
            response, _ = await asyncio.wait_for(
                ai_router.chat(
                    messages=[Message(role="user", content=prompt)],
                    task_type=TaskType.ANALYSIS,
                    max_tokens=800,
                ),
                timeout=30.0,
            )
            if response.error:
                raise ValueError(response.error)
            structured = _parse_json_response(response.content or "")
        except Exception as exc:
            logger.warning("AI lead intake failed: %s", exc)
            structured = {}

        # Overlay regex-extracted entities if AI missed them
        if email_match and not structured.get("email"):
            structured["email"] = email_match.group()
        if phone_match and not structured.get("phone"):
            structured["phone"] = phone_match.group().strip()

        return {
            "raw_input": raw_input,
            "structured_lead": structured,
            "extracted_entities": {
                "email": email_match.group() if email_match else None,
                "url": url_match.group() if url_match else None,
                "phone": phone_match.group().strip() if phone_match else None,
            },
            "processing_status": "COMPLETE" if structured else "PARTIAL",
            "processed_at": datetime.now(UTC).isoformat(),
            "tenant_id": str(tenant_uuid),
        }

    # ─────────────────────────────── BRAIN DUMP ───────────────────────────── #

    async def parse_brain_dump(self, tenant_id: Any, text: str) -> dict:
        """Parse a wall of text from Captain into structured action items and insights."""
        tenant_uuid = _coerce_uuid(tenant_id)

        prompt = f"""You are JARVIS, executive operations manager for Aliyar Solutions.
Captain has dumped a wall of notes. Extract structured intelligence.

BRAIN DUMP:
{text}

Return ONLY valid JSON with these exact keys:
{{
  "action_items": [
    {{"item": "string", "priority": "HIGH|MEDIUM|LOW", "assignee": "string or null", "deadline": "string or null"}}
  ],
  "leads_mentioned": [
    {{"company": "string", "contact": "string or null", "context": "string"}}
  ],
  "decisions_made": [
    {{"decision": "string", "rationale": "string or null"}}
  ],
  "follow_ups_needed": [
    {{"item": "string", "due_by": "string or null", "contact": "string or null"}}
  ],
  "key_insights": [
    {{"insight": "string", "category": "STRATEGIC|OPERATIONAL|CLIENT|MARKET|RISK"}}
  ],
  "overall_priority": "LOW|MEDIUM|HIGH|CRITICAL",
  "summary": "Two sentence summary of the brain dump"
}}"""

        try:
            response, _ = await asyncio.wait_for(
                ai_router.chat(
                    messages=[Message(role="user", content=prompt)],
                    task_type=TaskType.ANALYSIS,
                    max_tokens=1200,
                ),
                timeout=30.0,
            )
            if response.error:
                raise ValueError(response.error)
            structured = _parse_json_response(response.content or "")
        except Exception as exc:
            logger.warning("Brain dump parsing failed: %s", exc)
            structured = {}

        return {
            "raw_text": text,
            "parsed_output": structured,
            "word_count": len(text.split()),
            "action_item_count": len(structured.get("action_items", [])),
            "lead_count": len(structured.get("leads_mentioned", [])),
            "processed_at": datetime.now(UTC).isoformat(),
            "tenant_id": str(tenant_uuid),
        }

    # ─────────────────────── EMAIL THREAD INTELLIGENCE ────────────────────── #

    async def extract_email_thread_intelligence(self, tenant_id: Any, email_thread: str) -> dict:
        """Extract actionable intelligence from a raw email thread paste."""
        tenant_uuid = _coerce_uuid(tenant_id)

        prompt = f"""You are JARVIS, sales intelligence layer for Aliyar Solutions.
Analyse this email thread and extract commercial intelligence.

EMAIL THREAD:
{email_thread}

Return ONLY valid JSON with these exact keys:
{{
  "sender": "string — primary external sender",
  "subject": "string — inferred subject",
  "key_asks": ["list of what they are asking for"],
  "objections": ["list of objections or blockers mentioned"],
  "buying_signals": ["list of positive indicators"],
  "recommended_next_step": "specific actionable recommendation string",
  "urgency_score": 1,
  "sentiment": "POSITIVE|NEUTRAL|NEGATIVE|MIXED",
  "deal_stage": "AWARENESS|INTEREST|EVALUATION|DECISION|CLOSED_WON|CLOSED_LOST|UNKNOWN",
  "estimated_value": "string or null"
}}

urgency_score must be integer 1–10. 10 = extremely urgent."""

        try:
            response, _ = await asyncio.wait_for(
                ai_router.chat(
                    messages=[Message(role="user", content=prompt)],
                    task_type=TaskType.ANALYSIS,
                    max_tokens=800,
                ),
                timeout=30.0,
            )
            if response.error:
                raise ValueError(response.error)
            structured = _parse_json_response(response.content or "")
        except Exception as exc:
            logger.warning("Email intelligence extraction failed: %s", exc)
            structured = {}

        return {
            "raw_thread_length": len(email_thread),
            "intelligence": structured,
            "processed_at": datetime.now(UTC).isoformat(),
            "tenant_id": str(tenant_uuid),
        }

    # ─────────────────────────── SITUATION REPORT ─────────────────────────── #

    async def generate_situation_report(self, tenant_id: Any) -> dict:
        """Assemble a real-time situation report for the Captain dashboard."""
        tenant_uuid = _coerce_uuid(tenant_id)

        pipeline_data = await self._fetch_pipeline_metrics(tenant_uuid)

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "tenant_id": str(tenant_uuid),
            "pipeline": pipeline_data,
            "system_health": "OPERATIONAL",
            "top_priority_action": pipeline_data.get("top_priority_action", "Review pipeline leads"),
            "alerts": pipeline_data.get("alerts", []),
        }

    async def _fetch_pipeline_metrics(self, tenant_uuid: UUID) -> dict:
        """Pull live pipeline metrics from the database."""
        try:
            from app.models.lead import Lead  # noqa: PLC0415
            from app.models.outreach import OutreachLog, ReplyClassification, ReplyLog  # noqa: PLC0415
            from app.models.revenue import Invoice, InvoiceStatus  # noqa: PLC0415

            now = datetime.now(UTC)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await set_tenant_context(session, str(tenant_uuid))

                    leads_count = await session.scalar(
                        select(func.count()).select_from(Lead).where(Lead.tenant_id == tenant_uuid)
                    ) or 0

                    qualified_count = await session.scalar(
                        select(func.count())
                        .select_from(Lead)
                        .where(
                            Lead.tenant_id == tenant_uuid,
                            Lead.score >= 60,
                        )
                    ) or 0

                    hot_count = await session.scalar(
                        select(func.count())
                        .select_from(Lead)
                        .where(
                            Lead.tenant_id == tenant_uuid,
                            Lead.score >= 80,
                        )
                    ) or 0

                    outreach_today = await session.scalar(
                        select(func.count())
                        .select_from(OutreachLog)
                        .where(
                            OutreachLog.tenant_id == tenant_uuid,
                            OutreachLog.created_at >= today_start,
                        )
                    ) or 0

                    pending_replies = await session.scalar(
                        select(func.count())
                        .select_from(ReplyLog)
                        .where(
                            ReplyLog.tenant_id == tenant_uuid,
                            ReplyLog.classification.in_(
                                [ReplyClassification.INTERESTED, ReplyClassification.QUESTION]
                            ),
                        )
                    ) or 0

                    revenue_this_month = await session.scalar(
                        select(func.coalesce(func.sum(Invoice.paid_amount_usd), 0))
                        .where(
                            Invoice.tenant_id == tenant_uuid,
                            Invoice.status == InvoiceStatus.PAID,
                            Invoice.created_at >= month_start,
                        )
                    ) or 0

            top_action = "No outreach sent today — launch campaign immediately" if outreach_today == 0 else (
                f"Follow up on {pending_replies} warm replies" if pending_replies > 0 else "Pipeline healthy — focus on proposal conversions"
            )

            alerts = []
            if outreach_today == 0:
                alerts.append({"type": "NO_OUTREACH", "severity": "HIGH", "message": "Zero outreach sent today"})
            if hot_count > 0:
                alerts.append({"type": "HOT_LEADS", "severity": "MEDIUM", "message": f"{hot_count} hot leads are ready for review"})
            if pending_replies > 5:
                alerts.append({"type": "REPLY_BACKLOG", "severity": "MEDIUM", "message": f"{pending_replies} replies awaiting response"})

            return {
                "pipeline_leads_count": leads_count,
                "qualified_leads_count": qualified_count,
                "hot_leads_count": hot_count,
                "outreach_today": outreach_today,
                "replies_pending": pending_replies,
                "revenue_this_month": float(revenue_this_month),
                "top_priority_action": top_action,
                "alerts": alerts,
            }

        except Exception as exc:
            logger.warning("Pipeline metrics fetch failed: %s", exc)
            return {
                "pipeline_leads_count": 0,
                "qualified_leads_count": 0,
                "hot_leads_count": 0,
                "outreach_today": 0,
                "replies_pending": 0,
                "revenue_this_month": 0.0,
                "top_priority_action": "System initialising — check back shortly",
                "alerts": [],
            }

    # ──────────────────────────── THREAT DETECTION ────────────────────────── #

    async def detect_threats(self, tenant_id: Any) -> list[dict]:
        """Scan recent activity for operational threats."""
        tenant_uuid = _coerce_uuid(tenant_id)
        threats: list[dict] = []

        try:
            from app.models.outreach import ReplyLog  # noqa: PLC0415
            from app.models.lead import Lead  # noqa: PLC0415
            from app.models.governance import Proposal  # noqa: PLC0415

            now = datetime.now(UTC)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            three_days_ago = now - timedelta(days=3)
            seven_days_ago = now - timedelta(days=7)

            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await set_tenant_context(session, str(tenant_uuid))

                    # Threat: No outreach today
                    outreach_today = await session.scalar(
                        select(func.count())
                        .select_from(ReplyLog)
                        .where(
                            ReplyLog.tenant_id == tenant_uuid,
                            ReplyLog.created_at >= today_start,
                        )
                    ) or 0

                    if outreach_today == 0:
                        threats.append({
                            "type": "NO_OUTREACH_TODAY",
                            "severity": "HIGH",
                            "description": "No outreach activity recorded today. Revenue pipeline will dry up within 2–3 weeks.",
                            "action_required": "Launch an outreach campaign immediately via /outreach/send-bulk",
                        })

                    # Threat: Stale warm replies
                    stale_replies = await session.scalar(
                        select(func.count())
                        .select_from(ReplyLog)
                        .where(
                            ReplyLog.tenant_id == tenant_uuid,
                            ReplyLog.classification.in_(["INTERESTED", "QUESTION"]),
                            ReplyLog.created_at <= three_days_ago,
                        )
                    ) or 0

                    if stale_replies > 0:
                        threats.append({
                            "type": "STALE_WARM_REPLIES",
                            "severity": "HIGH",
                            "description": f"{stale_replies} warm prospect replies have gone unaddressed for 3+ days. Deal velocity is collapsing.",
                            "action_required": "Follow up with these prospects immediately — warm leads go cold within 72 hours.",
                        })

                    # Threat: No new leads in 7 days
                    recent_leads = await session.scalar(
                        select(func.count())
                        .select_from(Lead)
                        .where(
                            Lead.tenant_id == tenant_uuid,
                            Lead.created_at >= seven_days_ago,
                        )
                    ) or 0

                    if recent_leads == 0:
                        threats.append({
                            "type": "LEAD_STARVATION",
                            "severity": "CRITICAL",
                            "description": "No new leads added in the past 7 days. Pipeline will be empty in 30 days.",
                            "action_required": "Import new lead list and launch prospecting campaign immediately.",
                        })

        except Exception as exc:
            logger.warning("Threat detection encountered errors: %s", exc)
            threats.append({
                "type": "SYSTEM_DEGRADED",
                "severity": "MEDIUM",
                "description": "Threat detection encountered a partial failure. Some signals may be unavailable.",
                "action_required": "Check system logs.",
            })

        return threats


    async def current_state(self, tenant_id: Any) -> dict:
        """Return the current operational state for the mirror profile endpoint."""
        tenant_uuid = _coerce_uuid(tenant_id)
        try:
            pipeline = await self._fetch_pipeline_metrics(tenant_uuid)
            return {
                "operational_state": "active",
                "tenant_id": str(tenant_uuid),
                "pipeline_alerts": pipeline.get("alerts", []),
                "top_priority": pipeline.get("top_priority_action", "Monitor pipeline"),
                "generated_at": datetime.now(UTC).isoformat(),
            }
        except Exception as exc:
            logger.warning("current_state partial failure for tenant %s: %s", tenant_uuid, exc)
            return {"operational_state": "active"}


captain_bridge = CaptainIntelligenceBridge()
