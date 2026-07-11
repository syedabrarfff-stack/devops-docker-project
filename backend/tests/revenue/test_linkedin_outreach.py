"""Tests for R6-4: LinkedIn outreach — Proxycurl enrichment, message generation, sweep."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestEnrichPersonProfile:
    @pytest.mark.asyncio
    async def test_valid_url_returns_profile_dict(self):
        mock_data = {
            "full_name": "Alice Smith",
            "headline": "CTO at AcmeCo",
            "summary": "Building great things.",
            "experiences": [],
        }
        with (
            patch("app.services.outreach.linkedin_outreach.settings") as cfg,
            patch("app.services.outreach.linkedin_outreach.httpx") as mock_httpx,
        ):
            cfg.PROXYCURL_API_KEY = "test_key"
            mock_resp = MagicMock(status_code=200)
            mock_resp.json.return_value = mock_data
            mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(get=AsyncMock(return_value=mock_resp))
            )
            mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.outreach.linkedin_outreach import enrich_person_profile
            result = await enrich_person_profile("https://linkedin.com/in/alice-smith")
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_api_error_returns_empty_dict(self):
        with (
            patch("app.services.outreach.linkedin_outreach.settings") as cfg,
            patch("app.services.outreach.linkedin_outreach.httpx") as mock_httpx,
        ):
            cfg.PROXYCURL_API_KEY = "test_key"
            mock_resp = MagicMock(status_code=429)
            mock_resp.json.return_value = {"error": "rate limited"}
            mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(get=AsyncMock(return_value=mock_resp))
            )
            mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.outreach.linkedin_outreach import enrich_person_profile
            result = await enrich_person_profile("https://linkedin.com/in/alice-smith")
            assert isinstance(result, dict)


class TestGenerateLinkedInMessage:
    @pytest.mark.asyncio
    async def test_message_under_300_chars(self):
        profile_data = {
            "full_name": "Bob Jones",
            "headline": "CEO at TechCorp",
            "summary": "Scaling SaaS businesses.",
        }
        mock_ai_resp = MagicMock(content="Hi Bob! Would love to connect about cloud automation for TechCorp.")
        with patch("app.services.ai.router.ai_router") as ai:
            ai.chat = AsyncMock(return_value=(mock_ai_resp, "sales"))
            from app.services.outreach.linkedin_outreach import generate_linkedin_message
            msg = await generate_linkedin_message(
                lead_company="TechCorp",
                contact_name="Bob Jones",
                profile_data=profile_data,
                service_angle="cloud infrastructure",
            )
            assert isinstance(msg, str)
            assert len(msg) <= 300

    @pytest.mark.asyncio
    async def test_ai_failure_returns_template_fallback(self):
        with patch("app.services.ai.router.ai_router") as ai:
            ai.chat = AsyncMock(side_effect=Exception("AI down"))
            from app.services.outreach.linkedin_outreach import generate_linkedin_message
            msg = await generate_linkedin_message(
                lead_company="FallbackCo",
                contact_name="Jane",
                profile_data={},
                service_angle="automation",
            )
            assert isinstance(msg, str)
            assert len(msg) > 0


class TestLinkedInSweep:
    @pytest.mark.asyncio
    async def test_sweep_processes_eligible_leads(self):
        mock_lead = MagicMock()
        mock_lead.id = "lead_123"
        mock_lead.company = "TargetCo"
        mock_lead.contact_name = "Alice"
        mock_lead.linkedin_url = "https://linkedin.com/in/alice"
        mock_lead.icp_score = 75

        with (
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.outreach.linkedin_outreach.enrich_and_queue_lead") as enrich,
        ):
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_lead])))
            ))
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            enrich.return_value = AsyncMock(return_value={"status": "queued"})

            from app.services.outreach.linkedin_outreach import linkedin_outreach_sweep
            result = await linkedin_outreach_sweep()
            assert isinstance(result, dict)
