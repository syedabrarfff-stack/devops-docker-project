"""Scout Network audit finding: the 9 scout agents made a real AI call per
scout, then discarded the raw JSON output entirely — never parsed, never
persisted. The scheduler job also read fields (total_leads, scout_summary,
github_push) that don't exist anywhere in the real return dict, silently
defaulting to zero every run. These tests lock in the real fix: parsing,
deduping, scoring, and inserting scout output as real leads.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.leads.scout_network import (
    ScoutNetwork,
    _parse_scout_output,
    _scout_lead_exists,
)


class TestParseScoutOutput:
    def test_parses_clean_json_array(self):
        raw = '[{"company": "Acme Corp", "website": "acme.com", "pain_point": "manual processes"}]'
        result = _parse_scout_output(raw)
        assert len(result) == 1
        assert result[0]["company"] == "Acme Corp"

    def test_tolerates_surrounding_prose(self):
        raw = 'Here are the companies:\n[{"company": "Beta Inc"}]\nHope this helps!'
        result = _parse_scout_output(raw)
        assert len(result) == 1
        assert result[0]["company"] == "Beta Inc"

    def test_drops_entries_without_a_company_name(self):
        raw = '[{"company": "Real Co"}, {"website": "noname.com"}]'
        result = _parse_scout_output(raw)
        assert len(result) == 1
        assert result[0]["company"] == "Real Co"

    def test_unparseable_output_returns_empty_list_not_an_exception(self):
        assert _parse_scout_output("not json at all, just prose") == []
        assert _parse_scout_output("") == []
        assert _parse_scout_output('{"not": "a list"}') == []


class TestScoutLeadExists:
    @pytest.mark.asyncio
    async def test_returns_true_when_company_name_matches(self):
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=uuid.uuid4())
        assert await _scout_lead_exists(session, uuid.uuid4(), "Acme Corp", None) is True

    @pytest.mark.asyncio
    async def test_returns_false_when_nothing_matches(self):
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=None)
        assert await _scout_lead_exists(session, uuid.uuid4(), "New Co", "new.com") is False


class TestInsertScoutLeads:
    @pytest.mark.asyncio
    async def test_inserts_parsed_companies_and_skips_duplicates(self):
        network = ScoutNetwork()
        tenant_uuid = uuid.uuid4()
        scout_result = {"scout_id": "alpha", "scout_name": "Alpha Scout", "specialty": "SaaS"}
        companies = [
            {"company": "Fresh Co", "website": "fresh.com", "country": "US", "industry": "SaaS", "pain_point": "no automation"},
            {"company": "Dup Co", "website": "dup.com"},
        ]

        fake_session = AsyncMock()

        class _NoopCtx:
            async def __aenter__(self):
                return None
            async def __aexit__(self, *a):
                return False
        fake_session.begin = MagicMock(return_value=_NoopCtx())
        # First company: not a duplicate. Second: duplicate.
        fake_session.scalar = AsyncMock(side_effect=[None, uuid.uuid4()])
        fake_session.add = MagicMock()
        fake_session.flush = AsyncMock()

        with (
            patch("app.services.leads.scout_network.AsyncSessionLocal") as db_ctx,
            patch("app.services.leads.scout_network.set_tenant_context", new_callable=AsyncMock),
            patch(
                "app.services.leads.scoring.lead_scoring_engine.score_against_icp",
                new_callable=AsyncMock,
                return_value=(72.0, {"total": 72.0}),
            ),
        ):
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=fake_session)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            inserted = await network._insert_scout_leads(tenant_uuid, scout_result, companies)

        assert inserted == 1
        # One real Lead + one AuditLog added for the non-duplicate company only.
        assert fake_session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_skips_companies_with_no_name(self):
        network = ScoutNetwork()
        fake_session = AsyncMock()

        class _NoopCtx:
            async def __aenter__(self):
                return None
            async def __aexit__(self, *a):
                return False
        fake_session.begin = MagicMock(return_value=_NoopCtx())

        with patch("app.services.leads.scout_network.AsyncSessionLocal") as db_ctx:
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=fake_session)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            inserted = await network._insert_scout_leads(uuid.uuid4(), {}, [{"website": "noname.com"}])

        assert inserted == 0


class TestRunAllScouts:
    @pytest.mark.asyncio
    async def test_reports_real_companies_found_and_inserted(self):
        network = ScoutNetwork()
        fake_scout_result = {
            "scout_id": "alpha",
            "scout_name": "Alpha Scout",
            "status": "success",
            "raw_output": '[{"company": "Acme"}, {"company": "Beta"}]',
        }

        with (
            patch.object(network, "run_scout", new_callable=AsyncMock, return_value=fake_scout_result),
            patch.object(network, "_insert_scout_leads", new_callable=AsyncMock, return_value=2),
        ):
            result = await network.run_all_scouts(tenant_id=str(uuid.uuid4()))

        assert result["scouts_run"] == 9
        assert result["successful"] == 9
        # 9 scouts each "finding" 2 companies via the mocked raw_output.
        assert result["companies_found"] == 18
        assert result["leads_inserted"] == 18
