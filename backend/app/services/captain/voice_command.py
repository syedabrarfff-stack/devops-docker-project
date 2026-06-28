"""
VoiceCommandProcessor — Natural language voice interface for Captain.
Processes transcripts, classifies intent, executes actions, returns audio-ready responses.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.services.ai.base_provider import Message, TaskType
from app.services.ai.router import ai_router

logger = logging.getLogger(__name__)

# Intent classification patterns (fast pre-filter before AI)
_INTENT_PATTERNS = {
    "ADD_LEAD": re.compile(r"add lead|new lead|add contact|new contact|add prospect", re.I),
    "SEND_OUTREACH": re.compile(r"send (email|outreach|message|campaign)|launch campaign", re.I),
    "CHECK_PIPELINE": re.compile(r"pipeline|how many leads|lead count|how.{0,20}doing|status", re.I),
    "GET_BRIEFING": re.compile(r"briefing|brief me|morning brief|update me|what.{0,20}happening|situation", re.I),
    "APPROVE_PROPOSAL": re.compile(r"approve|sign off|authorise|send proposal", re.I),
    "TASK_ASSIGNMENT": re.compile(r"assign|task|schedule|remind me|follow up on", re.I),
}


def _coerce_uuid(val: Any) -> UUID:
    return UUID(str(val)) if not isinstance(val, UUID) else val


def _parse_json_response(text: str) -> dict:
    try:
        match = re.search(r"\{[\s\S]+\}", text or "")
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    return {}


def _quick_classify(transcript: str) -> str | None:
    """Fast pattern-based intent classification before calling AI."""
    for intent, pattern in _INTENT_PATTERNS.items():
        if pattern.search(transcript):
            return intent
    return None


class VoiceCommandProcessor:
    """Processes voice transcripts and generates audio-ready briefing scripts."""

    # ────────────────────────── VOICE TRANSCRIPT PROCESSOR ───────────────── #

    async def process_voice_transcript(self, tenant_id: Any, transcript: str) -> dict:
        """Classify intent, extract entities, and generate JARVIS response text."""
        tenant_uuid = _coerce_uuid(tenant_id)

        # Fast pre-classification
        fast_intent = _quick_classify(transcript)

        prompt = f"""You are JARVIS, the executive operations intelligence for Aliyar Solutions.
Captain has sent this voice transcript:

TRANSCRIPT:
"{transcript}"

Pre-classified intent hint: {fast_intent or "unknown — use your judgement"}

Classify the intent and extract relevant entities. Return ONLY valid JSON:
{{
  "intent": "ADD_LEAD|SEND_OUTREACH|CHECK_PIPELINE|GET_BRIEFING|APPROVE_PROPOSAL|TASK_ASSIGNMENT|GENERAL_QUERY",
  "confidence": 0.9,
  "entities": {{
    "company_name": "string or null",
    "contact_name": "string or null",
    "email": "string or null",
    "amount": "string or null",
    "deadline": "string or null",
    "subject": "string or null",
    "any_other_key": "value"
  }},
  "action_taken": {{
    "type": "string describing what JARVIS did or would do",
    "status": "EXECUTED|QUEUED|REQUIRES_CONFIRMATION|NOT_APPLICABLE",
    "details": "string or null"
  }},
  "response_text": "What JARVIS says back to Captain — 1–3 sentences, calm, precise, British executive tone."
}}"""

        try:
            response, _ = await ai_router.chat(
                messages=[Message(role="user", content=prompt)],
                task_type=TaskType.FAST,
                max_tokens=600,
            )
            if response.error:
                raise ValueError(response.error)
            result = _parse_json_response(response.content)
            if result and "intent" in result:
                result["transcript"] = transcript
                result["processed_at"] = datetime.now(UTC).isoformat()
                result["tenant_id"] = str(tenant_uuid)
                return result
        except Exception as exc:
            logger.warning("Voice transcript processing failed: %s", exc)

        # Fallback
        intent = fast_intent or "GENERAL_QUERY"
        return {
            "intent": intent,
            "confidence": 0.5,
            "entities": {},
            "action_taken": {"type": "LOGGED", "status": "REQUIRES_CONFIRMATION", "details": None},
            "response_text": (
                f"Understood, Captain. I've logged that as a {intent.replace('_', ' ').lower()} request. "
                "Please confirm and I'll proceed immediately."
            ),
            "transcript": transcript,
            "processed_at": datetime.now(UTC).isoformat(),
            "tenant_id": str(tenant_uuid),
        }

    # ─────────────────────── AUDIO BRIEFING SCRIPT GENERATOR ─────────────── #

    async def generate_audio_briefing_script(self, tenant_id: Any) -> str:
        """Generate a natural-language morning briefing script for TTS delivery."""
        tenant_uuid = _coerce_uuid(tenant_id)

        # Pull pipeline context
        pipeline = await self._get_pipeline_snapshot(tenant_uuid)
        today = datetime.now(UTC).strftime("%A, %d %B %Y")

        prompt = f"""You are JARVIS, the executive operational intelligence for Aliyar Solutions.
Write a morning briefing script to be read aloud to Captain Syed Abrar via ElevenLabs TTS.

CURRENT DATA:
- Date: {today}
- Pipeline leads: {pipeline.get('total_leads', 0)}
- Outreach sent today: {pipeline.get('outreach_today', 0)}
- Warm replies pending: {pipeline.get('warm_replies', 0)}
- Revenue this month: ${pipeline.get('revenue_month', 0):,.2f}
- Active alerts: {pipeline.get('alerts', [])}

SCRIPT REQUIREMENTS:
1. Open with "Good morning, Captain" — natural, not robotic
2. Give a 2-sentence situation summary
3. State the 3 most important things to do today
4. Mention any critical alerts if present
5. Close with a confident, motivating statement
6. Total length: 150–200 words
7. Tone: calm, precise, British executive assistant — think M from James Bond
8. Write plain text only — no markdown, no bullet points, no headers
9. Pause cues: use commas and full stops for natural pacing"""

        try:
            response, _ = await ai_router.chat(
                messages=[Message(role="user", content=prompt)],
                task_type=TaskType.FAST,
                max_tokens=400,
            )
            if response.error:
                raise ValueError(response.error)
            script = (response.content or "").strip()
            if len(script) > 100:
                return script
        except Exception as exc:
            logger.warning("Audio briefing script generation failed: %s", exc)

        # Deterministic fallback script
        alert_text = ""
        if pipeline.get("alerts"):
            alert_text = f" I should also flag that {pipeline['alerts'][0].get('message', 'there is an active system alert requiring your attention')}."

        return (
            f"Good morning, Captain. Today is {today}. "
            f"Here is your operational briefing for Aliyar Solutions. "
            f"We currently have {pipeline.get('total_leads', 0)} leads in the pipeline, "
            f"with {pipeline.get('warm_replies', 0)} warm prospects awaiting follow-up. "
            f"Revenue this month stands at ${pipeline.get('revenue_month', 0):,.0f}."
            f"{alert_text} "
            f"Today's priority actions are: first, send today's outreach campaign. "
            f"Second, follow up on all warm replies. "
            f"Third, review any proposals awaiting approval. "
            f"You have everything you need to win today, Captain. Let us proceed."
        )

    async def _get_pipeline_snapshot(self, tenant_uuid: UUID) -> dict:
        """Pull lightweight pipeline data for briefing generation."""
        try:
            from app.core.database import AsyncSessionLocal, set_tenant_context  # noqa: PLC0415
            from app.models.lead import Lead  # noqa: PLC0415
            from app.models.outreach import OutreachLog, ReplyClassification, ReplyLog  # noqa: PLC0415
            from app.models.revenue import Invoice, InvoiceStatus  # noqa: PLC0415
            from sqlalchemy import func, select  # noqa: PLC0415

            now = datetime.now(UTC)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await set_tenant_context(session, str(tenant_uuid))

                    total_leads = await session.scalar(
                        select(func.count()).select_from(Lead).where(Lead.tenant_id == tenant_uuid)
                    ) or 0

                    qualified_leads = await session.scalar(
                        select(func.count())
                        .select_from(Lead)
                        .where(Lead.tenant_id == tenant_uuid, Lead.score >= 60)
                    ) or 0

                    outreach_today = await session.scalar(
                        select(func.count())
                        .select_from(OutreachLog)
                        .where(OutreachLog.tenant_id == tenant_uuid, OutreachLog.created_at >= today_start)
                    ) or 0

                    warm_replies = await session.scalar(
                        select(func.count())
                        .select_from(ReplyLog)
                        .where(
                            ReplyLog.tenant_id == tenant_uuid,
                            ReplyLog.classification == ReplyClassification.INTERESTED,
                        )
                    ) or 0

                    revenue_month = await session.scalar(
                        select(func.coalesce(func.sum(Invoice.paid_amount_usd), 0))
                        .where(
                            Invoice.tenant_id == tenant_uuid,
                            Invoice.status == InvoiceStatus.PAID,
                            Invoice.created_at >= month_start,
                        )
                    ) or 0

            alerts = []
            if outreach_today == 0:
                alerts.append({"message": "no outreach has been sent today — the pipeline requires immediate activity"})

            return {
                "total_leads": total_leads,
                "qualified_leads": qualified_leads,
                "outreach_today": outreach_today,
                "warm_replies": warm_replies,
                "revenue_month": float(revenue_month),
                "alerts": alerts,
            }

        except Exception as exc:
            logger.warning("Pipeline snapshot for briefing failed: %s", exc)
            return {"total_leads": 0, "outreach_today": 0, "warm_replies": 0, "revenue_month": 0.0, "alerts": []}


voice_command_processor = VoiceCommandProcessor()
