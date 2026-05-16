"""
Outreach sequence engine — Gemini-generated multi-step email campaigns.
All emails are signed by the appropriate Aliyar Solutions team member identity.
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.outreach import OutreachSequence, OutreachEmail
from app.models.crm import Contact
from app.services.communication.client_language import sanitize_subject_body

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
    except Exception as e:
        logger.warning(f"Team member lookup failed: {e}")
    # Safe fallback
    return {
        "name": "Darren",
        "full_name": "Darren Mitchell",
        "email": "darren.mitchell@aliyarsolutions.com",
        "signature": "Darren Mitchell\nClient Acquisition Specialist\nAliyar Solutions",
        "role": "Client Acquisition Specialist",
        "department": "Client Acquisition Division",
    }

def _build_templates(sender_name: str, signature: str) -> dict:
    return {
        "saas_usa": {
            "steps": [
                {"step": 1, "delay_days": 0,
                 "subject": "Quick question about {company}'s workflow",
                 "body": f"Hi {{name}},\n\nI came across {{company}} and noticed you're in the {{industry}} space.\n\nWe help growing companies reduce repetitive work, improve response speed, and create clearer operational visibility.\n\nWould a 15-minute call to see whether this is relevant make sense?\n\n{signature}"},
                {"step": 2, "delay_days": 3,
                 "subject": "Re: {company} workflow",
                 "body": f"Hi {{name}},\n\nJust following up on my last message. We recently helped a similar team reduce operational overhead and improve execution visibility.\n\nHappy to share a quick case study if useful.\n\n{signature}"},
                {"step": 3, "delay_days": 7,
                 "subject": "Last touch - workflow improvements for {company}",
                 "body": f"Hi {{name}},\n\nI'll keep this brief. If improving operational workflows is not a priority right now, no worries - I will not follow up again.\n\nIf you would like to see how similar companies reduce manual work and improve coordination, reply and I will send over details.\n\n{signature}"},
            ]
        },
        "hotel_uk": {
            "steps": [
                {"step": 1, "delay_days": 0,
                 "subject": "Reducing costs at {company} — worth a look?",
                 "body": f"Hi {{name}},\n\nHotels working with our team are cutting operational costs by 40% while improving guest experience.\n\nWe handle: automated check-in, demand forecasting, staff scheduling, and guest communication.\n\nIs this worth a quick chat?\n\n{signature}"},
                {"step": 2, "delay_days": 4,
                 "subject": "Case study: Hotel saved £180k",
                 "body": f"Hi {{name}},\n\nFollowing up — I wanted to share how a UK hotel similar to {{company}} saved £180k annually.\n\nKey results: 38% cost reduction, 4.9★ guest rating, 92% staff satisfaction.\n\nWant the full case study?\n\n{signature}"},
            ]
        },
    }


# Fallback static templates (used before team seed runs)
ICP_TEMPLATES = _build_templates(
    "Darren",
    "Darren Mitchell\nClient Acquisition Specialist\nAliyar Solutions\ndarren.mitchell@aliyarsolutions.com"
)


async def create_sequence(db: AsyncSession, data: dict) -> OutreachSequence:
    seq = OutreachSequence(**{k: v for k, v in data.items() if hasattr(OutreachSequence, k)})
    if not seq.steps:
        service_cat = data.get("service_category", "outreach")
        sender = await _get_sender(db, service_cat)
        templates = _build_templates(sender["name"], sender["signature"])
        template_key = f"{data.get('target_industry','saas')}_{data.get('target_country','usa')}".lower()
        template = templates.get(template_key) or list(templates.values())[0]
        seq.steps = template["steps"]
        seq.total_steps = len(seq.steps)
        # Store sender identity in sequence metadata if field exists
        if hasattr(seq, "sender_name"):
            seq.sender_name = sender["full_name"]
        if hasattr(seq, "sender_email"):
            seq.sender_email = sender["email"]
    if seq.steps:
        for step in seq.steps:
            step["subject"], step["body"] = sanitize_subject_body(step.get("subject", ""), step.get("body", ""))
    db.add(seq)
    await db.flush()
    await db.refresh(seq)
    return seq


async def generate_sequence_with_ai(db: AsyncSession,
                                    target_industry: str,
                                    target_country: str,
                                    service_offered: str,
                                    sequence_id: int) -> list[dict]:
    """Use Gemini to generate a custom 3-step sequence."""
    from app.services.ai.router import ai_router
    from app.services.ai.base_provider import Message, TaskType
    import json

    prompt = (
        f"Create a 3-step consulting outreach sequence for Aliyar Solutions.\n\n"
        f"Target: {target_industry} companies in {target_country}\n"
        f"Service: {service_offered}\n\n"
        f"Rules:\n"
        f"- Professional but human, not corporate-speak\n"
        f"- Never mention JARVIS, AI tools, agents, providers, prompts, routing, or internal infrastructure\n"
        f"- Position Aliyar Solutions as an operations consulting and workflow modernization team\n"
        f"- Step 1: day 0, introduce value proposition\n"
        f"- Step 2: day 3, social proof / case study\n"
        f"- Step 3: day 7, soft close / break-up\n"
        f"- Each email under 120 words\n"
        f"- Use {{name}}, {{company}}, {{industry}} as placeholders\n\n"
        f"Return ONLY valid JSON array:\n"
        f'[{{"step":1,"delay_days":0,"subject":"...","body":"..."}},...]\n'
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
        for step in steps:
            step["subject"], step["body"] = sanitize_subject_body(step.get("subject", ""), step.get("body", ""))
        from sqlalchemy import update
        await db.execute(update(OutreachSequence).where(OutreachSequence.id == sequence_id).values(
            steps=steps, total_steps=len(steps)
        ))
        await db.flush()
        return steps
    except Exception as e:
        logger.warning(f"AI sequence parse failed: {e}")
        return []


async def enroll_contacts(db: AsyncSession, sequence_id: int,
                          contact_ids: list[int]) -> list[OutreachEmail]:
    """Enroll contacts into a sequence by creating scheduled OutreachEmail records."""
    from datetime import datetime, timedelta, timezone

    seq_row = (await db.execute(select(OutreachSequence).where(OutreachSequence.id == sequence_id))).scalar_one_or_none()
    if not seq_row:
        return []

    contacts = (await db.execute(select(Contact).where(Contact.id.in_(contact_ids)))).scalars().all()
    created = []
    now = datetime.now(timezone.utc)

    for contact in contacts:
        for step in (seq_row.steps or []):
            delay = step.get("delay_days", 0)
            subject = step.get("subject", "").replace("{name}", contact.name or "")
            body    = step.get("body", "")
            subject, body = sanitize_subject_body(subject, body)
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
    rows = (await db.execute(select(OutreachSequence).order_by(desc(OutreachSequence.created_at)).limit(20))).scalars().all()
    return [{
        "id": s.id, "name": s.name, "status": s.status,
        "emails_sent": s.emails_sent, "replies_received": s.replies_received,
        "open_rate": round(s.emails_opened / s.emails_sent * 100, 1) if s.emails_sent else 0,
    } for s in rows]
