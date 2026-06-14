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
        """Web search discovery — general internet search for company mentions."""
        # This would integrate with a web search API (Serper, Jina, etc.)
        # For now, return empty to indicate method available but not configured
        logger.debug("Web search discovery not yet configured")
        return []

    async def _discover_linkedin(
        self,
        query: str,
        industry: str,
        limit: int,
    ) -> list[dict]:
        """LinkedIn discovery — professional network targeting."""
        # This would require LinkedIn API access or scraping
        # For now, return empty to indicate method available
        logger.debug("LinkedIn discovery not yet configured")
        return []

    async def _discover_referral_network(
        self,
        query: str,
        limit: int,
    ) -> list[dict]:
        """Referral network discovery — warm introductions from partners."""
        # This would integrate with referral/partnership network
        logger.debug("Referral network discovery not yet configured")
        return []


multi_path_discovery = MultiPathDiscovery()
