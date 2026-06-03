"""
Layer 5 — Client Call Intelligence

Full pipeline for every client call:

Pre-call (1 hour before):
  1. DIO collects all client history, company intel, previous interactions
  2. JARVIS generates comprehensive briefing PDF
  3. AI Council reviews and refines the briefing
  4. ElevenLabs voice agent configured with approved script

During call:
  - ElevenLabs voice agent handles conversation with human-grade voice
  - Follows approved script with dynamic objection handling

Post-call:
  1. Transcript analyzed
  2. Council debrief session
  3. Improvement directives generated for next call
  4. Lead/client record updated
"""
from __future__ import annotations

import io
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.department_intelligence import (
    CallStatus,
    ClientCallIntelligence,
    DepartmentIntelligenceOfficer,
)
from app.services.ai.base_provider import Message, TaskType
from app.services.ai.council import intelligence_council
from app.services.ai.router import ai_router
from app.services.memory.human_intelligence import human_intelligence_context

logger = logging.getLogger(__name__)

ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"
ELEVENLABS_AGENT_BASE = "https://api.elevenlabs.io/v1/convai/agents"


class CallIntelligenceService:
    """
    Manages the full lifecycle of client calls — from briefing generation
    to ElevenLabs voice agent deployment to post-call debrief.
    """

    async def schedule_call(
        self,
        db: AsyncSession,
        tenant_id: str,
        department_code: str,
        client_name: str,
        client_company: str,
        client_email: str | None,
        scheduled_at: datetime,
        call_topic: str,
        call_objective: str | None = None,
    ) -> ClientCallIntelligence:
        """Register an upcoming client call in the intelligence system."""
        tenant_uuid = uuid.UUID(str(tenant_id))

        dio = await db.scalar(
            select(DepartmentIntelligenceOfficer).where(
                DepartmentIntelligenceOfficer.tenant_id == tenant_uuid,
                DepartmentIntelligenceOfficer.department_code == department_code,
            )
        )
        if not dio:
            raise ValueError(f"No DIO found for department: {department_code}")

        call = ClientCallIntelligence(
            tenant_id=tenant_uuid,
            dio_id=dio.id,
            department_code=department_code,
            client_name=client_name,
            client_company=client_company,
            client_email=client_email,
            scheduled_at=scheduled_at,
            call_topic=call_topic,
            call_objective=call_objective,
            status=CallStatus.SCHEDULED.value,
        )
        db.add(call)
        await db.commit()
        await db.refresh(call)

        logger.info("Call scheduled: %s | %s | %s", client_name, client_company, scheduled_at)
        return call

    async def generate_pre_call_briefing(
        self, tenant_id: str, call_id: str
    ) -> dict[str, Any]:
        """
        Generate the comprehensive pre-call briefing package:
        - Client intelligence summary
        - What to say / what NOT to say
        - Objection handlers
        - ElevenLabs-ready call script
        """
        tenant_uuid = uuid.UUID(str(tenant_id))

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, str(tenant_uuid))
            call = await db.get(ClientCallIntelligence, uuid.UUID(call_id))
            if not call:
                raise ValueError(f"Call {call_id} not found")

            call.status = CallStatus.BRIEFING.value
            await db.commit()

        # Generate briefing content via AI
        briefing_data = await self._generate_briefing_content(call)

        # Generate PDF
        pdf_bytes = await self._generate_briefing_pdf(call, briefing_data)

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, str(tenant_uuid))
            call = await db.get(ClientCallIntelligence, uuid.UUID(call_id))
            if call:
                call.briefing_content = briefing_data["briefing_content"]
                call.what_to_say = briefing_data["what_to_say"]
                call.what_not_to_say = briefing_data["what_not_to_say"]
                call.objection_handlers = briefing_data["objection_handlers"]
                call.context_summary = briefing_data["context_summary"]
                call.call_script = briefing_data["call_script"]
                call.humanization_notes = briefing_data["humanization_notes"]
                call.briefing_pdf_url = f"/pdfs/briefings/{call_id}_briefing.pdf"
                call.status = CallStatus.COUNCIL_REVIEW.value
                await db.commit()

        logger.info("Pre-call briefing generated: %s | %s", call.client_name, call.client_company)
        return {
            "call_id": call_id,
            "briefing_pdf_url": f"/pdfs/briefings/{call_id}_briefing.pdf",
            "what_to_say_count": len(briefing_data["what_to_say"]),
            "objection_handlers_count": len(briefing_data["objection_handlers"]),
            "status": "council_review",
        }

    async def council_review_briefing(
        self, tenant_id: str, call_id: str
    ) -> dict[str, Any]:
        """Submit the pre-call briefing to Council for refinement before the call."""
        tenant_uuid = uuid.UUID(str(tenant_id))

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, str(tenant_uuid))
            call = await db.get(ClientCallIntelligence, uuid.UUID(call_id))
            if not call:
                raise ValueError(f"Call {call_id} not found")

            council_question = (
                f"Review this pre-call briefing for a {call.call_topic} call with "
                f"{call.client_name} from {call.client_company}.\n\n"
                f"Call objective: {call.call_objective}\n\n"
                f"Current briefing:\n{(call.briefing_content or '')[:2000]}\n\n"
                f"Key talking points:\n{json.dumps(call.what_to_say or [])}\n\n"
                f"Evaluate: (1) briefing quality and completeness, "
                f"(2) talking point effectiveness, "
                f"(3) missing critical information, "
                f"(4) specific improvements to the call script, "
                f"(5) risk factors to avoid."
            )

        council_result = await intelligence_council.convene(
            question=council_question,
            context={
                "call_id": call_id,
                "client": call.client_company,
                "topic": call.call_topic,
                "purpose": "pre_call_briefing_review",
            },
            council_type="call_briefing",
            tenant_id=tenant_id,
        )

        # Build refined PDF with Council improvements
        refined_pdf_bytes = await self._generate_refined_briefing_pdf(call, council_result)

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, str(tenant_uuid))
            call = await db.get(ClientCallIntelligence, uuid.UUID(call_id))
            if call:
                call.council_session_id = uuid.UUID(council_result.session_id)
                call.council_refinements = await self._extract_council_refinements(
                    council_result.reasoning
                )
                call.council_approved = council_result.decision in ("APPROVE",)
                call.refined_briefing_pdf_url = f"/pdfs/briefings/{call_id}_refined.pdf"
                call.status = CallStatus.READY.value
                await db.commit()

        return {
            "call_id": call_id,
            "council_session_id": council_result.session_id,
            "council_decision": council_result.decision,
            "council_score": council_result.score,
            "refinements_count": len(call.council_refinements) if call else 0,
            "refined_briefing_pdf_url": f"/pdfs/briefings/{call_id}_refined.pdf",
            "status": "ready",
        }

    async def deploy_elevenlabs_agent(
        self, tenant_id: str, call_id: str
    ) -> dict[str, Any]:
        """Deploy an ElevenLabs voice agent with the approved call script."""
        if not settings.ELEVENLABS_API_KEY:
            return {"error": "ElevenLabs API key not configured", "call_id": call_id}

        tenant_uuid = uuid.UUID(str(tenant_id))

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, str(tenant_uuid))
            call = await db.get(ClientCallIntelligence, uuid.UUID(call_id))
            if not call:
                raise ValueError(f"Call {call_id} not found")
            if not call.call_script:
                raise ValueError("Call script not generated — run pre-call briefing first")

        voice_id = settings.ELEVENLABS_VOICE_ID
        agent_name = f"JARVIS-{call.department_code.upper()}-{call.client_company[:10]}"

        system_prompt = self._build_elevenlabs_system_prompt(call)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    ELEVENLABS_AGENT_BASE,
                    headers={
                        "xi-api-key": settings.ELEVENLABS_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json={
                        "name": agent_name,
                        "conversation_config": {
                            "agent": {
                                "prompt": {"prompt": system_prompt},
                                "first_message": self._build_first_message(call),
                                "language": "en",
                            },
                            "tts": {
                                "voice_id": voice_id,
                                "model_id": "eleven_turbo_v2",
                                "optimize_streaming_latency": 3,
                            },
                            "asr": {"quality": "high"},
                        },
                        "platform_settings": {
                            "auth": {"enable_auth": False},
                        },
                    },
                )

                if response.status_code in (200, 201):
                    agent_data = response.json()
                    agent_id = agent_data.get("agent_id") or agent_data.get("id")

                    async with AsyncSessionLocal() as db:
                        await set_tenant_context(db, str(tenant_uuid))
                        call = await db.get(ClientCallIntelligence, uuid.UUID(call_id))
                        if call:
                            call.voice_agent_id = agent_id
                            call.voice_personality = "Daniel — British professional, intelligent, confident"
                            call.elevenlabs_voice_id = voice_id
                            await db.commit()

                    logger.info("ElevenLabs agent deployed: %s | agent_id=%s", agent_name, agent_id)
                    return {
                        "call_id": call_id,
                        "agent_id": agent_id,
                        "agent_name": agent_name,
                        "voice_id": voice_id,
                        "status": "deployed",
                    }
                else:
                    logger.warning(
                        "ElevenLabs agent creation failed: %d | %s",
                        response.status_code, response.text
                    )
                    return {
                        "call_id": call_id,
                        "error": f"ElevenLabs API returned {response.status_code}",
                        "details": response.text[:300],
                    }

        except httpx.HTTPError as exc:
            logger.error("ElevenLabs API error: %s", exc)
            return {"call_id": call_id, "error": str(exc)}

    async def record_call_outcome(
        self,
        db: AsyncSession,
        tenant_id: str,
        call_id: str,
        outcome: str,
        transcript: str | None = None,
        recording_url: str | None = None,
    ) -> dict[str, Any]:
        """Record the post-call outcome and trigger debrief generation."""
        tenant_uuid = uuid.UUID(str(tenant_id))
        call = await db.get(ClientCallIntelligence, uuid.UUID(call_id))
        if not call or call.tenant_id != tenant_uuid:
            raise ValueError("Call not found")

        call.outcome = outcome
        call.call_transcript = transcript
        call.call_recording_url = recording_url
        call.status = CallStatus.DEBRIEFING.value
        await db.commit()

        # Generate post-call debrief
        debrief = await self._generate_post_call_debrief(call, outcome, transcript)

        call = await db.get(ClientCallIntelligence, uuid.UUID(call_id))
        if call:
            call.post_call_debrief = debrief["debrief"]
            call.improvements_for_next = debrief["improvements"]
            call.council_debrief_pdf_url = f"/pdfs/debriefs/{call_id}_debrief.pdf"
            call.status = CallStatus.COMPLETED.value
            await db.commit()

        return {
            "call_id": call_id,
            "outcome": outcome,
            "debrief_generated": True,
            "improvements_count": len(debrief["improvements"]),
            "debrief_pdf_url": f"/pdfs/debriefs/{call_id}_debrief.pdf",
            "status": "completed",
        }

    async def get_upcoming_calls(
        self, db: AsyncSession, tenant_id: str, limit: int = 20
    ) -> list[dict]:
        tenant_uuid = uuid.UUID(str(tenant_id))
        result = await db.execute(
            select(ClientCallIntelligence)
            .where(
                ClientCallIntelligence.tenant_id == tenant_uuid,
                ClientCallIntelligence.scheduled_at >= datetime.now(timezone.utc),
            )
            .order_by(ClientCallIntelligence.scheduled_at)
            .limit(limit)
        )
        return [self._serialize_call(c) for c in result.scalars().all()]

    async def get_all_calls(
        self, db: AsyncSession, tenant_id: str, limit: int = 50
    ) -> list[dict]:
        tenant_uuid = uuid.UUID(str(tenant_id))
        result = await db.execute(
            select(ClientCallIntelligence)
            .where(ClientCallIntelligence.tenant_id == tenant_uuid)
            .order_by(ClientCallIntelligence.scheduled_at.desc())
            .limit(limit)
        )
        return [self._serialize_call(c) for c in result.scalars().all()]

    async def _generate_briefing_content(self, call: ClientCallIntelligence) -> dict:
        """Generate comprehensive briefing content."""
        prompt = f"""You are JARVIS, the intelligence core of Aliyar Solutions.

Use this M2 human intelligence context before writing:
{human_intelligence_context(max_chars=1800)}

Generate a comprehensive pre-call briefing for a {call.call_topic} call with:
- Client: {call.client_name}
- Company: {call.client_company}
- Email: {call.client_email or 'not provided'}
- Objective: {call.call_objective or 'not specified'}
- Department handling: {call.department_code.upper()}

Return a JSON object with these exact keys:
{{
  "briefing_content": "Full 3-4 paragraph briefing covering client profile, company analysis, call strategy",
  "context_summary": "2 paragraph executive summary of the client context",
  "what_to_say": ["list of 8-10 specific key talking points"],
  "what_not_to_say": ["list of 5-7 forbidden topics/phrases — pricing specifics, competitor comparisons, etc"],
  "objection_handlers": {{
    "objection 1": "response 1",
    "objection 2": "response 2"
  }},
  "call_script": "Full call script with opening, key sections, and close — written to sound completely natural and human",
  "humanization_notes": "Specific notes on tone, pacing, personality — how to sound like a senior Aliyar Solutions executive"
}}

The call script must sound 100% human — a senior executive named according to the department persona.
Never mention AI, automation, or JARVIS. Always refer to 'our team' and 'Aliyar Solutions'.
Return only valid JSON, no markdown."""

        try:
            response, _ = await ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=TaskType.STRATEGY,
            )
            data = json.loads(response.content.strip())
            return data
        except Exception as exc:
            logger.warning("Briefing content generation failed: %s", exc)
            return {
                "briefing_content": f"Pre-call briefing for {call.client_name} at {call.client_company}",
                "context_summary": f"Call scheduled for {call.call_topic}",
                "what_to_say": ["Introduce Aliyar Solutions", "Understand client needs", "Present relevant services"],
                "what_not_to_say": ["Specific pricing without context", "Competitor names"],
                "objection_handlers": {"cost concern": "Our pricing reflects enterprise-grade delivery"},
                "call_script": f"Hello {call.client_name}, I'm calling from Aliyar Solutions regarding {call.call_topic}...",
                "humanization_notes": "Confident, measured tone. Senior executive style.",
            }

    async def _generate_briefing_pdf(
        self, call: ClientCallIntelligence, briefing_data: dict
    ) -> bytes:
        """Generate professional pre-call briefing PDF."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import cm
            from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm,
                                    topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()

            title_s = ParagraphStyle("T", parent=styles["Heading1"], fontSize=18,
                                      textColor=colors.HexColor("#1a1a2e"), spaceAfter=4)
            sub_s = ParagraphStyle("S", parent=styles["Normal"], fontSize=10,
                                    textColor=colors.HexColor("#555588"), spaceAfter=10)
            section_s = ParagraphStyle("Sec", parent=styles["Heading2"], fontSize=12,
                                        textColor=colors.HexColor("#2c3e50"), spaceBefore=10, spaceAfter=4)
            body_s = ParagraphStyle("B", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=6)
            green_s = ParagraphStyle("G", parent=styles["Normal"], fontSize=10, leading=14,
                                      textColor=colors.HexColor("#1e8449"), spaceAfter=4)
            red_s = ParagraphStyle("R", parent=styles["Normal"], fontSize=10, leading=14,
                                    textColor=colors.HexColor("#c0392b"), spaceAfter=4)

            elements = []
            elements.append(Paragraph("PRE-CALL INTELLIGENCE BRIEFING", title_s))
            elements.append(Paragraph(
                f"CONFIDENTIAL — {call.client_name} | {call.client_company} | {call.scheduled_at.strftime('%Y-%m-%d %H:%M UTC')}",
                sub_s
            ))
            elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")))
            elements.append(Spacer(1, 0.4*cm))

            elements.append(Paragraph("CALL OVERVIEW", section_s))
            meta = [
                ["Topic", call.call_topic], ["Objective", call.call_objective or "Build relationship"],
                ["Department", call.department_code.upper()], ["Scheduled", call.scheduled_at.strftime("%Y-%m-%d %H:%M UTC")],
            ]
            t = Table(meta, colWidths=[4*cm, 12*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eeeeff")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ccccdd")),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.3*cm))

            elements.append(Paragraph("CONTEXT SUMMARY", section_s))
            elements.append(Paragraph(briefing_data.get("context_summary", ""), body_s))

            elements.append(Paragraph("WHAT TO SAY", section_s))
            for item in briefing_data.get("what_to_say", []):
                elements.append(Paragraph(f"✓ {item}", green_s))

            elements.append(Paragraph("WHAT NOT TO SAY", section_s))
            for item in briefing_data.get("what_not_to_say", []):
                elements.append(Paragraph(f"✗ {item}", red_s))

            elements.append(Paragraph("CALL SCRIPT", section_s))
            elements.append(Paragraph(briefing_data.get("call_script", "")[:3000], body_s))

            elements.append(Spacer(1, cm))
            elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#ccccdd")))
            elements.append(Paragraph(
                f"JARVIS Intelligence | Aliyar Solutions | CONFIDENTIAL | {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
                ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7,
                               textColor=colors.grey, alignment=1)
            ))

            doc.build(elements)
            return buf.getvalue()
        except ImportError:
            return b"%PDF-1.4 briefing-placeholder"

    async def _generate_refined_briefing_pdf(
        self, call: ClientCallIntelligence, council_result: Any
    ) -> bytes:
        """Generate the Council-refined briefing PDF."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import cm
            from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm,
                                    topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()
            elements = []

            title_s = ParagraphStyle("T", parent=styles["Heading1"], fontSize=18,
                                      textColor=colors.HexColor("#1a1a2e"))
            section_s = ParagraphStyle("Sec", parent=styles["Heading2"], fontSize=12,
                                        textColor=colors.HexColor("#2c3e50"), spaceBefore=10, spaceAfter=4)
            body_s = ParagraphStyle("B", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=6)

            elements.append(Paragraph("COUNCIL-REFINED CALL BRIEFING", title_s))
            elements.append(Paragraph(
                f"{call.client_name} | {call.client_company} | Council Score: {council_result.score:.1f}/100",
                ParagraphStyle("S", parent=styles["Normal"], fontSize=10,
                               textColor=colors.HexColor("#555588"))
            ))
            elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")))
            elements.append(Spacer(1, 0.4*cm))

            elements.append(Paragraph("COUNCIL DECISION", section_s))
            verdict_color = colors.HexColor("#27ae60") if council_result.decision == "APPROVE" else colors.HexColor("#e74c3c")
            elements.append(Paragraph(
                f"Decision: {council_result.decision} | Score: {council_result.score:.1f}/100",
                ParagraphStyle("V", parent=styles["Normal"], fontSize=14, textColor=verdict_color, spaceAfter=6)
            ))

            elements.append(Paragraph("COUNCIL REFINEMENTS & RECOMMENDATIONS", section_s))
            elements.append(Paragraph(council_result.reasoning[:3000], body_s))

            elements.append(Spacer(1, cm))
            elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#ccccdd")))
            elements.append(Paragraph(
                f"AI Council | JARVIS Intelligence | {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
                ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7,
                               textColor=colors.grey, alignment=1)
            ))

            doc.build(elements)
            return buf.getvalue()
        except ImportError:
            return b"%PDF-1.4 refined-briefing-placeholder"

    async def _generate_post_call_debrief(
        self, call: ClientCallIntelligence, outcome: str, transcript: str | None
    ) -> dict:
        prompt = f"""You are JARVIS, analyzing a completed client call.

Call details:
- Client: {call.client_name} at {call.client_company}
- Topic: {call.call_topic}
- Outcome: {outcome}
- Transcript excerpt: {(transcript or '')[:1000]}

Generate a post-call debrief. Return JSON:
{{
  "debrief": "3-4 paragraph analysis of what happened, what worked, what did not",
  "improvements": ["list of 5 specific improvements for the next call with this client"]
}}
Return only valid JSON."""

        try:
            response, _ = await ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=TaskType.ANALYSIS,
            )
            return json.loads(response.content.strip())
        except Exception:
            return {
                "debrief": f"Post-call analysis for {outcome} outcome with {call.client_company}.",
                "improvements": ["Follow up within 24 hours", "Send proposal if requested"],
            }

    async def _extract_council_refinements(self, reasoning: str) -> list[str]:
        prompt = f"""Extract 5 specific refinements from this Council analysis for a call briefing.
Return as JSON array of strings. Only valid JSON.
Analysis: {reasoning[:1500]}"""
        try:
            response, _ = await ai_router.chat(
                [Message(role="user", content=prompt)], task_type=TaskType.FAST
            )
            items = json.loads(response.content.strip())
            return items if isinstance(items, list) else []
        except Exception:
            return [reasoning[:200]]

    def _build_elevenlabs_system_prompt(self, call: ClientCallIntelligence) -> str:
        return f"""You are a senior representative from Aliyar Solutions, a global technology company.
Your name is relevant to the {call.department_code} department team.
You are calling {call.client_name} from {call.client_company} regarding: {call.call_topic}.

Objective: {call.call_objective or 'Understand needs, present relevant Aliyar Solutions services, advance the relationship'}

CRITICAL RULES:
- Never mention AI, automation scripts, or that you are a voice assistant
- Always say "our team" or "Aliyar Solutions" — never "I" alone
- Speak naturally, confidently, and professionally
- Use the call script but adapt naturally to the conversation
- Your goal: {call.call_objective or 'advance the business relationship'}

Call script context: {(call.call_script or '')[:1500]}
{(call.humanization_notes or '')}"""

    def _build_first_message(self, call: ClientCallIntelligence) -> str:
        return (
            f"Hello, is this {call.client_name}? "
            f"Great — this is calling from Aliyar Solutions. "
            f"I hope I'm catching you at a good time. "
            f"I'm reaching out regarding {call.call_topic}. Do you have a few minutes to connect?"
        )

    def _serialize_call(self, c: ClientCallIntelligence) -> dict:
        return {
            "id": str(c.id),
            "department_code": c.department_code,
            "client_name": c.client_name,
            "client_company": c.client_company,
            "client_email": c.client_email,
            "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
            "call_topic": c.call_topic,
            "call_objective": c.call_objective,
            "briefing_pdf_url": c.briefing_pdf_url,
            "refined_briefing_pdf_url": c.refined_briefing_pdf_url,
            "council_approved": c.council_approved,
            "council_score": None,
            "voice_agent_id": c.voice_agent_id,
            "elevenlabs_voice_id": c.elevenlabs_voice_id,
            "outcome": c.outcome,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }


call_intelligence_service = CallIntelligenceService()
