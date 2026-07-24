"""Tests for the free, no-API-key OpenStreetMap local-business discovery
source — added because the only other free source (clearbit_autocomplete)
does keyword-substring matching against arbitrary company names and can
return a bank or a government agency for a query like "saas". This source
queries real, mapped local businesses instead, and derives pain-point
signals from real evidence (does OSM have a website/phone/email for this
business?) rather than repeating canned text on every lead.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.revenue_activation.osm_discovery import (
    OSMLocalBusinessDiscovery,
    _CATEGORY_QUERIES,
    _CITY_BBOXES,
)


def _overpass_response(elements):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"elements": elements}
    return resp


class TestQueryCategory:
    @pytest.mark.asyncio
    async def test_business_with_no_website_or_phone_gets_honest_pain_points(self):
        discovery = OSMLocalBusinessDiscovery()
        elements = [
            {
                "id": 123,
                "type": "node",
                "tags": {"name": "Corner Law Office", "addr:city": "London"},
            }
        ]
        client = MagicMock()
        client.post = AsyncMock(return_value=_overpass_response(elements))

        rows = await discovery._query_category(
            client, 'office="lawyer"', _CITY_BBOXES["London,UK"], "London,UK", "Professional Services Operations"
        )

        assert len(rows) == 1
        row = rows[0]
        assert row["company_name"] == "Corner Law Office"
        assert row["industry"] == "Professional Services Operations"
        assert row["country"] == "UK"
        assert row["source"] == "osm_local_business"
        # Must reuse the ICP's exact scoring vocabulary, not arbitrary wording.
        joined_pain = " ".join(row["pain_points"]).lower()
        assert "no automation" in joined_pain
        assert "no tech team" in joined_pain or "manual processes" in joined_pain
        assert row["website"] is None
        assert row["enrichment_data"]["has_website"] is False

    @pytest.mark.asyncio
    async def test_business_with_website_and_phone_does_not_claim_a_gap_it_has_no_evidence_for(self):
        discovery = OSMLocalBusinessDiscovery()
        elements = [
            {
                "id": 456,
                "type": "way",
                "tags": {
                    "name": "Riverside Estate Agents",
                    "website": "https://riverside-estates.example.com",
                    "phone": "+44 20 1234 5678",
                    "addr:city": "London",
                },
            }
        ]
        client = MagicMock()
        client.post = AsyncMock(return_value=_overpass_response(elements))

        rows = await discovery._query_category(
            client, 'office="estate_agent"', _CITY_BBOXES["London,UK"], "London,UK", "Real Estate Operations"
        )

        row = rows[0]
        assert row["website"] == "https://riverside-estates.example.com"
        assert row["phone"] == "+44 20 1234 5678"
        assert row["enrichment_data"]["has_website"] is True
        assert row["enrichment_data"]["has_phone"] is True
        joined_pain = " ".join(row["pain_points"]).lower()
        assert "no website" not in joined_pain
        assert "no public contact" not in joined_pain

    @pytest.mark.asyncio
    async def test_elements_without_a_name_are_skipped(self):
        discovery = OSMLocalBusinessDiscovery()
        elements = [{"id": 1, "type": "node", "tags": {}}]
        client = MagicMock()
        client.post = AsyncMock(return_value=_overpass_response(elements))

        rows = await discovery._query_category(
            client, 'office="lawyer"', _CITY_BBOXES["London,UK"], "London,UK", "Professional Services Operations"
        )
        assert rows == []

    @pytest.mark.asyncio
    async def test_http_error_returns_empty_list_not_an_exception(self):
        discovery = OSMLocalBusinessDiscovery()
        client = MagicMock()
        bad_response = MagicMock(status_code=500)
        client.post = AsyncMock(return_value=bad_response)

        rows = await discovery._query_category(
            client, 'office="lawyer"', _CITY_BBOXES["London,UK"], "London,UK", "Professional Services Operations"
        )
        assert rows == []

    @pytest.mark.asyncio
    async def test_network_failure_is_isolated(self):
        discovery = OSMLocalBusinessDiscovery()
        client = MagicMock()
        client.post = AsyncMock(side_effect=RuntimeError("connection refused"))

        rows = await discovery._query_category(
            client, 'office="lawyer"', _CITY_BBOXES["London,UK"], "London,UK", "Professional Services Operations"
        )
        assert rows == []


class TestIndustryAndCountryLabelsMatchICPVocabulary:
    """These labels feed directly into LeadScoringEngine's substring matching
    against ALIYAR_ICP — if the wording drifts, leads silently stop scoring
    well despite being genuinely on-target."""

    def test_industry_labels_contain_a_real_icp_target_industry_substring(self):
        from app.services.leads.scoring import ALIYAR_ICP

        for label in _CATEGORY_QUERIES.values():
            assert any(industry.lower() in label.lower() for industry in ALIYAR_ICP["target_industries"]), (
                f"Industry label {label!r} doesn't match any ALIYAR_ICP target_industries substring"
            )

    def test_city_country_suffixes_match_a_real_icp_target_country(self):
        from app.services.leads.scoring import ALIYAR_ICP

        for city_key in _CITY_BBOXES:
            country = city_key.split(",", 1)[1]
            assert any(target.lower() in country.lower() for target in ALIYAR_ICP["target_countries"]), (
                f"City entry {city_key!r}'s country doesn't match any ALIYAR_ICP target_countries"
            )


class TestRun:
    @pytest.mark.asyncio
    async def test_run_stops_once_limit_reached(self):
        discovery = OSMLocalBusinessDiscovery()
        many_elements = [{"id": i, "type": "node", "tags": {"name": f"Business {i}"}} for i in range(10)]

        with patch.object(discovery, "_query_category", new_callable=AsyncMock) as query_mock:
            query_mock.return_value = [
                {"company_name": f"Business {i}", "source": "osm_local_business", "pain_points": []}
                for i in range(10)
            ]
            rows = await discovery.run(limit=5)

        assert len(rows) == 5
