import json
import logging
import asyncio
from app.core.database import AsyncSessionLocal
from app.models.trust_engine import ExecutiveOpportunityBrief

logger = logging.getLogger(__name__)

BRIEF_PROMPT = """You are the Intelligence Division of Aliyar Solutions, a premium AI automation and cloud consulting firm.

Analyse the following prospect and generate an Executive Opportunity Brief.

COMPANY: {company_name}
INDUSTRY: {industry}
PAIN POINTS: {pain_points}

Respond with a JSON object (no markdown, pure JSON) with these exact keys:
{{
  "bottlenecks": ["list of 3-5 specific operational bottlenecks this company likely faces"],
  "opportunities": ["list of 3-5 specific revenue or efficiency opportunities"],
  "quick_wins": ["list of 3 specific high-ROI actions achievable in 30 days"],
  "risk_factors": ["list of 2-3 risks if they delay acting"],
  "estimated_roi": "A specific estimated ROI range e.g. '$45,000–$80,000 annually' or '3–5x operational efficiency'",
  "narrative": "A 3-paragraph executive brief written directly to the company. Open by naming their specific challenge (not generic). Present Aliyar Solutions as a firm that has solved this exact problem. Close with a specific recommended next step. Tone: premium, confident, business-focused. Never use 'I' — use 'our team'. Maximum 200 words."
}}"""


class BriefGenerator:

    async def generate(
        self,
        company_name: str,
        industry: str,
        pain_points: list[str],
        lead_id=None,
        tenant_id=None,
    ) -> dict:
        from app.services.ai.router import ai_router
        from app.services.ai.base_provider import TaskType, Message

        pain_points_str = ", ".join(pain_points) if pain_points else "Not specified"
        prompt = BRIEF_PROMPT.format(
            company_name=company_name,
            industry=industry or "Not specified",
            pain_points=pain_points_str,
        )
        messages = [Message(role="user", content=prompt)]

        parsed = {}
        brief_status = "generated"
        try:
            response, _ = await asyncio.wait_for(
                ai_router.chat(
                    messages,
                    task_type=TaskType.STRATEGY,
                    max_tokens=1500,
                ),
                timeout=30.0,
            )
            if response.error:
                raise ValueError(f"AI provider error: {response.error}")
            raw = response.content.strip()
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                logger.error(
                    "BriefGenerator: JSON parse failed for %s (response prefix: %.100s): %s",
                    company_name, raw, exc,
                )
                brief_status = "failed"
        except asyncio.TimeoutError:
            logger.error("BriefGenerator: AI call timed out for %s", company_name)
            brief_status = "failed"
        except Exception as exc:
            logger.error("BriefGenerator: AI call failed for %s: %s", company_name, exc)
            brief_status = "failed"

        trust_score = 0.0
        if lead_id:
            try:
                from app.services.trust.scoring import compute_scores
                scores = await compute_scores(lead_id)
                trust_score = scores.get("trust_score", 0.0)
            except Exception as exc:
                logger.warning("BriefGenerator: trust score failed for lead %s: %s", lead_id, exc)

        async with AsyncSessionLocal() as db:
            brief = ExecutiveOpportunityBrief(
                lead_id=lead_id,
                company_name=company_name,
                industry=industry or None,
                pain_points=pain_points,
                bottlenecks=parsed.get("bottlenecks", []),
                opportunities=parsed.get("opportunities", []),
                quick_wins=parsed.get("quick_wins", []),
                risk_factors=parsed.get("risk_factors", []),
                estimated_roi=parsed.get("estimated_roi"),
                narrative=parsed.get("narrative"),
                trust_score_at_creation=trust_score,
                status=brief_status,
            )
            db.add(brief)
            await db.commit()
            await db.refresh(brief)
            return self._serialize(brief)

    def _serialize(self, b: ExecutiveOpportunityBrief) -> dict:
        return {
            "id": b.id,
            "lead_id": str(b.lead_id) if b.lead_id else None,
            "company_name": b.company_name,
            "industry": b.industry,
            "pain_points": b.pain_points or [],
            "bottlenecks": b.bottlenecks or [],
            "opportunities": b.opportunities or [],
            "quick_wins": b.quick_wins or [],
            "risk_factors": b.risk_factors or [],
            "estimated_roi": b.estimated_roi,
            "narrative": b.narrative,
            "trust_score_at_creation": b.trust_score_at_creation,
            "status": b.status,
            "delivered_at": b.delivered_at.isoformat() if b.delivered_at else None,
            "viewed_at": b.viewed_at.isoformat() if b.viewed_at else None,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }


brief_generator = BriefGenerator()
