"""
JARVIS Cialdini Engine — persuasion engineering based on Robert Cialdini's
6 principles: Reciprocity, Commitment, Social Proof, Authority, Liking, Scarcity.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from app.services.ai.router import ai_router
from app.services.ai.base_provider import Message, TaskType

logger = logging.getLogger(__name__)

CIALDINI_SYSTEM = """You are a world-class persuasion engineer and copywriter specializing in
Cialdini's 6 principles of influence. You help Aliyar Solutions — a premium AI technology company —
craft compelling outreach that converts leads into clients ethically and effectively.

The 6 principles:
1. RECIPROCITY: Give value first (insights, audit, free analysis)
2. COMMITMENT: Get small yes → build toward big yes
3. SOCIAL_PROOF: Clients, case studies, industry adoption
4. AUTHORITY: Expertise, credentials, thought leadership
5. LIKING: Genuine connection, similarity, shared values
6. SCARCITY: Limited availability, time-sensitive opportunity

Always maintain Aliyar Solutions' premium, professional tone. Never be pushy or manipulative.
Output structured JSON only."""

SEQUENCE_TEMPLATES = {
    "email_1": {
        "principles": ["reciprocity", "authority"],
        "day": 0,
        "intent": "Establish credibility and give immediate value with a free insight or audit offer.",
    },
    "email_2": {
        "principles": ["social_proof", "liking"],
        "day": 3,
        "intent": "Build rapport with a relevant case study and show you understand their specific situation.",
    },
    "email_3": {
        "principles": ["commitment", "scarcity"],
        "day": 7,
        "intent": "Create gentle urgency and invite a small commitment (15-min call, quick question).",
    },
}


def _parse_json_response(content: str) -> dict:
    """Extract JSON from AI response."""
    try:
        match = re.search(r"\{.*\}", content or "", re.DOTALL)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    return {}


def _parse_json_array(content: str) -> list:
    """Extract JSON array from AI response."""
    try:
        match = re.search(r"\[.*\]", content or "", re.DOTALL)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    return []


class CialdiniEngine:
    """Persuasion engineering engine using Cialdini's principles."""

    async def engineer_outreach(
        self,
        tenant_id: UUID,
        lead_data: dict,
        email_draft: str,
    ) -> dict[str, Any]:
        """Analyze and enhance an email draft using all 6 Cialdini principles."""
        company = lead_data.get("company_name") or lead_data.get("company", "the company")
        industry = lead_data.get("industry", "technology")

        prompt = (
            f"Lead context:\n"
            f"- Company: {company}\n"
            f"- Industry: {industry}\n"
            f"- Notes: {lead_data.get('notes', 'None')}\n\n"
            f"Original email draft:\n{email_draft}\n\n"
            f"Analyze this email for Cialdini's 6 principles and provide:\n"
            f"1. An enhanced version of the email\n"
            f"2. For each principle: applied (bool), implementation (string), strength_rating (1-5)\n"
            f"3. A persuasion_score (0-100)\n"
            f"4. 3 improvement_suggestions (list)\n\n"
            f"Return JSON with keys: enhanced_email, principles_applied (object with each principle), "
            f"persuasion_score, improvement_suggestions."
        )

        try:
            response, _ = await ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=TaskType.REASONING,
                system_prompt=CIALDINI_SYSTEM,
                max_tokens=1200,
            )
            if response.error:
                raise ValueError(response.error)
            parsed = _parse_json_response(response.content)

            # Normalize principles_applied
            raw_principles = parsed.get("principles_applied", {})
            principles_list = []
            principle_names = ["reciprocity", "commitment", "social_proof", "authority", "liking", "scarcity"]
            for p in principle_names:
                p_data = raw_principles.get(p, {})
                principles_list.append({
                    "principle": p,
                    "applied": bool(p_data.get("applied", False)),
                    "implementation": p_data.get("implementation", f"Not applied."),
                    "strength_rating": int(p_data.get("strength_rating", 1)),
                })

            result = {
                "tenant_id": str(tenant_id),
                "original_email": email_draft,
                "enhanced_email": parsed.get("enhanced_email", email_draft),
                "principles_applied": principles_list,
                "persuasion_score": float(parsed.get("persuasion_score", 50)),
                "improvement_suggestions": parsed.get("improvement_suggestions", []),
                "engineered_at": datetime.now(timezone.utc).isoformat(),
            }

            # Persist session
            await self._persist_session(tenant_id, lead_data, email_draft, result)
            return result

        except Exception as exc:
            logger.warning("Cialdini enhancement failed: %s", exc)
            return {
                "tenant_id": str(tenant_id),
                "original_email": email_draft,
                "enhanced_email": email_draft,
                "principles_applied": [],
                "persuasion_score": 0,
                "improvement_suggestions": ["AI enhancement temporarily unavailable"],
                "engineered_at": datetime.now(timezone.utc).isoformat(),
            }

    async def generate_cialdini_sequence(
        self,
        tenant_id: UUID,
        lead_data: dict,
    ) -> list[dict[str, Any]]:
        """Generate a 3-email sequence engineered for lead psychology."""
        company = lead_data.get("company_name") or lead_data.get("company", "your company")
        industry = lead_data.get("industry", "your industry")
        pain_points = lead_data.get("pain_points", [])
        notes = lead_data.get("notes", "")

        sequence = []

        for seq_key, config in SEQUENCE_TEMPLATES.items():
            principles = config["principles"]
            day = config["day"]
            intent = config["intent"]

            prompt = (
                f"Lead: {company} in {industry}\n"
                f"Pain points: {pain_points}\n"
                f"Notes: {notes}\n\n"
                f"Write Email {seq_key[-1]} of a 3-part outreach sequence.\n"
                f"Primary principles to apply: {', '.join(principles)}\n"
                f"Intent: {intent}\n"
                f"Send on day {day} of the sequence.\n\n"
                f"Return JSON with keys: subject (string), body (string), "
                f"principle_focus (list of principle names), send_day (integer)."
            )

            try:
                response, _ = await ai_router.chat(
                    [Message(role="user", content=prompt)],
                    task_type=TaskType.REASONING,
                    system_prompt=CIALDINI_SYSTEM,
                    max_tokens=800,
                )
                if response.error:
                    raise ValueError(response.error)
                parsed = _parse_json_response(response.content)

                sequence.append({
                    "email_number": int(seq_key[-1]),
                    "subject": parsed.get("subject", f"Following up — {company}"),
                    "body": parsed.get("body", "Email generation unavailable."),
                    "principle_focus": parsed.get("principle_focus", principles),
                    "send_day": parsed.get("send_day", day),
                })
            except Exception as exc:
                logger.warning("Sequence email %s generation failed: %s", seq_key, exc)
                sequence.append({
                    "email_number": int(seq_key[-1]),
                    "subject": f"A thought for {company}",
                    "body": "Email generation temporarily unavailable.",
                    "principle_focus": principles,
                    "send_day": day,
                })

        return sequence

    async def _persist_session(
        self,
        tenant_id: UUID,
        lead_data: dict,
        original_email: str,
        result: dict,
    ) -> None:
        """Store Cialdini session in database."""
        try:
            from app.core.database import AsyncSessionLocal, set_tenant_context
            import uuid
            from sqlalchemy import text

            lead_id = lead_data.get("id") or lead_data.get("lead_id")

            async with AsyncSessionLocal() as session:
                await set_tenant_context(session, tenant_id)
                await session.execute(
                    text(
                        """
                        INSERT INTO cialdini_sessions
                          (id, tenant_id, lead_id, original_email, enhanced_email,
                           principles_applied, persuasion_score, created_at)
                        VALUES
                          (:id, :tenant_id, :lead_id, :original_email, :enhanced_email,
                           :principles_applied::jsonb, :persuasion_score, now())
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "tenant_id": str(tenant_id),
                        "lead_id": str(lead_id) if lead_id else None,
                        "original_email": original_email,
                        "enhanced_email": result.get("enhanced_email", original_email),
                        "principles_applied": json.dumps(result.get("principles_applied", [])),
                        "persuasion_score": result.get("persuasion_score", 0),
                    },
                )
                await session.commit()
        except Exception as exc:
            logger.warning("Failed to persist Cialdini session: %s", exc)


cialdini_engine = CialdiniEngine()
