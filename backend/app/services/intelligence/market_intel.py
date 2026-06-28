from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.intelligence import CompetitorProfile, MarketIntelligence
from app.services.ai.base_provider import Message, TaskType
from app.services.ai.router import ai_router
from app.services.notifications import notify_business_event

logger = logging.getLogger(__name__)

DEFAULT_MARKET_TOPICS = [
    "AI automation market",
    "SMB technology adoption",
    "competitor pricing changes",
]

MARKET_REPORT_PROMPT = """You are the Aliyar Solutions Market Intelligence Division.

Generate an executive market intelligence report for Captain Syed Abrar.

Topics:
{topics}

Return a report that includes:
1. Executive summary
2. Market movement
3. Competitor and pricing implications
4. Revenue opportunities for Aliyar Solutions
5. Risks or watch-outs
6. Recommended next actions for the next 14 days

Keep the report practical. Focus on acquiring paying clients, improving close rate, and selecting profitable services.
This is internal strategy material for Aliyar Solutions."""


class MarketIntelligenceEngine:
    async def generate_report(self, topics: list[str], tenant_id) -> str:
        tenant_uuid = _coerce_tenant_id(tenant_id)
        normalized_topics = [topic.strip() for topic in topics if topic and topic.strip()] or DEFAULT_MARKET_TOPICS
        prompt = MARKET_REPORT_PROMPT.format(topics="\n".join(f"- {topic}" for topic in normalized_topics))

        try:
            response, _ = await asyncio.wait_for(
                ai_router.chat(
                    [Message(role="user", content=prompt)],
                    task_type=TaskType.RESEARCH,
                    force_provider="google",
                    force_model="gemini-pro",
                    system_prompt="You are a senior market intelligence analyst for a technology operations company.",
                    max_tokens=4500,
                ),
                timeout=60.0,
            )
            if response.error:
                logger.warning("Market intelligence AI failed: %s", response.error)
                return ""
            report_content = (response.content or "").strip()
            if not report_content:
                logger.warning("Market intelligence report returned empty content")
                return ""
        except Exception as exc:
            logger.warning("Market intelligence AI call failed: %s", exc)
            return ""

        async with AsyncSessionLocal() as db:
            await _apply_tenant_context(db, tenant_uuid)
            report = MarketIntelligence(
                tenant_id=tenant_uuid,
                title=f"Market Intelligence Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
                topics=normalized_topics,
                report_content=report_content,
                summary=_first_paragraph(report_content),
                opportunities=_extract_lines(report_content, ("opportunity", "next action", "recommended")),
                risks=_extract_lines(report_content, ("risk", "watch")),
                confidence_score=0.78 if not response.demo else 0.25,
                evidence_refs=normalized_topics,
                generated_by=response.model or "gemini-pro",
            )
            db.add(report)
            await db.flush()
            db.add(
                AuditLog(
                    tenant_id=tenant_uuid,
                    action="market_intelligence_report_generated",
                    entity_type="market_intelligence",
                    entity_id=None,
                    actor="market_intelligence_engine",
                    details={"topics": normalized_topics, "model": response.model, "provider": response.provider},
                )
            )
            await db.commit()

        return report_content

    async def monitor_competitors(self, tenant_id) -> list[dict]:
        tenant_uuid = _coerce_tenant_id(tenant_id)
        changes: list[dict[str, Any]] = []

        async with AsyncSessionLocal() as db:
            await _apply_tenant_context(db, tenant_uuid)
            result = await db.execute(
                select(CompetitorProfile)
                .where(
                    CompetitorProfile.tenant_id == tenant_uuid,
                    CompetitorProfile.is_active.is_(True),
                )
                .order_by(CompetitorProfile.name)
            )
            competitors = list(result.scalars().all())

            async with httpx.AsyncClient(timeout=12, follow_redirects=True, headers={"User-Agent": "AliyarSolutions-MarketIntel/1.0"}) as client:
                for competitor in competitors:
                    observed = await self._observe_competitor(client, competitor)
                    if not observed:
                        continue

                    pricing_changed = (
                        bool(competitor.last_pricing_hash)
                        and bool(observed.get("pricing_hash"))
                        and competitor.last_pricing_hash != observed["pricing_hash"]
                    )
                    website_changed = (
                        bool(competitor.last_website_hash)
                        and bool(observed.get("website_hash"))
                        and competitor.last_website_hash != observed["website_hash"]
                    )
                    linkedin_changed = (
                        bool(competitor.last_linkedin_hash)
                        and bool(observed.get("linkedin_hash"))
                        and competitor.last_linkedin_hash != observed["linkedin_hash"]
                    )

                    change = {
                        "competitor": competitor.name,
                        "pricing_changed": pricing_changed,
                        "website_changed": website_changed,
                        "linkedin_changed": linkedin_changed,
                        "checked_at": datetime.now(timezone.utc).isoformat(),
                    }
                    if any((pricing_changed, website_changed, linkedin_changed)):
                        changes.append(change)
                        competitor.last_change_summary = json.dumps(change)

                    competitor.last_website_hash = observed.get("website_hash") or competitor.last_website_hash
                    competitor.last_linkedin_hash = observed.get("linkedin_hash") or competitor.last_linkedin_hash
                    competitor.last_pricing_hash = observed.get("pricing_hash") or competitor.last_pricing_hash
                    competitor.last_checked_at = datetime.now(timezone.utc)

                    if pricing_changed:
                        await notify_business_event(
                            "competitor_pricing_changed",
                            f"Competitor pricing changed: {competitor.name}",
                            "JARVIS detected a pricing-page change. Review the competitor profile before the next outreach or proposal cycle.",
                        )

            db.add(
                AuditLog(
                    tenant_id=tenant_uuid,
                    action="competitor_monitoring_completed",
                    entity_type="competitor_profiles",
                    actor="market_intelligence_engine",
                    details={"competitors_checked": len(competitors), "changes_detected": len(changes)},
                )
            )
            await db.commit()

        return changes

    async def _observe_competitor(self, client: httpx.AsyncClient, competitor: CompetitorProfile) -> dict[str, str]:
        return {
            "website_hash": await _fetch_hash(client, competitor.website_url),
            "linkedin_hash": await _fetch_hash(client, competitor.linkedin_url),
            "pricing_hash": await _fetch_hash(client, competitor.pricing_url),
        }


async def _fetch_hash(client: httpx.AsyncClient, url: str | None) -> str:
    if not url:
        return ""
    try:
        response = await client.get(url)
        text = " ".join((response.text or "").split())
        payload = f"{response.status_code}:{text[:50000]}"
        return hashlib.sha256(payload.encode("utf-8", errors="ignore")).hexdigest()
    except Exception as exc:
        logger.info("Competitor fetch skipped for %s: %s", url, exc)
        return ""


async def _apply_tenant_context(db, tenant_id: uuid.UUID) -> None:
    if settings.DATABASE_URL.startswith("sqlite"):
        return
    await set_tenant_context(db, str(tenant_id))


def _coerce_tenant_id(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _first_paragraph(text: str) -> str:
    for part in text.splitlines():
        clean = part.strip(" -#")
        if len(clean) > 40:
            return clean[:1000]
    return text[:1000]


def _extract_lines(text: str, needles: tuple[str, ...]) -> list[str]:
    lines = []
    for line in text.splitlines():
        clean = line.strip(" -0123456789.")
        lower = clean.lower()
        if clean and any(needle in lower for needle in needles):
            lines.append(clean[:500])
        if len(lines) >= 6:
            break
    return lines
