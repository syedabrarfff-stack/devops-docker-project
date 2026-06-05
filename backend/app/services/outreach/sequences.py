"""
Compatibility outreach sequence engine.
All cold emails follow the concise Phase 2 client-acquisition format.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import Contact
from app.models.outreach import OutreachEmail, OutreachSequence

logger = logging.getLogger(__name__)


async def _get_sender(db: AsyncSession, service_category: str = "outreach") -> dict:
    """Resolve the human team member identity for a given service category."""
    try:
        from app.services.team.team_service import get_member_for_service

        member = await get_member_for_service(db, service_category)
        if member:
            return {
                "name": member.first_name,
                "full_name": member.name,
                "email": member.email,
                "signature": member.email_signature,
                "role": member.role,
                "department": member.department,
            }
    except Exception as exc:
        logger.warning("Team member lookup failed: %s", exc)
    return {
        "name": "Darren",
        "full_name": "Darren Mitchell",
        "email": "darren.mitchell@aliyarsolutions.com",
        "signature": "Darren Mitchell, Client Acquisition Specialist, Aliyar Solutions.",
        "role": "Client Acquisition Specialist",
        "department": "Client Acquisition Division",
    }


def _build_templates(sender_name: str, signature: str) -> dict:
    clean_signature = _compact_signature(signature)
    return {
        "saas_usa": {
            "steps": [
                {
                    "step": 1,
                    "delay_days": 0,
                    "subject": "Where follow-ups leak revenue",
                    "body": (
                        "Hi {name} - {company} looks exposed to manual follow-up gaps, which usually slows {industry} teams when volume rises. "
                        "For a comparable operator, our team removed 38% of manual follow-up work in 30 days and recovered about 11 hours per week. "
                        "How are you currently catching missed handoffs before they turn into lost revenue? "
                        "The demo is ready, and if you're interested, we can share it with you. "
                        f"{clean_signature}"
                    ),
                },
                {
                    "step": 2,
                    "delay_days": 3,
                    "subject": "One workflow question",
                    "body": (
                        "Hi {name} - the reason {company} stood out is that customer handoffs can quietly drain team focus even when demand is healthy. "
                        "A similar team used our workflow map to cut response gaps by 42% and make every follow-up visible in one operating view. "
                        "What would change if your team could see every pending customer action before it slipped? "
                        "Would a short demo outline help you decide whether this matters? "
                        f"{clean_signature}"
                    ),
                },
                {
                    "step": 3,
                    "delay_days": 7,
                    "subject": "Final note on handoffs",
                    "body": (
                        "Hi {name} - this is the last note because missed handoffs may not be today's priority. "
                        "For another operator, the same pattern turned into 9 recovered hours per week after the first workflow fix. "
                        "Is the bigger risk for {company} missed revenue, slower response time, or team overload? "
                        "If any of those feel current, Aliyar Solutions can send the demo path. "
                        f"{clean_signature}"
                    ),
                },
            ]
        },
        "hotel_uk": {
            "steps": [
                {
                    "step": 1,
                    "delay_days": 0,
                    "subject": "Guest handoffs worth checking",
                    "body": (
                        "Hi {name} - {company} may be losing staff time where guest requests, bookings, and follow-ups move between teams. "
                        "A comparable hospitality workflow cut response gaps by 41% and recovered 12 staff hours per week after the first operating map. "
                        "Where do guest handoffs most often slow your team down? "
                        "The demo is ready, and if you're interested, we can share it with you. "
                        f"{clean_signature}"
                    ),
                },
                {
                    "step": 2,
                    "delay_days": 4,
                    "subject": "One guest-flow question",
                    "body": (
                        "Hi {name} - guest experience often suffers when small requests are tracked across inboxes, phones, and spreadsheets. "
                        "A similar hotel team reduced missed follow-ups by 38% and improved response visibility for managers within 30 days. "
                        "What would change if every pending guest action was visible before the shift changed? "
                        "Would a short demo outline help you decide whether this matters? "
                        f"{clean_signature}"
                    ),
                },
            ]
        },
    }


def _compact_signature(signature: str) -> str:
    parts = [part.strip() for part in (signature or "").splitlines() if part.strip()]
    if not parts:
        return "Darren Mitchell, Client Acquisition Specialist, Aliyar Solutions."
    if len(parts) >= 2:
        return f"{parts[0]}, {parts[1]}, Aliyar Solutions."
    return parts[0].rstrip(".") + "."


ICP_TEMPLATES = _build_templates(
    "Darren",
    "Darren Mitchell\nClient Acquisition Specialist\nAliyar Solutions\ndarren.mitchell@aliyarsolutions.com",
)


async def create_sequence(db: AsyncSession, data: dict) -> OutreachSequence:
    seq = OutreachSequence(**{k: v for k, v in data.items() if hasattr(OutreachSequence, k)})
    if not seq.steps:
        service_cat = data.get("service_category", "outreach")
        sender = await _get_sender(db, service_cat)
        templates = _build_templates(sender["name"], sender["signature"])
        template_key = f"{data.get('target_industry', 'saas')}_{data.get('target_country', 'usa')}".lower()
        template = templates.get(template_key) or list(templates.values())[0]
        seq.steps = template["steps"]
        seq.total_steps = len(seq.steps)
        if hasattr(seq, "sender_name"):
            seq.sender_name = sender["full_name"]
        if hasattr(seq, "sender_email"):
            seq.sender_email = sender["email"]
    db.add(seq)
    await db.flush()
    await db.refresh(seq)
    return seq


async def generate_sequence_with_ai(
    db: AsyncSession,
    target_industry: str,
    target_country: str,
    service_offered: str,
    sequence_id: int,
) -> list[dict]:
    """Use the AI router to generate a custom concise 3-step sequence."""
    from app.services.ai.base_provider import Message, TaskType
    from app.services.ai.router import ai_router
    from app.services.memory.human_intelligence import human_intelligence_context

    prompt = (
        "Create a 3-step cold email outreach sequence for Aliyar Solutions.\n\n"
        f"Target: {target_industry} companies in {target_country}\n"
        f"Service: {service_offered}\n\n"
        f"Human intelligence rules:\n{human_intelligence_context(max_chars=1200)}\n\n"
        "Rules:\n"
        "- Maximum 5 sentences total per email\n"
        "- Sentence 1: one specific pain point relevant to their industry\n"
        "- Sentence 2: one quantified result for a comparable company\n"
        "- Sentence 3: one question that makes them think about their own situation\n"
        "- Sentence 4: soft relevance CTA that says the demo is ready and can be shared if they're interested\n"
        "- Sentence 5: sender full name and title from the team persona\n"
        "- Subject line maximum 7 words, no AI, no automation, no solution\n"
        "- Zero attachments, no pricing, no first-person singular language\n"
        "- Use {name}, {company}, {industry} as placeholders\n\n"
        'Return ONLY valid JSON array: [{"step":1,"delay_days":0,"subject":"...","body":"..."},...]'
    )
    resp, _ = await ai_router.chat(
        [Message(role="user", content=prompt)],
        task_type=TaskType.FAST,
        force_provider="google",
    )
    try:
        text = resp.content.strip()
        if "```" in text:
            text = text.split("```")[1].lstrip("json").strip()
        steps = json.loads(text)
        await db.execute(
            update(OutreachSequence)
            .where(OutreachSequence.id == sequence_id)
            .values(steps=steps, total_steps=len(steps))
        )
        await db.flush()
        return steps
    except Exception as exc:
        logger.warning("AI sequence parse failed: %s", exc)
        return []


async def enroll_contacts(
    db: AsyncSession,
    sequence_id: int,
    contact_ids: list[int],
) -> list[OutreachEmail]:
    """Enroll contacts into a sequence by creating scheduled OutreachEmail records."""
    from datetime import datetime, timedelta, timezone

    seq_row = (await db.execute(select(OutreachSequence).where(OutreachSequence.id == sequence_id))).scalar_one_or_none()
    if not seq_row:
        return []

    contacts = (await db.execute(select(Contact).where(Contact.id.in_(contact_ids)))).scalars().all()
    created = []
    now = datetime.now(timezone.utc)

    for contact in contacts:
        for step in seq_row.steps or []:
            delay = step.get("delay_days", 0)
            subject = (step.get("subject") or "").replace("{name}", contact.name or "")
            company_name = ""
            body = (step.get("body") or "").replace("{name}", contact.name or "").replace("{company}", company_name)
            email = OutreachEmail(
                sequence_id=sequence_id,
                contact_id=contact.id,
                to_email=contact.email or "",
                to_name=contact.name or "",
                subject=subject,
                body=body,
                step_number=step.get("step", 1),
                status="scheduled",
                scheduled_at=now + timedelta(days=delay),
            )
            db.add(email)
            created.append(email)

    await db.flush()
    return created


async def get_sequence_stats(db: AsyncSession) -> list[dict]:
    rows = (
        await db.execute(
            select(OutreachSequence).order_by(desc(OutreachSequence.created_at)).limit(20)
        )
    ).scalars().all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "status": s.status,
            "emails_sent": s.emails_sent,
            "replies_received": s.replies_received,
            "open_rate": round(s.emails_opened / s.emails_sent * 100, 1) if s.emails_sent else 0,
        }
        for s in rows
    ]
