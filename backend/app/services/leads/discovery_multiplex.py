"""
Multi-path lead discovery — resilience against single provider failure.
Implements Apollo + Google Maps + Web Search + LinkedIn + Referral network.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class MultiPathDiscovery:
    """Unified discovery engine with fallback chain."""

    async def discover_leads(
        self,
        query: str,
        industry: str = None,
        location: str = None,
        limit: int = 25,
        preferred_methods: list[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Discover leads using multiple methods with intelligent fallback.
        Tries methods in order until sufficient results gathered.
        """
        if not preferred_methods:
            preferred_methods = ["apollo", "google_maps", "web_search", "linkedin", "referral"]

        all_leads = []
        tried_methods = []

        for method in preferred_methods:
            if len(all_leads) >= limit:
                break

            try:
                if method == "apollo":
                    leads = await self._discover_apollo(query, industry, location, limit - len(all_leads))
                elif method == "google_maps":
                    leads = await self._discover_google_maps(query, location, limit - len(all_leads))
                elif method == "web_search":
                    leads = await self._discover_web_search(query, industry, limit - len(all_leads))
                elif method == "linkedin":
                    leads = await self._discover_linkedin(query, industry, limit - len(all_leads))
                elif method == "referral":
                    leads = await self._discover_referral_network(query, limit - len(all_leads))
                else:
                    continue

                if leads:
                    all_leads.extend(leads)
                    tried_methods.append((method, len(leads)))
                    logger.info("Discovery method '%s' returned %d leads", method, len(leads))

            except Exception as exc:
                logger.warning("Discovery method '%s' failed: %s", method, exc)
                tried_methods.append((method, 0))
                continue

        return all_leads[:limit] if all_leads else []

    async def _discover_apollo(
        self,
        query: str,
        industry: str,
        location: str,
        limit: int,
    ) -> list[dict]:
        """Apollo.io discovery — primary method."""
        if not settings.APOLLO_API_KEY:
            logger.debug("Apollo API key not set")
            return []

        from app.services.leads.discovery import LeadDiscoveryEngine
        engine = LeadDiscoveryEngine()

        filters = {}
        if industry:
            filters["industries"] = [industry]
        if location:
            filters["locations"] = [location]
        filters["limit"] = limit

        try:
            results = await engine.search_apollo(query, filters)
            return results
        except Exception as exc:
            logger.error("Apollo discovery failed: %s", exc)
            return []

    async def _discover_google_maps(
        self,
        query: str,
        location: str,
        limit: int,
    ) -> list[dict]:
        """Google Maps Places discovery — local business targeting."""
        if not settings.GOOGLE_MAPS_API_KEY:
            logger.debug("Google Maps API key not set")
            return []

        if not location:
            location = "United States"

        search_query = f"{query} near {location}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"https://maps.googleapis.com/maps/api/place/textsearch/json",
                    params={
                        "query": search_query,
                        "key": settings.GOOGLE_MAPS_API_KEY,
                        "pagesize": min(limit, 20),
                    },
                )

                if response.status_code != 200:
                    logger.warning("Google Maps query failed: %s", response.status_code)
                    return []

                data = response.json()
                results = data.get("results", [])

                leads = []
                for place in results[:limit]:
                    leads.append({
                        "name": place.get("name", ""),
                        "company": place.get("name", ""),
                        "location": place.get("formatted_address", ""),
                        "phone": place.get("formatted_phone_number"),
                        "website": place.get("website"),
                        "types": place.get("types", []),
                        "rating": place.get("rating"),
                        "source": "google_maps",
                        "place_id": place.get("place_id"),
                    })

                logger.info("Google Maps found %d places for '%s'", len(leads), search_query)
                return leads

        except Exception as exc:
            logger.error("Google Maps discovery failed: %s", exc)
            return []

    async def _discover_web_search(
        self,
        query: str,
        industry: str,
        limit: int,
    ) -> list[dict]:
        """Web search via DuckDuckGo lite — no API key required."""
        search_query = f"{industry or query} company agency"
        leads = []
        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                headers={"User-Agent": "Mozilla/5.0 (compatible; JARVIS-LeadDiscovery/1.0)"},
                follow_redirects=True,
            ) as client:
                # DuckDuckGo Instant Answer API (free, no key)
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": search_query,
                        "format": "json",
                        "no_html": "1",
                        "skip_disambig": "1",
                    },
                )
                if resp.status_code != 200:
                    return []
                data = resp.json()

                # Extract company names from RelatedTopics
                for topic in (data.get("RelatedTopics") or [])[:limit]:
                    text = topic.get("Text") or ""
                    url = topic.get("FirstURL") or ""
                    if not text:
                        continue
                    name = text.split(" - ")[0].strip() or text[:60].strip()
                    if len(name) < 3 or len(name) > 120:
                        continue
                    leads.append({
                        "company": name,
                        "company_name": name,
                        "website": url if url.startswith("http") else None,
                        "source": "duckduckgo_web_search",
                        "industry": industry,
                        "description": text[:200],
                    })

                # Also check Abstract for a direct match
                if data.get("AbstractText") and data.get("AbstractURL"):
                    leads.insert(0, {
                        "company": data.get("Heading") or query,
                        "company_name": data.get("Heading") or query,
                        "website": data.get("AbstractURL"),
                        "source": "duckduckgo_web_search",
                        "industry": industry,
                        "description": (data.get("AbstractText") or "")[:200],
                    })

        except Exception as exc:
            logger.warning("DuckDuckGo web search failed: %s", exc)
        return leads[:limit]

    async def _discover_linkedin(
        self,
        query: str,
        industry: str,
        limit: int,
    ) -> list[dict]:
        """LinkedIn company discovery via Clearbit autocomplete (free tier)."""
        leads = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://autocomplete.clearbit.com/v1/companies/suggest",
                    params={"query": f"{industry or query}"},
                    headers={"User-Agent": "JARVIS-LeadDiscovery/1.0"},
                )
                if resp.status_code == 200:
                    for company in resp.json()[:limit]:
                        name = company.get("name") or ""
                        if not name:
                            continue
                        leads.append({
                            "company": name,
                            "company_name": name,
                            "website": company.get("domain") and f"https://{company['domain']}",
                            "industry": industry,
                            "source": "clearbit_linkedin_fallback",
                            "enrichment_data": {
                                "logo": company.get("logo"),
                                "domain": company.get("domain"),
                            },
                        })
        except Exception as exc:
            logger.warning("Clearbit/LinkedIn fallback failed: %s", exc)
        return leads[:limit]

    async def _discover_referral_network(
        self,
        query: str,
        limit: int,
    ) -> list[dict]:
        """GitHub org discovery — active open-source companies in tech."""
        leads = []
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(
                    "https://api.github.com/search/repositories",
                    params={
                        "q": f"{query} in:description language:python stars:>50",
                        "sort": "updated",
                        "per_page": min(limit, 30),
                    },
                    headers={"Accept": "application/vnd.github+json"},
                )
                if resp.status_code == 200:
                    for item in resp.json().get("items", [])[:limit]:
                        owner = item.get("owner") or {}
                        org_name = owner.get("login") or ""
                        if not org_name or owner.get("type") != "Organization":
                            continue
                        leads.append({
                            "company": org_name,
                            "company_name": org_name,
                            "website": item.get("homepage") or f"https://github.com/{org_name}",
                            "source": "github_org_network",
                            "industry": "technology",
                            "description": (item.get("description") or "")[:200],
                        })
        except Exception as exc:
            logger.warning("GitHub org discovery failed: %s", exc)
        return leads[:limit]


multi_path_discovery = MultiPathDiscovery()
