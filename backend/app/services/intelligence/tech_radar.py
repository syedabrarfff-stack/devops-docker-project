"""
JARVIS Technology Radar — continuously monitors the tech landscape and classifies
tools/frameworks into adopt / trial / assess / hold for Aliyar Solutions.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.intelligence import TechRadarEntry
from app.services.ai.base_provider import Message

logger = logging.getLogger(__name__)

TECH_RADAR_PROMPT = """You are JARVIS analyzing the technology landscape for Aliyar Solutions — an AI consulting and DevOps company.

Evaluate the following 14 technologies relevant to our stack and business as of {date}.
Return ONLY a valid JSON array — no markdown, no explanation, no code fences.

Each item must have exactly these fields:
- name (string)
- category (one of: AI/ML, Cloud/AWS, DevOps, Security, Automation, Frameworks)
- status (one of: adopt, trial, assess, hold)
- summary (1 sentence, what it is)
- recommendation (1-2 sentences, what Aliyar Solutions should do with it)
- why_it_matters (1 sentence, business impact)

Technologies to evaluate:
1. Claude Sonnet 4.6 / Opus 4.7 (Anthropic)
2. AWS Bedrock Agents
3. Kubernetes + ArgoCD
4. Apache Kafka
5. LangGraph (multi-agent orchestration)
6. Terraform 1.x
7. OpenTelemetry
8. Qdrant (vector database)
9. GitHub Actions
10. FastAPI 0.115+
11. AWS Step Functions
12. Redis 8
13. Prometheus + Grafana
14. CrewAI

Status guide:
- adopt: proven, production-ready, use now
- trial: promising, test in next project
- assess: emerging, worth watching closely
- hold: pause, deprecated, or not suited for our stack

Return ONLY the JSON array. Example structure:
[{"name":"...","category":"...","status":"...","summary":"...","recommendation":"...","why_it_matters":"..."}]"""


async def scan_technologies(db: AsyncSession) -> int:
    """Run a full tech radar scan using AI and persist results."""
    from app.services.ai.router import ai_router
    from app.services.ai.base_provider import TaskType

    prompt = TECH_RADAR_PROMPT.format(date=datetime.now(timezone.utc).strftime("%B %Y"))
    messages = [Message(role="user", content=prompt)]

    try:
        response, _ = await ai_router.chat(
            messages,
            task_type=TaskType.RESEARCH,
            system_prompt="You are a technology analyst. Return only valid JSON arrays. No markdown.",
            max_tokens=3000,
        )

        raw = response.content.strip()
        # Strip any accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        entries = json.loads(raw)
        if not isinstance(entries, list):
            raise ValueError("Expected JSON array")

        # Clear stale entries and replace with fresh scan
        await db.execute(delete(TechRadarEntry))

        count = 0
        for item in entries:
            name = str(item.get("name", "")).strip()
            category = str(item.get("category", "General")).strip()
            status = str(item.get("status", "assess")).strip()
            if status not in ("adopt", "trial", "assess", "hold"):
                status = "assess"
            if not name:
                continue
            entry = TechRadarEntry(
                name=name,
                category=category,
                status=status,
                summary=item.get("summary", ""),
                recommendation=item.get("recommendation", ""),
                why_it_matters=item.get("why_it_matters", ""),
            )
            db.add(entry)
            count += 1

        return count

    except json.JSONDecodeError as e:
        logger.warning(f"Tech radar JSON parse error: {e}")
        return 0
    except Exception as e:
        logger.warning(f"Tech radar scan failed: {e}")
        return 0


async def get_radar(db: AsyncSession) -> dict:
    """Return tech radar entries grouped by category."""
    result = await db.execute(
        select(TechRadarEntry).order_by(TechRadarEntry.category, TechRadarEntry.status)
    )
    entries = result.scalars().all()

    grouped: dict = {}
    for e in entries:
        grouped.setdefault(e.category, []).append({
            "id": e.id,
            "name": e.name,
            "status": e.status,
            "summary": e.summary,
            "recommendation": e.recommendation,
            "why_it_matters": e.why_it_matters,
            "updated_at": e.updated_at.isoformat() if e.updated_at else None,
        })

    return {
        "categories": grouped,
        "total": len(entries),
        "by_status": {
            "adopt":  sum(1 for e in entries if e.status == "adopt"),
            "trial":  sum(1 for e in entries if e.status == "trial"),
            "assess": sum(1 for e in entries if e.status == "assess"),
            "hold":   sum(1 for e in entries if e.status == "hold"),
        },
    }
