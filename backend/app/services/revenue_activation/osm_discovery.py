"""Free, no-API-key local business discovery via OpenStreetMap's public
Overpass API — no signup, no billing account, no key of any kind required.

This exists because the other free source (clearbit_autocomplete in
free_discovery.py) does pure keyword-substring matching against arbitrary
company names — searching "saas" can and does return a government research
agency because the word appears somewhere in an unrelated database. It fills
the lead count without finding anything real.

This module instead queries real, mapped local businesses by category and
city, in Aliyar Solutions' actual target industries/markets (see
ALIYAR_ICP in leads/scoring.py), and derives its pain-point signal from real,
observable evidence — whether OpenStreetMap has a website/phone/email on
record for that business — rather than repeating the same canned text on
every lead. Category and pain-point wording deliberately reuse the exact
vocabulary LeadScoringEngine's ICP matches on (target_industries,
target_countries, pain_points), because that vocabulary is a genuine,
already-defined statement of what Aliyar sells into — not a scoring hack.

Honest limitation: OSM rarely lists a business email. These leads will
usually score well (real industry/country/pain-point match) but still lack
an email address needed for outreach.py to actually send anything — the same
fundamental gap as clearbit_autocomplete, just with far better data behind
the leads that do reach the pipeline. Apollo/Google Maps (or any paid
enrichment) remains the real fix for email coverage specifically.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# One representative city per Aliyar target market (see TARGET_MARKETS /
# ALIYAR_ICP["target_countries"]). Small fixed bounding boxes keep each query
# modest and considerate of the shared public Overpass instance rather than
# scanning entire countries.
_CITY_BBOXES: dict[str, tuple[float, float, float, float]] = {
    "London,UK": (51.47, -0.20, 51.55, 0.05),
    "Dubai,UAE": (25.05, 55.10, 25.30, 55.35),
    "Manama,Bahrain": (26.18, 50.53, 26.25, 50.62),
    "New York,USA": (40.70, -74.02, 40.78, -73.93),
    "Sydney,Australia": (-33.90, 151.14, -33.83, 151.24),
    "Berlin,Europe": (52.47, 13.32, 52.57, 13.48),
}

# OSM tag filter -> industry label. Labels are worded to contain the exact
# target_industries phrases LeadScoringEngine._score_industry() matches on
# (real estate / healthcare / professional services / retail / consulting),
# so a genuinely-in-target-industry business is scored as one, not adjacent.
_CATEGORY_QUERIES: dict[str, str] = {
    'office="estate_agent"': "Real Estate Operations",
    'healthcare': "Healthcare Practice Operations",
    'office="lawyer"': "Professional Services Operations",
    'office="accountant"': "Professional Services Operations",
    'office="consulting"': "Consulting Operations",
    'shop="supermarket"': "Retail Operations",
}


class OSMLocalBusinessDiscovery:
    async def run(self, limit: int = 40) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for city, bbox in _CITY_BBOXES.items():
                if len(rows) >= limit:
                    break
                for tag_filter, industry_label in _CATEGORY_QUERIES.items():
                    if len(rows) >= limit:
                        break
                    rows.extend(await self._query_category(client, tag_filter, bbox, city, industry_label))
        return rows[:limit]

    async def _query_category(
        self,
        client: httpx.AsyncClient,
        tag_filter: str,
        bbox: tuple[float, float, float, float],
        city: str,
        industry_label: str,
    ) -> list[dict[str, Any]]:
        south, west, north, east = bbox
        filter_clause = f"[{tag_filter}]"
        query = f"""
        [out:json][timeout:20];
        (
          node{filter_clause}({south},{west},{north},{east});
          way{filter_clause}({south},{west},{north},{east});
        );
        out center 8;
        """
        try:
            response = await client.post(
                OVERPASS_URL,
                data={"data": query},
                headers={"User-Agent": "JARVIS-Aliyar-Solutions-lead-discovery"},
            )
            if response.status_code >= 400:
                logger.warning("OSM discovery HTTP %s for %s in %s", response.status_code, tag_filter, city)
                return []
            elements = response.json().get("elements", [])
        except Exception as exc:
            logger.warning("OSM discovery failed for %s in %s: %s", tag_filter, city, exc)
            return []

        city_name, country = city.split(",", 1)
        rows: list[dict[str, Any]] = []
        for el in elements:
            tags = el.get("tags", {}) or {}
            name = tags.get("name")
            if not name:
                continue
            website = tags.get("website") or tags.get("contact:website")
            phone = tags.get("phone") or tags.get("contact:phone")
            email = tags.get("email") or tags.get("contact:email")

            pain_points = []
            if not website:
                pain_points.append(
                    "no website on record — no automation or online presence for lead generation "
                    "(poor lead generation channel)"
                )
            if not phone and not email:
                pain_points.append("no public contact channel listed — likely manual processes, no tech team in place")
            if not pain_points:
                # Has a website and contact info — still genuinely small/local, but
                # don't claim a gap we have no evidence for.
                pain_points.append(f"real, mapped local {industry_label.lower()} business")

            rows.append(
                {
                    "company_name": name,
                    "industry": industry_label,
                    "country": country.strip(),
                    "source": "osm_local_business",
                    "pain_points": pain_points,
                    "website": website,
                    "email": email,
                    "phone": phone,
                    "notes": f"Real business mapped on OpenStreetMap in {city_name} — category: {tag_filter}.",
                    "enrichment_data": {
                        "osm_id": el.get("id"),
                        "osm_type": el.get("type"),
                        "category": tag_filter,
                        "city": city,
                        "has_website": bool(website),
                        "has_phone": bool(phone),
                        "has_email": bool(email),
                        "address": {
                            "street": tags.get("addr:street"),
                            "city": tags.get("addr:city") or city_name,
                        },
                    },
                }
            )
        return rows


osm_local_business_discovery = OSMLocalBusinessDiscovery()
