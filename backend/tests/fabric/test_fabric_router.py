"""Tests for F3-3: FabricRouter — full pipeline, budget gate, verification."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.fabric.router import FabricRouter, FabricResponse
from app.services.ai.base_provider import AIResponse


def _make_ai_response(content="OK", error=None) -> AIResponse:
    return AIResponse(
        content=content,
        model="claude-sonnet",
        provider="anthropic",
        task_type="general",
        tokens_used=100,
        latency_ms=200,
        cost_estimate_usd=0.01,
        error=error,
    )


def _make_router() -> FabricRouter:
    router = FabricRouter()

    # Stub the AI router.
    mock_ai = AsyncMock()
    mock_ai.chat = AsyncMock(return_value=(_make_ai_response(), "general"))
    router._ai_router = mock_ai

    # Stub model registry.
    mock_reg = MagicMock()
    mock_reg.get_fallback_chain.return_value = [("anthropic", "claude-sonnet")]
    mock_reg.record_call = AsyncMock()
    router._registry = mock_reg

    # Stub token governor.
    mock_gov = MagicMock()
    mock_gov.is_rate_limited = AsyncMock(return_value=False)
    mock_gov.get_usage_pct = AsyncMock(return_value=0.10)
    mock_gov.record_usage = AsyncMock()
    router._governor = mock_gov

    # Stub response verifier (pass by default).
    from app.services.fabric.response_verifier import VerificationResult
    mock_verifier = MagicMock()
    mock_verifier.verify = AsyncMock(return_value=VerificationResult(
        passed=True, confidence=0.95, issues=[],
        requires_review=False, policy_compliant=True,
        hallucination_risk=0.0,
    ))
    router._verifier = mock_verifier

    return router


class TestChatBasic:
    @pytest.mark.asyncio
    async def test_returns_fabric_response(self):
        router = _make_router()
        result = await router.chat([{"role": "user", "content": "Hello"}])
        assert isinstance(result, FabricResponse)
        assert result.content == "OK"
        assert result.provider == "anthropic"

    @pytest.mark.asyncio
    async def test_task_type_normalised(self):
        router = _make_router()
        result = await router.chat([{"role": "user", "content": "q"}], task_type="CODE")
        assert result.task_type == "code"

    @pytest.mark.asyncio
    async def test_routing_trace_populated(self):
        router = _make_router()
        result = await router.chat([{"role": "user", "content": "q"}])
        assert len(result.routing_trace) > 0

    @pytest.mark.asyncio
    async def test_verification_runs_by_default(self):
        router = _make_router()
        result = await router.chat([{"role": "user", "content": "q"}])
        assert result.verification is not None
        assert result.passed_verification is True

    @pytest.mark.asyncio
    async def test_skip_verification(self):
        router = _make_router()
        result = await router.chat([{"role": "user", "content": "q"}], verify=False)
        assert result.verification is None
        assert result.passed_verification is True   # property defaults True when None


class TestBudgetGate:
    @pytest.mark.asyncio
    async def test_over_budget_uses_cheap_chain(self):
        router = _make_router()
        router._governor.get_usage_pct = AsyncMock(return_value=0.85)
        cheap_chain = [("nvidia", "llama-4-scout")]
        router._governor.get_cheap_fallback = AsyncMock(return_value=cheap_chain)

        result = await router.chat([{"role": "user", "content": "q"}])
        assert result.over_budget is True
        assert result.fallback_chain_used == cheap_chain

    @pytest.mark.asyncio
    async def test_rate_limited_flag(self):
        router = _make_router()
        router._governor.is_rate_limited = AsyncMock(return_value=True)

        result = await router.chat([{"role": "user", "content": "q"}])
        assert result.rate_limited is True


class TestAIRouterFailure:
    @pytest.mark.asyncio
    async def test_ai_failure_returns_error_response(self):
        router = _make_router()
        router._ai_router.chat = AsyncMock(side_effect=RuntimeError("provider down"))

        result = await router.chat([{"role": "user", "content": "q"}])
        assert result.error is not None
        assert result.content == ""

    @pytest.mark.asyncio
    async def test_verifier_error_is_non_fatal(self):
        router = _make_router()
        router._verifier.verify = AsyncMock(side_effect=Exception("verifier crash"))

        result = await router.chat([{"role": "user", "content": "q"}])
        # Response still returned; verification is None.
        assert result.content == "OK"
        assert result.verification is None


class TestRegistryIntegration:
    @pytest.mark.asyncio
    async def test_record_call_invoked_with_session(self):
        router = _make_router()
        mock_session = MagicMock()

        await router.chat([{"role": "user", "content": "q"}], db_session=mock_session)
        router._registry.record_call.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_record_call_skipped_without_session(self):
        router = _make_router()
        await router.chat([{"role": "user", "content": "q"}], db_session=None)
        router._registry.record_call.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_token_governor_always_records(self):
        router = _make_router()
        await router.chat([{"role": "user", "content": "q"}])
        router._governor.record_usage.assert_awaited_once()


class TestStatus:
    @pytest.mark.asyncio
    async def test_status_keys(self):
        router = _make_router()
        router._governor.status = AsyncMock(return_value={"spend_usd": 1.0})
        router._registry.snapshot.return_value = {}
        router._registry.list_active.return_value = []

        s = await router.status()
        assert "active_models" in s
        assert "budget" in s
        assert "model_registry" in s


class TestFabricResponseProperties:
    def test_passed_verification_no_verification(self):
        r = FabricResponse(content="x", model="m", provider="p", task_type="t")
        assert r.passed_verification is True

    def test_requires_review_no_verification(self):
        r = FabricResponse(content="x", model="m", provider="p", task_type="t")
        assert r.requires_review is False
