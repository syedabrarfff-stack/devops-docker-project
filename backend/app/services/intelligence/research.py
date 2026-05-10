"""
JARVIS Autonomous Research Division — generates structured intelligence reports
on market opportunities, niches, technologies, and competitive landscape.
"""
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.intelligence import ResearchReport
from app.services.ai.base_provider import Message

logger = logging.getLogger(__name__)

RESEARCH_PROMPT = """You are JARVIS — the intelligence division of Aliyar Solutions, an AI consulting and DevOps agency.

Generate a structured research report on the following topic for Captain Abrar.

TOPIC: {topic}
CATEGORY: {category}

Return ONLY a valid JSON object — no markdown, no explanation.

Required fields:
- title (concise, professional, max 120 chars)
- category (one of: market, technology, competitor, niche, infrastructure)
- summary (2-3 sentences executive summary)
- findings (array of 4-6 specific findings, each a full sentence with data or evidence)
- opportunities (array of 3-5 actionable opportunities for Aliyar Solutions)
- risks (array of 2-4 risks or watchouts)
- action_items (array of 3-5 concrete next steps, each starting with a verb)
- confidence_level (one of: high, medium, low — based on how certain the analysis is)

Focus on: profitability, scalability, market demand, competitive advantage, and Aliyar Solutions' positioning.
Return ONLY the JSON object."""

DEFAULT_TOPICS = [
    ("AI automation demand in hotel and hospitality industry", "niche"),
    ("Cloud modernization opportunities in South Asia (India, Pakistan, UAE)", "market"),
    ("Competing AI consulting agencies on Upwork — pricing and positioning", "competitor"),
    ("Emerging DevOps tools displacing Jenkins in 2025-2026", "technology"),
    ("SaaS companies with high automation ROI (ideal ICP for Aliyar)", "niche"),
]


async def generate_report(
    db: AsyncSession,
    topic: str,
    category: str = "market",
) -> dict | None:
    """Generate and persist a single research report."""
    from app.services.ai.router import ai_router
    from app.services.ai.base_provider import TaskType

    prompt = RESEARCH_PROMPT.format(topic=topic, category=category)
    messages = [Message(role="user", content=prompt)]

    try:
        response, _ = await ai_router.chat(
            messages,
            task_type=TaskType.RESEARCH,
            system_prompt="You are a strategic business analyst. Return only valid JSON objects.",
            max_tokens=2500,
        )

        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("Expected JSON object")

        cat = str(data.get("category", category)).strip()
        if cat not in ("market", "technology", "competitor", "niche", "infrastructure"):
            cat = category

        conf = str(data.get("confidence_level", "medium")).strip()
        if conf not in ("high", "medium", "low"):
            conf = "medium"

        report = ResearchReport(
            title=str(data.get("title", topic))[:500],
            category=cat,
            summary=data.get("summary", ""),
            findings=data.get("findings", []),
            opportunities=data.get("opportunities", []),
            risks=data.get("risks", []),
            action_items=data.get("action_items", []),
            confidence_level=conf,
        )
        db.add(report)
        await db.flush()

        return _serialize(report)

    except json.JSONDecodeError as e:
        logger.warning(f"Research report JSON parse error: {e}")
        return None
    except Exception as e:
        logger.warning(f"Research report generation failed: {e}")
        return None


async def generate_default_reports(db: AsyncSession) -> int:
    """Generate one default report from the rotating topic list."""
    from app.models.intelligence import ResearchReport as RR
    existing = (await db.execute(select(RR).order_by(RR.created_at.desc()).limit(1))).scalar_one_or_none()
    idx = 0
    if existing:
        # Rotate through default topics
        for i, (t, _) in enumerate(DEFAULT_TOPICS):
            if t in (existing.title or ""):
                idx = (i + 1) % len(DEFAULT_TOPICS)
                break

    topic, category = DEFAULT_TOPICS[idx]
    result = await generate_report(db, topic, category)
    return 1 if result else 0


async def get_reports(db: AsyncSession, limit: int = 20) -> list[dict]:
    result = await db.execute(
        select(ResearchReport).order_by(ResearchReport.created_at.desc()).limit(limit)
    )
    return [_serialize(r) for r in result.scalars().all()]


def _serialize(r: ResearchReport) -> dict:
    return {
        "id": r.id,
        "title": r.title,
        "category": r.category,
        "summary": r.summary,
        "findings": r.findings or [],
        "opportunities": r.opportunities or [],
        "risks": r.risks or [],
        "action_items": r.action_items or [],
        "confidence_level": r.confidence_level,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
