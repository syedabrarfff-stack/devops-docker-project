from __future__ import annotations

import html
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import or_, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.lead import Lead, LeadStatus
from app.services.leads.scoring import lead_scoring_engine
from app.services.revenue_activation.osm_discovery import osm_local_business_discovery

logger = logging.getLogger(__name__)

HN_BASE = "https://hacker-news.firebaseio.com/v0"
CLEARBIT_URL = "https://autocomplete.clearbit.com/v1/companies/suggest"
GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
DEFAULT_CLEARBIT_QUERIES = ["saas", "crm", "devops", "cloud", "workflow", "agency"]


class FreeDiscoveryEngine:
    async def run(self, tenant_id=None, limit: int = 50) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        discovered: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            discovered.extend(await self._hn_whos_hiring(client, limit=20))
            discovered.extend(await self._clearbit_queries(client, DEFAULT_CLEARBIT_QUERIES, limit=30))
            discovered.extend(await self._github_trending_orgs(client, limit=25))
        try:
            discovered.extend(await osm_local_business_discovery.run(limit=40))
        except Exception as exc:
            logger.warning("OSM local business discovery failed: %s", exc)

        inserted = await self._insert_leads(tenant_uuid, discovered[: max(1, min(limit, 200))])
        enriched = await self.enrich_manual_leads(tenant_uuid, limit=25)
        return {
            "tenant_id": str(tenant_uuid),
            "sources": {
                "hacker_news_whos_hiring": sum(1 for row in discovered if row.get("source") == "hn_whos_hiring"),
                "clearbit_autocomplete": sum(1 for row in discovered if row.get("source") == "clearbit_autocomplete"),
                "github_active_repos": sum(1 for row in discovered if row.get("source") == "github_active_repos"),
                "osm_local_business": sum(1 for row in discovered if row.get("source") == "osm_local_business"),
            },
            "discovered": len(discovered),
            "inserted": inserted,
            "manual_leads_enriched": enriched,
        }

    async def enrich_manual_leads(self, tenant_id=None, limit: int = 25) -> int:
        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                leads = (
                    await session.execute(
                        select(Lead)
                        .where(
                            Lead.tenant_id == tenant_uuid,
                            Lead.company_name.is_not(None),
                            or_(Lead.website.is_(None), Lead.website == ""),
                        )
                        .order_by(Lead.created_at.desc())
                        .limit(max(1, min(limit, 100)))
                    )
                ).scalars().all()

        enriched = 0
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            for lead in leads:
                suggestions = await self._clearbit_suggest(client, lead.company_name or lead.company or "")
                if not suggestions:
                    continue
                best = suggestions[0]
                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        await set_tenant_context(session, str(tenant_uuid))
                        live = await session.scalar(
                            select(Lead).where(Lead.tenant_id == tenant_uuid, Lead.id == lead.id)
                        )
                        if not live:
                            continue
                        live.website = best.get("domain") or live.website
                        live.company_website = best.get("domain") or live.company_website
                        live.industry = live.industry or best.get("type") or "Technology"
                        live.enrichment_data = {
                            **(live.enrichment_data or {}),
                            "clearbit_autocomplete": best,
                            "manual_enriched_at": datetime.now(UTC).isoformat(),
                        }
                        session.add(
                            AuditLog(
                                tenant_id=tenant_uuid,
                                action="manual_lead_clearbit_enriched",
                                entity_type="lead",
                                entity_id=live.id,
                                actor="FreeDiscoveryEngine",
                                details={"company": live.company_name, "domain": best.get("domain")},
                                after_json={"clearbit": best},
                            )
                        )
                        enriched += 1
        return enriched

    async def _hn_whos_hiring(self, client: httpx.AsyncClient, limit: int = 20) -> list[dict[str, Any]]:
        try:
            ids = (await client.get(f"{HN_BASE}/newstories.json")).json()[:250]
            thread = None
            for item_id in ids:
                item = (await client.get(f"{HN_BASE}/item/{item_id}.json")).json()
                title = (item or {}).get("title", "").lower()
                if "who is hiring" in title:
                    thread = item
                    break
            if not thread:
                return []
            rows = []
            for kid in (thread.get("kids") or [])[: max(limit * 3, 30)]:
                comment = (await client.get(f"{HN_BASE}/item/{kid}.json")).json() or {}
                text = _clean_html(comment.get("text") or "")
                company = _company_from_hn_text(text)
                if not company:
                    continue
                rows.append(
                    {
                        "company_name": company,
                        "industry": "Technology",
                        "country": "USA",
                        "source": "hn_whos_hiring",
                        "pain_points": ["hiring technical staff", "scaling delivery", "active product roadmap"],
                        "website": _domain_from_text(text),
                        "notes": f"Hacker News Who's Hiring signal: {text[:500]}",
                        "enrichment_data": {"hn_thread_id": thread.get("id"), "hn_comment_id": kid, "raw_text": text[:1200]},
                    }
                )
                if len(rows) >= limit:
                    break
            return rows
        except Exception as exc:
            logger.warning("HN free discovery failed: %s", exc)
            return []

    async def _clearbit_queries(self, client: httpx.AsyncClient, queries: list[str], limit: int = 30) -> list[dict[str, Any]]:
        rows = []
        for query in queries:
            for item in await self._clearbit_suggest(client, query):
                rows.append(
                    {
                        "company_name": item.get("name"),
                        "industry": item.get("type") or "Technology",
                        "country": "Unknown",
                        "source": "clearbit_autocomplete",
                        "pain_points": ["public digital footprint", "possible workflow and reporting gaps"],
                        "website": item.get("domain"),
                        "notes": f"Clearbit autocomplete match for query '{query}'.",
                        "enrichment_data": {"clearbit_autocomplete": item, "query": query},
                    }
                )
                if len(rows) >= limit:
                    return rows
        return rows

    async def _clearbit_suggest(self, client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
        if not query:
            return []
        try:
            response = await client.get(CLEARBIT_URL, params={"query": query})
            if response.status_code >= 400:
                return []
            data = response.json()
            return data if isinstance(data, list) else []
        except Exception:
            return []

    async def _github_trending_orgs(self, client: httpx.AsyncClient, limit: int = 25) -> list[dict[str, Any]]:
        try:
            response = await client.get(
                GITHUB_SEARCH_URL,
                params={"q": "stars:>100 pushed:>2024-01-01", "sort": "stars", "order": "desc", "per_page": limit},
                headers={"Accept": "application/vnd.github+json", "User-Agent": "JARVIS-Aliyar-Solutions"},
            )
            if response.status_code >= 400:
                return []
            items = response.json().get("items", [])
            rows = []
            seen = set()
            for repo in items:
                owner = repo.get("owner") or {}
                login = owner.get("login")
                if not login or login.lower() in seen:
                    continue
                seen.add(login.lower())
                rows.append(
                    {
                        "company_name": login,
                        "industry": _language_to_industry(repo.get("language")),
                        "country": "Unknown",
                        "source": "github_active_repos",
                        "pain_points": ["active engineering roadmap", "developer workflow scale", "release reliability"],
                        "website": repo.get("html_url"),
                        "notes": f"Active GitHub repository signal: {repo.get('full_name')} with {repo.get('stargazers_count')} stars.",
                        "enrichment_data": {"github_repository": repo.get("html_url"), "language": repo.get("language")},
                    }
                )
            return rows
        except Exception as exc:
            logger.warning("GitHub free discovery failed: %s", exc)
            return []

    async def _insert_leads(self, tenant_uuid: uuid.UUID, rows: list[dict[str, Any]]) -> int:
        inserted = 0
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                for row in rows:
                    if not row.get("company_name"):
                        continue
                    if await _lead_exists(session, tenant_uuid, row):
                        continue
                    score, reasoning = await lead_scoring_engine.score_against_icp(row)
                    lead = Lead(
                        tenant_id=tenant_uuid,
                        company_name=row.get("company_name"),
                        company=row.get("company_name"),
                        country=row.get("country"),
                        industry=row.get("industry"),
                        score=score,
                        status=LeadStatus.NEW,
                        source=row.get("source") or "free_discovery",
                        pain_points=row.get("pain_points") or [],
                        enrichment_data={**(row.get("enrichment_data") or {}), "icp_scoring": reasoning},
                        website=row.get("website"),
                        company_website=row.get("website"),
                        notes=row.get("notes"),
                        email=row.get("email"),
                        phone=row.get("phone"),
                    )
                    session.add(lead)
                    await session.flush()
                    session.add(
                        AuditLog(
                            tenant_id=tenant_uuid,
                            action="free_lead_discovered",
                            entity_type="lead",
                            entity_id=lead.id,
                            actor="FreeDiscoveryEngine",
                            details={"source": lead.source, "score": score, "company": lead.company_name},
                            after_json={"lead": row, "score": score, "reasoning": reasoning},
                        )
                    )
                    inserted += 1
        return inserted


async def _lead_exists(session, tenant_uuid: uuid.UUID, row: dict[str, Any]) -> bool:
    company = _clean(row.get("company_name"))
    website = _clean(row.get("website"))
    conditions = []
    if company:
        conditions.append(Lead.company_name.ilike(company))
        conditions.append(Lead.company.ilike(company))
    if website:
        conditions.append(Lead.website.ilike(f"%{website}%"))
        conditions.append(Lead.company_website.ilike(f"%{website}%"))
    if not conditions:
        return False
    existing = await session.scalar(select(Lead.id).where(Lead.tenant_id == tenant_uuid, or_(*conditions)).limit(1))
    return bool(existing)


def _clean_html(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _company_from_hn_text(text: str) -> str | None:
    if not text:
        return None
    first = text.split("|")[0].split("-")[0].strip()
    first = re.sub(r"\b(is hiring|hiring|remote|onsite|hybrid)\b", "", first, flags=re.I).strip(" :.,")
    if 2 <= len(first) <= 80:
        return first
    match = re.search(r"([A-Z][A-Za-z0-9& .]{2,60})\s+(?:is hiring|hiring)", text)
    return match.group(1).strip() if match else None


def _domain_from_text(text: str) -> str | None:
    match = re.search(r"https?://([A-Za-z0-9.-]+\.[A-Za-z]{2,})", text or "")
    return match.group(1).lower() if match else None


def _language_to_industry(language: str | None) -> str:
    if not language:
        return "Technology"
    if language.lower() in {"typescript", "javascript", "python", "go", "rust"}:
        return "Software"
    return f"{language} technology"


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _tenant_uuid(value=None) -> uuid.UUID:
    raw = value or settings.JARVIS_DEFAULT_TENANT_ID
    if not raw:
        raise ValueError("tenant_id is required")
    return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))


free_discovery_engine = FreeDiscoveryEngine()

