"""
JARVIS Lead Generation Engine.
Gemini scores, qualifies, and generates outreach strategy for leads.
Aliyar Solutions ICP: SaaS, hotels, restaurants, clinics, recruiters.
Target: USA, Canada, UK, Europe, Australia, NZ.
"""
import asyncio
import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from app.models.lead import Lead, LeadStatus

logger = logging.getLogger(__name__)

ALIYAR_ICP = {
    "industries":  ["saas", "software", "hotel", "hospitality", "restaurant", "clinic",
                    "healthcare", "recruitment", "staffing", "e-commerce", "fintech"],
    "countries":   ["usa", "canada", "uk", "australia", "new zealand", "germany",
                    "netherlands", "ireland", "singapore"],
    "pain_points": ["manual processes", "scaling", "cost reduction", "automation",
                    "lead generation", "cloud migration", "devops", "ai integration"],
    "min_score":   65,
}

SCORE_PROMPT = """You are JARVIS, AI analyst for Aliyar Solutions.
Score this lead 0-100 for fit with Aliyar Solutions services
(AI automation, DevOps, cloud consulting, lead generation).

ICP: SaaS/software/hotels/restaurants/clinics/recruitment agencies.
Target markets: USA, Canada, UK, Europe, Australia, NZ.

Lead data:
{lead_data}

Respond with ONLY a JSON object:
{{
  "score": <int 0-100>,
  "tier": "<A|B|C|D>",
  "reasoning": "<2 sentences>",
  "pain_points": ["<point1>", "<point2>"],
  "recommended_service": "<service>",
  "outreach_angle": "<1 sentence pitch angle>"
}}"""


async def score_lead_with_ai(lead: Lead) -> dict:
    """Use Gemini to score and qualify a lead."""
    from app.services.ai.router import ai_router
    from app.services.ai.base_provider import Message, TaskType
    import json

    lead_data = (
        f"Company: {lead.company_name or lead.company}\n"
        f"Contact: {lead.contact_name}\n"
        f"Industry: {lead.industry}\n"
        f"Country: {lead.country}\n"
        f"Email: {lead.email}\n"
        f"Website: {lead.website or 'unknown'}\n"
        f"Pain points: {', '.join(lead.pain_points or [])}\n"
        f"Opportunity: {lead.opportunity_type or 'unknown'}"
    )

    try:
        resp, _ = await asyncio.wait_for(
            ai_router.chat(
                [Message(role="user", content=SCORE_PROMPT.format(lead_data=lead_data))],
                task_type=TaskType.FAST,
                force_provider="google",
            ),
            timeout=60.0,
        )
        if resp.error:
            raise ValueError(resp.error)
        text = (resp.content or "").strip()
        if "```" in text:
            text = text.split("```")[1].lstrip("json").strip()
        return json.loads(text)
    except Exception:
        # Fallback scoring (covers AI errors, timeouts, and JSON parse failures)
        score = 50
        if lead.country and any(c in lead.country.lower() for c in ALIYAR_ICP["countries"]):
            score += 15
        if lead.industry and any(i in lead.industry.lower() for i in ALIYAR_ICP["industries"]):
            score += 20
        return {"score": score, "tier": "B", "reasoning": "Auto-scored.", "pain_points": [],
                "recommended_service": "AI automation", "outreach_angle": "Automate your operations"}


async def qualify_and_score(db: AsyncSession, lead_id: UUID, tenant_id: Optional[UUID] = None) -> Optional[Lead]:
    """Score a lead with Gemini and update the database record."""
    _tid = tenant_id
    if _tid is None:
        from app.core.config import settings as _cfg
        if _cfg.JARVIS_DEFAULT_TENANT_ID:
            try:
                _tid = UUID(str(_cfg.JARVIS_DEFAULT_TENANT_ID))
            except (ValueError, AttributeError):
                pass
    q = select(Lead).where(Lead.id == lead_id)
    if _tid is not None:
        q = q.where(Lead.tenant_id == _tid)
    lead = (await db.execute(q)).scalar_one_or_none()
    if not lead:
        return None

    result = await score_lead_with_ai(lead)
    lead.score        = result.get("score", 50)
    lead.tier         = result.get("tier", "B")
    lead.ai_analysis  = result.get("reasoning", "")
    lead.pain_points  = result.get("pain_points", lead.pain_points or [])
    lead.opportunity_type = result.get("recommended_service", lead.opportunity_type)

    lead.signal_breakdown = {
        "score": int(lead.score or 0),
        "tier": lead.tier,
        "recommended_service": result.get("recommended_service"),
        "outreach_angle": result.get("outreach_angle"),
    }
    if lead.score >= ALIYAR_ICP["min_score"] and lead.status == LeadStatus.NEW:
        lead.status = LeadStatus.NURTURE
        lead.outreach_eligible = True
        lead.review_queue = False
        lead.disqualification_reason = None
    else:
        lead.outreach_eligible = False
        lead.review_queue = lead.score >= 45
        lead.disqualification_reason = "Score below 65 outreach threshold"
    await db.flush()

    # Telegram notification for A-tier leads
    if result.get("tier") == "A":
        try:
            from app.services.notifications.telegram import notify_telegram
            await notify_telegram(
                f"*A-Tier Lead Identified*\n\n"
                f"*{lead.company_name or lead.company}* - {lead.industry} ({lead.country})\n"
                f"Score: {lead.score}/100\n"
                f"Service: {result.get('recommended_service')}\n"
                f"Angle: {result.get('outreach_angle')}"
            )
        except Exception as exc:
            logger.warning("A-tier lead Telegram notification failed for lead %s: %s", lead.id, exc)

    return lead


async def bulk_score(db: AsyncSession, limit: int = 20, tenant_id: Optional[UUID] = None) -> int:
    """Score all unscored leads. Returns count processed."""
    from app.core.config import settings as _cfg
    _tid = tenant_id
    if _tid is None and _cfg.JARVIS_DEFAULT_TENANT_ID:
        try:
            _tid = UUID(str(_cfg.JARVIS_DEFAULT_TENANT_ID))
        except (ValueError, AttributeError):
            pass
    q = select(Lead).where(Lead.score == 0)
    if _tid is not None:
        q = q.where(Lead.tenant_id == _tid)
    rows = (await db.execute(q.limit(limit))).scalars().all()
    count = 0
    for lead in rows:
        try:
            await qualify_and_score(db, lead.id)
            count += 1
        except Exception as e:
            logger.warning(f"Failed to score lead {lead.id}: {e}")
    return count


async def create_lead(db: AsyncSession, data: dict) -> Lead:
    lead = Lead(**{k: v for k, v in data.items() if hasattr(Lead, k)})
    db.add(lead)
    await db.flush()
    await db.refresh(lead)
    return lead


async def list_leads(db: AsyncSession, status: Optional[str] = None,
                     min_score: int = 0, limit: int = 50,
                     tenant_id: Optional[UUID] = None) -> list[Lead]:
    from app.core.config import settings as _cfg
    _tid = tenant_id
    if _tid is None and _cfg.JARVIS_DEFAULT_TENANT_ID:
        try:
            _tid = UUID(str(_cfg.JARVIS_DEFAULT_TENANT_ID))
        except (ValueError, AttributeError):
            pass
    q = select(Lead).order_by(desc(Lead.score)).limit(limit)
    if _tid is not None:
        q = q.where(Lead.tenant_id == _tid)
    if status:
        q = q.where(Lead.status == status)
    if min_score:
        q = q.where(Lead.score >= min_score)
    return list((await db.execute(q)).scalars().all())


async def lead_stats(db: AsyncSession, tenant_id: Optional[UUID] = None) -> dict:
    from app.core.config import settings as _cfg
    _tid = tenant_id
    if _tid is None and _cfg.JARVIS_DEFAULT_TENANT_ID:
        try:
            _tid = UUID(str(_cfg.JARVIS_DEFAULT_TENANT_ID))
        except (ValueError, AttributeError):
            pass
    _t = (Lead.tenant_id == _tid,) if _tid is not None else ()
    total              = await db.scalar(select(func.count()).select_from(Lead).where(*_t)) or 0
    qualified          = await db.scalar(
        select(func.count()).select_from(Lead).where(*_t, Lead.score >= ALIYAR_ICP["min_score"])
    ) or 0
    high_score         = await db.scalar(
        select(func.count()).select_from(Lead).where(*_t, Lead.score >= 70)
    ) or 0
    outreach_eligible  = await db.scalar(
        select(func.count()).select_from(Lead).where(*_t, Lead.outreach_eligible == True)
    ) or 0
    contacted          = await db.scalar(select(func.count()).select_from(Lead).where(*_t, Lead.outreach_sent == True)) or 0
    unscored           = await db.scalar(select(func.count()).select_from(Lead).where(*_t, Lead.score == 0)) or 0
    avg_score          = await db.scalar(select(func.avg(Lead.score)).where(*_t, Lead.score > 0)) or 0
    by_status: dict[str, int] = {}
    for status_val in ["NEW", "CONTACTED", "REPLIED", "DEMO", "PROPOSAL", "WON", "LOST"]:
        cnt = await db.scalar(select(func.count()).select_from(Lead).where(*_t, Lead.status == status_val)) or 0
        if cnt:
            by_status[status_val.lower()] = cnt
    return {
        "total": total,
        "qualified": qualified,
        "high_score": high_score,
        "outreach_eligible": outreach_eligible,
        "contacted": contacted,
        "unscored": unscored,
        "avg_score": round(float(avg_score), 1),
        "conversion_rate": round(qualified / total * 100, 1) if total else 0,
        "by_status": by_status,
        "icp_min_score": ALIYAR_ICP["min_score"],
    }
