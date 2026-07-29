"""Tests for F3-4: TokenGovernor — budget management, rate limiting."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.fabric.token_governor import TokenGovernor, _current_month


def make_governor() -> TokenGovernor:
    return TokenGovernor()


class TestRecordUsage:
    @pytest.mark.asyncio
    async def test_records_spend(self):
        gov = make_governor()
        await gov.record_usage("anthropic", "claude-sonnet", 1000, 0.05)
        spend = await gov.get_monthly_spend()
        assert spend == pytest.approx(0.05)

    @pytest.mark.asyncio
    async def test_per_provider_spend(self):
        gov = make_governor()
        await gov.record_usage("anthropic", "claude-sonnet", 500, 0.10)
        await gov.record_usage("openai", "gpt-4o", 500, 0.20)
        assert await gov.get_monthly_spend("anthropic") == pytest.approx(0.10)
        assert await gov.get_monthly_spend("openai") == pytest.approx(0.20)
        assert await gov.get_monthly_spend() == pytest.approx(0.30)

    @pytest.mark.asyncio
    async def test_returns_true_within_budget(self):
        gov = make_governor()
        result = await gov.record_usage("anthropic", "claude", 100, 1.00)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_over_budget(self):
        gov = make_governor()
        # Default budget is 100.0 USD; spend way over it.
        gov._monthly[_current_month()]["anthropic"] = 200.0
        result = await gov.record_usage("anthropic", "claude", 100, 1.00)
        assert result is False


class TestUsagePct:
    @pytest.mark.asyncio
    async def test_zero_initially(self):
        gov = make_governor()
        pct = await gov.get_usage_pct()
        assert pct == 0.0

    @pytest.mark.asyncio
    async def test_pct_at_half_budget(self):
        gov = make_governor()
        # Mock budget = 100.0 default; spend 50.
        gov._monthly[_current_month()]["anthropic"] = 50.0
        pct = await gov.get_usage_pct()
        assert pct == pytest.approx(0.50)


class TestRateLimit:
    @pytest.mark.asyncio
    async def test_not_rate_limited_initially(self):
        gov = make_governor()
        assert await gov.is_rate_limited() is False

    @pytest.mark.asyncio
    async def test_rate_limited_when_bucket_full(self):
        gov = make_governor()
        from app.services.fabric.token_governor import _current_minute
        minute = _current_minute()
        gov._rate_buckets[minute] = 120   # default limit
        assert await gov.is_rate_limited() is True

    @pytest.mark.asyncio
    async def test_not_limited_when_zero_limit(self):
        gov = make_governor()
        from app.services.fabric.token_governor import _current_minute
        minute = _current_minute()
        gov._rate_buckets[minute] = 9999
        # Patch rate limit to 0 = unlimited.
        with patch.object(gov, "_get_rate_limit", new=AsyncMock(return_value=0)):
            assert await gov.is_rate_limited() is False


class TestCheapFallback:
    @pytest.mark.asyncio
    async def test_returns_chain(self):
        gov = make_governor()
        chain = await gov.get_cheap_fallback("general")
        assert len(chain) > 0
        assert all(isinstance(p, str) and isinstance(m, str) for p, m in chain)

    @pytest.mark.asyncio
    async def test_excludes_over_quota_provider(self):
        gov = make_governor()
        # Put nvidia over its quota.
        with patch.object(gov, "is_over_quota", new=AsyncMock(side_effect=lambda p: p == "nvidia")):
            chain = await gov.get_cheap_fallback("general")
        providers = {p for p, _ in chain}
        assert "nvidia" not in providers or len(chain) == 0

    @pytest.mark.asyncio
    async def test_always_returns_something_even_all_over_quota(self):
        gov = make_governor()
        with patch.object(gov, "is_over_quota", new=AsyncMock(return_value=True)):
            chain = await gov.get_cheap_fallback("general")
        assert len(chain) > 0


class TestBudgetAlert:
    @pytest.mark.asyncio
    async def test_alert_fired_at_80_pct(self):
        gov = make_governor()
        gov._monthly[_current_month()]["test"] = 79.99
        with patch.object(gov, "_emit_budget_alert", new=AsyncMock()) as mock_alert:
            # Push over 80%.
            await gov.record_usage("test", "model", 0, 0.02)
            mock_alert.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_alert_not_repeated_same_month(self):
        gov = make_governor()
        gov._monthly[_current_month()]["test"] = 90.0
        gov._alert_sent_month = _current_month()
        with patch.object(gov, "_emit_budget_alert", new=AsyncMock()) as mock_alert:
            await gov.record_usage("test", "model", 0, 1.0)
            mock_alert.assert_not_awaited()


class TestStatus:
    @pytest.mark.asyncio
    async def test_status_keys(self):
        gov = make_governor()
        s = await gov.status()
        assert "spend_usd" in s
        assert "budget_usd" in s
        assert "usage_pct" in s
        assert "rate_limit_per_min" in s
