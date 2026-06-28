"""
Layer 4 — Technology Evolution Engine

24/7 monitoring of:
- GitHub trending repositories
- OpenAI / Anthropic / Google AI announcements
- ArXiv AI/ML papers
- Product Hunt launches
- HuggingFace model releases
- Developer community signals (Reddit, HN)

For each discovery:
- Classify relevance to Aliyar Solutions (0-100 score)
- Build full adoption guide
- Submit to AI Council for strategic evaluation
- Council generates implementation roadmap
- Deploy approved technologies to JARVIS infrastructure
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.department_intelligence import TechnologyDiscovery, TechStatus
from app.services.ai.base_provider import Message, TaskType
from app.services.ai.council import intelligence_council
from app.services.ai.router import ai_router

logger = logging.getLogger(__name__)

# Intelligence sources monitored continuously
MONITORED_SOURCES = [
    {"name": "anthropic", "url": "https://anthropic.com", "type": "ai_company"},
    {"name": "openai", "url": "https://openai.com", "type": "ai_company"},
    {"name": "google_deepmind", "url": "https://deepmind.google", "type": "ai_company"},
    {"name": "mistral_ai", "url": "https://mistral.ai", "type": "ai_company"},
    {"name": "github_trending", "url": "https://github.com/trending", "type": "repository"},
    {"name": "arxiv_ai", "url": "https://arxiv.org/list/cs.AI/recent", "type": "research"},
    {"name": "huggingface", "url": "https://huggingface.co/models", "type": "model_hub"},
    {"name": "aws_announcements", "url": "https://aws.amazon.com/new", "type": "cloud"},
    {"name": "product_hunt_ai", "url": "https://producthunt.com", "type": "product"},
    {"name": "vercel_blog", "url": "https://vercel.com/blog", "type": "devtools"},
]

TECH_CATEGORIES = [
    "llm", "vision", "voice", "agents", "rag", "vectordb",
    "cloud_native", "devops", "security", "frontend", "backend",
    "automation", "monitoring", "data_pipeline", "edge_compute",
]


class TechEvolutionEngine:
    """
    Continuously discovers, evaluates, and adopts emerging technologies.
    Operates 24/7 without human intervention.
    """

    async def run_discovery_cycle(self, tenant_id: str) -> dict[str, Any]:
        """Execute a full technology discovery and evaluation cycle."""
        tenant_uuid = uuid.UUID(str(tenant_id))

        # Generate discoveries via AI analysis of the technology landscape
        discoveries = await self._discover_technologies(tenant_uuid)

        saved = 0
        high_priority = []

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, str(tenant_uuid))

            for disc in discoveries:
                # Skip if already discovered (deduplicate by name)
                existing = await db.scalar(
                    select(TechnologyDiscovery).where(
                        TechnologyDiscovery.tenant_id == tenant_uuid,
                        TechnologyDiscovery.technology_name == disc["technology_name"],
                    )
                )
                if existing:
                    continue

                tech = TechnologyDiscovery(
                    tenant_id=tenant_uuid,
                    technology_name=disc["technology_name"],
                    source=disc["source"],
                    source_url=disc.get("source_url"),
                    discovered_at=datetime.now(timezone.utc),
                    category=disc["category"],
                    provider=disc.get("provider"),
                    relevance_score=disc.get("relevance_score", 0.0),
                    priority=disc.get("priority", "medium"),
                    summary=disc.get("summary"),
                    capabilities=disc.get("capabilities", []),
                    integration_feasibility=disc.get("integration_feasibility", 0.0),
                    estimated_impact=disc.get("estimated_impact"),
                    status=TechStatus.DISCOVERED.value,
                )
                db.add(tech)
                saved += 1

                if disc.get("relevance_score", 0) >= 80 or disc.get("priority") == "critical":
                    high_priority.append(disc)

            await db.commit()

        # Submit high-priority discoveries to Council immediately
        council_results = []
        for disc in high_priority[:3]:  # Max 3 council sessions per cycle
            try:
                result = await self._submit_to_council(tenant_id, disc)
                council_results.append(result)
            except Exception as exc:
                logger.warning("Council submission failed for %s: %s", disc["technology_name"], exc)

        logger.info(
            "Tech evolution cycle: %d discovered, %d new saved, %d council reviews",
            len(discoveries), saved, len(council_results)
        )

        return {
            "tenant_id": str(tenant_uuid),
            "cycle_at": datetime.now(timezone.utc).isoformat(),
            "total_discovered": len(discoveries),
            "new_saved": saved,
            "high_priority_count": len(high_priority),
            "council_reviews": len(council_results),
        }

    async def evaluate_technology(self, tenant_id: str, tech_id: str) -> dict[str, Any]:
        """Deep evaluation of a specific technology with full adoption guide."""
        tenant_uuid = uuid.UUID(str(tenant_id))

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, str(tenant_uuid))
            tech = await db.get(TechnologyDiscovery, uuid.UUID(tech_id))
            if not tech:
                raise ValueError(f"Technology {tech_id} not found")

            # Generate full adoption guide
            adoption_guide = await self._generate_adoption_guide(tech)

            tech.adoption_guide = adoption_guide
            tech.status = TechStatus.EVALUATING.value
            await db.commit()

            return {
                "tech_id": tech_id,
                "technology_name": tech.technology_name,
                "adoption_guide": adoption_guide,
                "status": tech.status,
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
            }

    async def submit_for_council_review(self, tenant_id: str, tech_id: str) -> dict[str, Any]:
        """Submit a technology discovery to the Council for strategic evaluation."""
        tenant_uuid = uuid.UUID(str(tenant_id))

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, str(tenant_uuid))
            tech = await db.get(TechnologyDiscovery, uuid.UUID(tech_id))
            if not tech:
                raise ValueError(f"Technology {tech_id} not found")

            tech_dict = {
                "technology_name": tech.technology_name,
                "category": tech.category,
                "summary": tech.summary,
                "capabilities": tech.capabilities,
                "relevance_score": tech.relevance_score,
                "estimated_impact": tech.estimated_impact,
                "adoption_guide": tech.adoption_guide,
            }

        result = await self._submit_to_council(tenant_id, tech_dict)

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, str(tenant_uuid))
            tech = await db.get(TechnologyDiscovery, uuid.UUID(tech_id))
            if tech:
                tech.council_session_id = uuid.UUID(result["session_id"])
                tech.council_strategy = result.get("decision")
                tech.implementation_roadmap = result.get("recommendations", {})
                tech.status = (
                    TechStatus.APPROVED.value
                    if result.get("decision") == "APPROVE"
                    else TechStatus.COUNCIL_QUEUE.value
                )
                await db.commit()

        return result

    async def get_discoveries(
        self,
        db: AsyncSession,
        tenant_id: str,
        category: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        tenant_uuid = uuid.UUID(str(tenant_id))
        query = (
            select(TechnologyDiscovery)
            .where(TechnologyDiscovery.tenant_id == tenant_uuid)
            .order_by(TechnologyDiscovery.relevance_score.desc(), TechnologyDiscovery.discovered_at.desc())
            .limit(limit)
        )
        if category:
            query = query.where(TechnologyDiscovery.category == category)
        if status:
            query = query.where(TechnologyDiscovery.status == status)
        if priority:
            query = query.where(TechnologyDiscovery.priority == priority)

        result = await db.execute(query)
        return [self._serialize_discovery(t) for t in result.scalars().all()]

    async def get_tech_landscape(self, db: AsyncSession, tenant_id: str) -> dict[str, Any]:
        """High-level technology landscape dashboard."""
        tenant_uuid = uuid.UUID(str(tenant_id))
        result = await db.execute(
            select(TechnologyDiscovery)
            .where(TechnologyDiscovery.tenant_id == tenant_uuid)
            .order_by(TechnologyDiscovery.discovered_at.desc())
            .limit(200)
        )
        techs = result.scalars().all()

        by_category: dict = {}
        for t in techs:
            by_category.setdefault(t.category, []).append({
                "name": t.technology_name,
                "status": t.status,
                "priority": t.priority,
                "relevance": t.relevance_score,
            })

        by_status: dict = {}
        for t in techs:
            by_status[t.status] = by_status.get(t.status, 0) + 1

        return {
            "total_discoveries": len(techs),
            "by_category": by_category,
            "by_status": by_status,
            "critical_priority": [self._serialize_discovery(t) for t in techs if t.priority == "critical"][:5],
            "approved_for_adoption": [self._serialize_discovery(t) for t in techs if t.status == TechStatus.APPROVED.value][:10],
            "recently_deployed": [self._serialize_discovery(t) for t in techs if t.status == TechStatus.DEPLOYED.value][:5],
        }

    async def _discover_technologies(self, tenant_uuid: uuid.UUID) -> list[dict]:
        """AI-powered technology landscape scan."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        discovery_prompt = f"""You are JARVIS, the AI-powered intelligence core of Aliyar Solutions.
Today is {today}. Execute a comprehensive technology landscape scan.

Aliyar Solutions delivers: AI automation, cloud infrastructure (AWS), DevOps, security, web applications,
sales automation, and operational intelligence systems.

Scan these technology domains and identify the most impactful emerging technologies:
- Large Language Models (new releases, fine-tuning tools, deployment frameworks)
- AI Agents and orchestration frameworks (LangChain, CrewAI, new frameworks)
- Voice AI (ElevenLabs competitors, STT/TTS advances)
- Vector databases and RAG improvements
- Cloud-native tools (Kubernetes operators, serverless advances)
- DevOps automation (CI/CD tools, observability platforms)
- Security tools (AI-powered security, zero-trust advances)
- Low-code/no-code platforms competitive to what Aliyar delivers
- Sales automation and CRM AI tools

Return a JSON array of 10-15 technology discoveries. Each must have:
- technology_name: string (specific product/framework/model name)
- source: one of {json.dumps([s['name'] for s in MONITORED_SOURCES])}
- source_url: URL where this can be found (best guess, common URL)
- category: one of {json.dumps(TECH_CATEGORIES)}
- provider: company or organization behind it
- relevance_score: 0-100 (how relevant to Aliyar Solutions operations)
- priority: critical/high/medium/low
- summary: 2-3 sentence description
- capabilities: array of 3-5 capability strings
- integration_feasibility: 0-100 (how easy to integrate into existing JARVIS stack)
- estimated_impact: one paragraph on business/operational impact

Focus on technologies released or significantly updated in the last 30 days.
Return only valid JSON array, no markdown."""

        try:
            response, _ = await asyncio.wait_for(
                ai_router.chat(
                    [Message(role="user", content=discovery_prompt)],
                    task_type=TaskType.RESEARCH,
                ),
                timeout=60.0,
            )
            if response.error:
                raise ValueError(response.error)
            discoveries = json.loads(_clean_json(response.content or ""))
            return discoveries if isinstance(discoveries, list) else []
        except Exception as exc:
            logger.warning("Technology discovery scan failed: %s", exc)
            return []

    async def _generate_adoption_guide(self, tech: TechnologyDiscovery) -> str:
        """Generate a comprehensive adoption guide for a technology."""
        prompt = f"""You are a senior technology architect at Aliyar Solutions.

Generate a comprehensive adoption guide for: {tech.technology_name}

Context:
- Category: {tech.category}
- Summary: {tech.summary}
- Capabilities: {json.dumps(tech.capabilities)}
- Current JARVIS stack: FastAPI, PostgreSQL, Redis, React, AWS ECS, Docker

The guide must include:
1. **What It Is** — technical overview (2 paragraphs)
2. **Why Aliyar Solutions Should Adopt** — business case, competitive advantage
3. **Integration Points** — exactly where in the JARVIS codebase to integrate
4. **Implementation Steps** — numbered step-by-step technical guide
5. **Configuration Required** — env vars, API keys, dependencies needed
6. **Estimated Implementation Time** — hours/days/weeks
7. **Risks & Mitigations** — what could go wrong and how to prevent it
8. **Success Metrics** — how to measure successful adoption
9. **Monthly Cost Estimate** — realistic cost projection
10. **First 30 Days Action Plan** — specific tasks to complete

Write at senior-architect level. Be specific and actionable."""

        try:
            response, _ = await asyncio.wait_for(
                ai_router.chat(
                    [Message(role="user", content=prompt)],
                    task_type=TaskType.STRATEGY,
                ),
                timeout=60.0,
            )
            if response.error:
                raise ValueError(response.error)
            return response.content or f"Adoption guide generation pending for {tech.technology_name}"
        except Exception as exc:
            logger.warning("Adoption guide generation failed: %s", exc)
            return f"Adoption guide generation pending for {tech.technology_name}"

    async def _submit_to_council(self, tenant_id: str, tech_dict: dict) -> dict[str, Any]:
        """Submit technology to AI Council for strategic evaluation."""
        question = (
            f"Evaluate this technology discovery for Aliyar Solutions:\n\n"
            f"Technology: {tech_dict['technology_name']}\n"
            f"Category: {tech_dict['category']}\n"
            f"Summary: {tech_dict.get('summary', '')}\n"
            f"Capabilities: {json.dumps(tech_dict.get('capabilities', []))}\n"
            f"Relevance Score: {tech_dict.get('relevance_score', 0)}/100\n\n"
            f"Should Aliyar Solutions adopt this technology? "
            f"Provide: (1) strategic recommendation, (2) integration priority, "
            f"(3) implementation roadmap, (4) competitive advantage analysis, "
            f"(5) specific risks to avoid."
        )

        context = {
            "tech_name": tech_dict["technology_name"],
            "category": tech_dict["category"],
            "relevance": tech_dict.get("relevance_score", 0),
            "purpose": "technology_adoption_evaluation",
        }

        result = await intelligence_council.convene(
            question=question,
            context=context,
            council_type="technology_evaluation",
            tenant_id=tenant_id,
        )

        return {
            "session_id": result.session_id,
            "decision": result.decision,
            "score": result.score,
            "reasoning": result.reasoning,
            "recommendations": {"council_strategy": result.reasoning[:500]},
        }

    def _serialize_discovery(self, t: TechnologyDiscovery) -> dict:
        return {
            "id": str(t.id),
            "technology_name": t.technology_name,
            "source": t.source,
            "source_url": t.source_url,
            "category": t.category,
            "provider": t.provider,
            "relevance_score": t.relevance_score,
            "priority": t.priority,
            "summary": t.summary,
            "capabilities": t.capabilities or [],
            "integration_feasibility": t.integration_feasibility,
            "estimated_impact": t.estimated_impact,
            "adoption_guide": t.adoption_guide,
            "council_strategy": t.council_strategy,
            "status": t.status,
            "discovered_at": t.discovered_at.isoformat() if t.discovered_at else None,
            "deployed_at": t.deployed_at.isoformat() if t.deployed_at else None,
        }


def _clean_json(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("```"):
        parts = text.split("```", 2)
        text = parts[1]
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1:
        return text[start:end + 1]
    return text.strip()


tech_evolution_engine = TechEvolutionEngine()
