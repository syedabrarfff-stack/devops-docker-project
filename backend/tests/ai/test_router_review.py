"""
Tests for the AIRouter generate-then-review pipeline:
NVIDIA NIM / Google Gemini draft everything, OpenRouter Claude Opus 4.8
(falling back to direct Anthropic Claude Sonnet 4.6) reviews and refines it.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ai.base_provider import AIResponse, Message
from app.services.ai.router import AIRouter, _REVIEW_PROVIDERS


def _mock_provider(name: str, available: bool = True, response: AIResponse | None = None):
    provider = MagicMock()
    provider.name = name
    provider.is_available.return_value = available
    provider.models = {"model-a": "real-model-a"}
    if response is not None:
        provider.chat = AsyncMock(return_value=response)
    return provider


@pytest.fixture
def router():
    r = AIRouter.__new__(AIRouter)
    r._providers = {}
    return r


class TestReviewAndRefine:
    @pytest.mark.asyncio
    async def test_openrouter_reviews_the_draft(self, router):
        draft = AIResponse(content="draft answer", model="deepseek-v4-pro", provider="nvidia", task_type="general")
        reviewed = AIResponse(content="polished answer", model="claude-opus-4.8", provider="openrouter", task_type="general")
        router._providers = {
            "openrouter": _mock_provider("openrouter", response=reviewed),
            "anthropic": _mock_provider("anthropic", available=True),
        }

        result = await router._review_and_refine(draft, "what is 2+2?", max_tokens=2048)

        assert result.content == "polished answer"
        assert result.reviewed_by == "openrouter/claude-opus-4.8"
        assert result.draft_provider == "nvidia"

    @pytest.mark.asyncio
    async def test_falls_back_to_anthropic_when_openrouter_unavailable(self, router):
        draft = AIResponse(content="draft answer", model="gemini-pro", provider="google", task_type="general")
        reviewed = AIResponse(content="sonnet-polished answer", model="claude-sonnet-4-6", provider="anthropic", task_type="general")
        router._providers = {
            "openrouter": _mock_provider("openrouter", available=False),
            "anthropic": _mock_provider("anthropic", response=reviewed),
        }

        result = await router._review_and_refine(draft, "summarize this", max_tokens=2048)

        assert result.content == "sonnet-polished answer"
        assert result.reviewed_by == "anthropic/claude-sonnet-4-6"

    @pytest.mark.asyncio
    async def test_falls_back_to_anthropic_when_openrouter_errors(self, router):
        draft = AIResponse(content="draft answer", model="deepseek-v4-pro", provider="nvidia", task_type="general")
        failed = AIResponse(content="", model="claude-opus-4.8", provider="openrouter", task_type="general", error="rate_limited")
        reviewed = AIResponse(content="sonnet saved it", model="claude-sonnet-4-6", provider="anthropic", task_type="general")
        router._providers = {
            "openrouter": _mock_provider("openrouter", response=failed),
            "anthropic": _mock_provider("anthropic", response=reviewed),
        }

        result = await router._review_and_refine(draft, "prompt", max_tokens=2048)

        assert result.content == "sonnet saved it"
        assert result.reviewed_by == "anthropic/claude-sonnet-4-6"

    @pytest.mark.asyncio
    async def test_returns_original_draft_when_both_reviewers_fail(self, router):
        draft = AIResponse(content="original draft", model="deepseek-v4-pro", provider="nvidia", task_type="general")
        router._providers = {
            "openrouter": _mock_provider("openrouter", available=False),
            "anthropic": _mock_provider("anthropic", available=False),
        }

        result = await router._review_and_refine(draft, "prompt", max_tokens=2048)

        assert result.content == "original draft"
        assert result.reviewed_by is None

    @pytest.mark.asyncio
    async def test_returns_original_draft_when_no_reviewers_configured(self, router):
        draft = AIResponse(content="original draft", model="deepseek-v4-pro", provider="nvidia", task_type="general")
        router._providers = {}

        result = await router._review_and_refine(draft, "prompt", max_tokens=2048)

        assert result.content == "original draft"
        assert result.reviewed_by is None


class TestReviewProvidersExemption:
    def test_review_provider_set_excludes_the_review_layer_itself(self):
        # A draft from openrouter, anthropic, or bedrock must never be sent
        # back through review — those ARE the review layer.
        assert _REVIEW_PROVIDERS == {"openrouter", "anthropic", "bedrock"}
