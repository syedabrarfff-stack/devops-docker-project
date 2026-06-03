from __future__ import annotations

import hashlib
import logging
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.intelligence import CompetitorProfile
from app.models.revenue_activation import MarketPulseItem
from app.services.ai.base_provider import Message, TaskType
from app.services.ai.router import ai_router
from app.services.notifications import notify_business_event

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    {"source": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"source": "Product Hunt", "url": "https://www.producthunt.com/feed"},
    {"source": "Hacker News", "url": "https://hnrss.org/frontpage"},
    {"source": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"source": "Wired", "url": "https://www.wired.com/feed/rss"},
]

TRACKED_COMPETITORS = [
    {"name": "Cognitiv+", "website_url": "https://www.cognitivplus.com/", "pricing_url": ""},
    {"name": "Automation Agency", "website_url": "https://www.automation-agency.co.uk/", "pricing_url": ""},
    {"name": "SmartSuite AI", "website_url": "https://www.smartsuite.com/", "pricing_url": "https://www.smartsuite.com/pricing"},
]


class MarketAwarenessEngine:
    async def weekly_scan(self, tenant_id=None) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        articles = await self._fetch_feed_articles()
        stored_articles = 0
        high_relevance = []
        for article in articles[:80]:
            score, reason = await self._score_article(article)
            if score < 7.0:
                continue
            created = await self._store_market_item(tenant_uuid, article, score, reason)
            if created:
                stored_articles += 1
                high_relevance.append({**article, "score": score, "reason": reason})
                await notify_business_event(
                    "market_intelligence",
                    f"Market signal: {article['title'][:90]}",
                    f"{article['source']} relevance {score}/10. {reason}\n{article['url']}",
                )

        competitor_result = await self.track_competitors(tenant_uuid)
        return {
            "tenant_id": str(tenant_uuid),
            "articles_scanned": len(articles),
            "high_relevance_new_items": stored_articles,
            "competitors": competitor_result,
        }

    async def market_pulse(self, tenant_id=None, limit: int = 25) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                rows = (
                    await session.execute(
                        select(MarketPulseItem)
                        .where(MarketPulseItem.tenant_id == tenant_uuid)
                        .order_by(MarketPulseItem.relevance_score.desc(), MarketPulseItem.created_at.desc())
                        .limit(max(1, min(limit, 100)))
                    )
                ).scalars().all()
                competitors = (
                    await session.execute(
                        select(CompetitorProfile)
                        .where(CompetitorProfile.tenant_id == tenant_uuid, CompetitorProfile.is_active == True)
                        .order_by(CompetitorProfile.last_checked_at.desc().nullslast())
                        .limit(10)
                    )
                ).scalars().all()
        return {
            "tenant_id": str(tenant_uuid),
            "market_items": [_serialize_market_item(row) for row in rows],
            "competitors": [
                {
                    "name": row.name,
                    "website_url": row.website_url,
                    "pricing_url": row.pricing_url,
                    "last_change_summary": row.last_change_summary,
                    "last_checked_at": row.last_checked_at.isoformat() if row.last_checked_at else None,
                    "metadata": row.metadata_json or {},
                }
                for row in competitors
            ],
        }

    async def track_competitors(self, tenant_id=None) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        created = 0
        changed = 0
        checked = 0
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await set_tenant_context(session, str(tenant_uuid))
                    for spec in TRACKED_COMPETITORS:
                        checked += 1
                        homepage_text = await _fetch_text(client, spec["website_url"])
                        pricing_text = await _fetch_text(client, spec["pricing_url"]) if spec.get("pricing_url") else ""
                        website_hash = _hash(homepage_text[:50000])
                        pricing_hash = _hash(pricing_text[:50000]) if pricing_text else ""
                        profile = await session.scalar(
                            select(CompetitorProfile).where(
                                CompetitorProfile.tenant_id == tenant_uuid,
                                CompetitorProfile.name == spec["name"],
                            )
                        )
                        pricing_changed = bool(profile and pricing_hash and profile.last_pricing_hash and profile.last_pricing_hash != pricing_hash)
                        website_changed = bool(profile and website_hash and profile.last_website_hash and profile.last_website_hash != website_hash)
                        summary = _competitor_summary(spec, homepage_text, pricing_text, pricing_changed, website_changed)
                        if not profile:
                            profile = CompetitorProfile(
                                tenant_id=tenant_uuid,
                                name=spec["name"],
                                website_url=spec["website_url"],
                                pricing_url=spec.get("pricing_url", ""),
                                last_website_hash=website_hash,
                                last_pricing_hash=pricing_hash,
                                last_change_summary="Initial Batch 3 market tracker snapshot created.",
                                last_checked_at=datetime.now(UTC),
                                is_active=True,
                                metadata_json=summary,
                            )
                            session.add(profile)
                            created += 1
                        else:
                            profile.website_url = spec["website_url"]
                            profile.pricing_url = spec.get("pricing_url", "")
                            profile.last_website_hash = website_hash or profile.last_website_hash
                            profile.last_pricing_hash = pricing_hash or profile.last_pricing_hash
                            profile.last_checked_at = datetime.now(UTC)
                            profile.metadata_json = {**(profile.metadata_json or {}), **summary}
                            if pricing_changed or website_changed:
                                changed += 1
                                profile.last_change_summary = summary["change_summary"]
                                await notify_business_event(
                                    "competitor_change",
                                    f"Competitor change detected: {spec['name']}",
                                    summary["change_summary"],
                                )
                            else:
                                profile.last_change_summary = "No public pricing or homepage change detected in latest scan."

                    session.add(
                        AuditLog(
                            tenant_id=tenant_uuid,
                            action="weekly_market_scan_completed",
                            entity_type="market_awareness",
                            actor="MarketAwarenessEngine",
                            details={"checked": checked, "created": created, "changed": changed},
                        )
                    )
        return {"checked": checked, "created": created, "changed": changed}

    async def _fetch_feed_articles(self) -> list[dict[str, Any]]:
        articles = []
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            for feed in RSS_FEEDS:
                try:
                    response = await client.get(feed["url"])
                    if response.status_code >= 400:
                        continue
                    articles.extend(_parse_feed(feed["source"], response.text))
                except Exception as exc:
                    logger.warning("RSS feed failed for %s: %s", feed["source"], exc)
        return articles

    async def _score_article(self, article: dict[str, Any]) -> tuple[float, str]:
        fallback = _heuristic_relevance(article)
        prompt = f"""
Score this article for Aliyar Solutions revenue strategy from 0 to 10.
Aliyar sells AI operations, workflow systems, cloud/DevOps, dashboards, CRM, client acquisition, and automation to SMBs.
Return JSON only: {{"score":7.5,"reason":"..."}}
Article:
Title: {article.get('title')}
Source: {article.get('source')}
Summary: {article.get('summary')}
URL: {article.get('url')}
""".strip()
        try:
            response, _ = await ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=TaskType.RESEARCH,
                max_tokens=300,
            )
            if not response.error:
                parsed = _parse_json(response.content)
                score = float(parsed.get("score", fallback[0]))
                reason = str(parsed.get("reason") or fallback[1])
                return max(0.0, min(10.0, score)), reason[:500]
        except Exception:
            pass
        return fallback

    async def _store_market_item(self, tenant_uuid, article: dict, score: float, reason: str) -> bool:
        content_hash = _hash(f"{article.get('source')}|{article.get('url')}|{article.get('title')}")
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                existing = await session.scalar(
                    select(MarketPulseItem.id).where(
                        MarketPulseItem.tenant_id == tenant_uuid,
                        MarketPulseItem.content_hash == content_hash,
                    )
                )
                if existing:
                    return False
                session.add(
                    MarketPulseItem(
                        tenant_id=tenant_uuid,
                        source=article["source"],
                        title=article["title"][:500],
                        url=article["url"],
                        summary=article.get("summary"),
                        relevance_score=score,
                        relevance_reason=reason,
                        published_at=article.get("published_at"),
                        content_hash=content_hash,
                        payload=_serializable_article(article),
                    )
                )
                session.add(
                    AuditLog(
                        tenant_id=tenant_uuid,
                        action="market_pulse_item_stored",
                        entity_type="market_pulse_item",
                        actor="MarketAwarenessEngine",
                        details={"source": article["source"], "score": score, "title": article["title"][:120]},
                    )
                )
                return True


def _parse_feed(source: str, xml_text: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text.encode("utf-8"))
    rows = []
    channel_items = root.findall(".//item")
    atom_items = root.findall("{http://www.w3.org/2005/Atom}entry")
    for item in channel_items[:25]:
        title = _node_text(item, "title")
        link = _node_text(item, "link")
        summary = _node_text(item, "description")
        published = _parse_date(_node_text(item, "pubDate"))
        if title and link:
            rows.append({"source": source, "title": title, "url": link, "summary": _clean(summary), "published_at": published})
    for item in atom_items[:25]:
        title = _node_text(item, "{http://www.w3.org/2005/Atom}title")
        link_node = item.find("{http://www.w3.org/2005/Atom}link")
        link = link_node.attrib.get("href") if link_node is not None else ""
        summary = _node_text(item, "{http://www.w3.org/2005/Atom}summary")
        published = _parse_date(_node_text(item, "{http://www.w3.org/2005/Atom}updated"))
        if title and link:
            rows.append({"source": source, "title": title, "url": link, "summary": _clean(summary), "published_at": published})
    return rows


def _serializable_article(article: dict[str, Any]) -> dict[str, Any]:
    published_at = article.get("published_at")
    return {
        **article,
        "published_at": published_at.isoformat() if isinstance(published_at, datetime) else published_at,
    }


async def _fetch_text(client: httpx.AsyncClient, url: str) -> str:
    if not url:
        return ""
    try:
        response = await client.get(url, headers={"User-Agent": "JARVIS-Aliyar-Solutions"})
        if response.status_code >= 400:
            return ""
        return _clean(response.text)
    except Exception:
        return ""


def _node_text(item: ET.Element, tag: str) -> str:
    node = item.find(tag)
    return "".join(node.itertext()).strip() if node is not None else ""


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except Exception:
        return None


def _heuristic_relevance(article: dict) -> tuple[float, str]:
    text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    keywords = {
        "ai": 2,
        "automation": 2,
        "agent": 2,
        "workflow": 2,
        "crm": 2,
        "cloud": 1.5,
        "security": 1.5,
        "startup": 1,
        "sales": 1,
        "productivity": 1,
        "enterprise": 1,
    }
    score = 2.0 + sum(weight for keyword, weight in keywords.items() if keyword in text)
    return min(10.0, score), "Heuristic relevance based on Aliyar service and revenue keywords."


def _competitor_summary(spec: dict, homepage_text: str, pricing_text: str, pricing_changed: bool, website_changed: bool) -> dict:
    pricing_signals = _pricing_signals(pricing_text or homepage_text)
    changes = []
    if pricing_changed:
        changes.append("pricing page changed")
    if website_changed:
        changes.append("homepage changed")
    return {
        "pricing_signals": pricing_signals,
        "service_signals": _service_signals(homepage_text),
        "pricing_changed": pricing_changed,
        "website_changed": website_changed,
        "change_summary": f"{spec['name']}: {', '.join(changes) if changes else 'no change detected'}; pricing signals: {', '.join(pricing_signals[:5]) or 'none found'}.",
    }


def _pricing_signals(text: str) -> list[str]:
    signals = re.findall(r"(?:[$£€]\s?\d[\d,]*(?:/\w+)?|\d+\s?(?:per month|/month|monthly|annually))", text or "", flags=re.I)
    return list(dict.fromkeys(signal.strip() for signal in signals))[:10]


def _service_signals(text: str) -> list[str]:
    lowered = (text or "").lower()
    services = ["automation", "workflow", "ai", "dashboard", "crm", "cloud", "security", "compliance", "integration", "agent"]
    return [service for service in services if service in lowered]


def _parse_json(text: str) -> dict[str, Any]:
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start:end + 1]
        parsed = __import__("json").loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _serialize_market_item(row: MarketPulseItem) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "source": row.source,
        "title": row.title,
        "url": row.url,
        "summary": row.summary,
        "relevance_score": row.relevance_score,
        "relevance_reason": row.relevance_reason,
        "published_at": row.published_at.isoformat() if row.published_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()


def _hash(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _tenant_uuid(value=None) -> uuid.UUID:
    raw = value or settings.JARVIS_DEFAULT_TENANT_ID
    if not raw:
        raise ValueError("tenant_id is required")
    return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))


market_awareness_engine = MarketAwarenessEngine()
