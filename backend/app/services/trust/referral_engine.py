import logging
import asyncio
from uuid import UUID
from app.core.database import AsyncSessionLocal
from app.models.trust_engine import ReferralRequest

logger = logging.getLogger(__name__)

REFERRAL_PROMPTS = {
    "testimonial": """You are writing on behalf of Aliyar Solutions to a satisfied client.
Write a brief, warm testimonial request email.
CLIENT: {client_name} at {company}
SERVICE DELIVERED: {service_type}
Tone: Grateful, specific, easy to act on. Under 120 words.
Ask them to reply with 2–3 sentences about the outcome they experienced.""",

    "referral": """Write a referral request email from Aliyar Solutions to a satisfied client.
CLIENT: {client_name} at {company}
SERVICE DELIVERED: {service_type}
Tone: Confident, non-pushy, makes it easy. Under 120 words.
Ask if they know any businesses facing similar challenges who might benefit from an introduction.""",

    "case_study": """Write a brief case study outline for Aliyar Solutions based on this client engagement.
CLIENT: {company}
SERVICE: {service_type}
MRR: {mrr}
Structure: Challenge → Solution → Results (3 bullet points with specific metrics where possible).
Tone: Professional, outcome-focused. Under 200 words.""",
}


class ReferralEngine:

    async def _generate_one(
        self,
        request_type: str,
        client_name: str,
        company: str,
        service_type: str,
        mrr: float,
    ) -> str:
        from app.services.ai.router import ai_router
        from app.services.ai.base_provider import TaskType, Message

        template = REFERRAL_PROMPTS[request_type]
        prompt = template.format(
            client_name=client_name,
            company=company,
            service_type=service_type,
            mrr=f"${mrr:,.0f}/month",
        )
        messages = [Message(role="user", content=prompt)]

        try:
            response, _ = await asyncio.wait_for(
                ai_router.chat(
                    messages,
                    task_type=TaskType.STRATEGY,
                    max_tokens=400,
                ),
                timeout=30.0,
            )
            if response.error:
                raise ValueError(response.error)
            return (response.content or "").strip()
        except Exception as e:
            logger.warning("ReferralEngine: AI failed for %s: %s", request_type, e)
            return f"[{request_type.title()} content for {client_name} at {company} — AI generation unavailable]"

    async def generate(
        self,
        client_id: UUID,
        client_name: str,
        company: str,
        service_type: str,
        mrr: float,
        tenant_id=None,
    ) -> dict:
        types = ["testimonial", "referral", "case_study"]
        contents = await asyncio.gather(
            *[self._generate_one(t, client_name, company, service_type, mrr) for t in types]
        )

        result = {}
        async with AsyncSessionLocal() as db:
            for request_type, content in zip(types, contents):
                record = ReferralRequest(
                    client_id=client_id,
                    request_type=request_type,
                    content=content,
                    status="draft",
                )
                db.add(record)
                await db.flush()
                result[request_type] = {
                    "id": record.id,
                    "client_id": str(client_id),
                    "request_type": request_type,
                    "content": content,
                    "status": record.status,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                }
            await db.commit()

        return result


referral_engine = ReferralEngine()
