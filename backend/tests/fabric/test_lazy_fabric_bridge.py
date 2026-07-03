"""Tests for F3-7: _LazyFabricBridge — transparent ai_router shim."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.base_provider import AIResponse, TaskType
from app.services.ai.router import _LazyFabricBridge


def _make_ai_response(**kwargs) -> AIResponse:
    defaults = dict(
        content="fallback response",
        model="gpt-4o",
        provider="openai",
        task_type="general",
        tokens_used=50,
        latency_ms=100,
        cost_estimate_usd=0.005,
        error=None,
    )
    defaults.update(kwargs)
    return AIResponse(**defaults)


def _make_fallback():
    fallback = AsyncMock()
    fallback.chat = AsyncMock(return_value=(_make_ai_response(), "general"))
    fallback.available_providers = MagicMock(return_value=["openai"])
    fallback.operational_providers = MagicMock(return_value=["openai"])
    fallback.get_provider_status = MagicMock(return_value={"openai": "ok"})
    return fallback


def _make_fabric_response(**kwargs):
    """Minimal FabricResponse-like object (avoids circular import in tests)."""
    obj = MagicMock()
    obj.content = kwargs.get("content", "fabric response")
    obj.model = kwargs.get("model", "claude-sonnet")
    obj.provider = kwargs.get("provider", "anthropic")
    obj.task_type = kwargs.get("task_type", "general")
    obj.tokens_used = kwargs.get("tokens_used", 100)
    obj.latency_ms = kwargs.get("latency_ms", 200)
    obj.cost_estimate_usd = kwargs.get("cost_estimate_usd", 0.01)
    obj.error = kwargs.get("error", None)
    return obj


class TestBridgeFabricPath:
    @pytest.mark.asyncio
    async def test_delegates_to_fabric_when_available(self):
        fallback = _make_fallback()
        bridge = _LazyFabricBridge(fallback)

        fabric_mock = AsyncMock()
        fabric_mock.chat = AsyncMock(return_value=_make_fabric_response())
        bridge._fabric = fabric_mock

        response, task_type = await bridge.chat(
            [{"role": "user", "content": "hi"}], task_type="general"
        )
        fabric_mock.chat.assert_awaited_once()
        fallback.chat.assert_not_awaited()
        assert response.content == "fabric response"

    @pytest.mark.asyncio
    async def test_fabric_response_converted_to_ai_response(self):
        fallback = _make_fallback()
        bridge = _LazyFabricBridge(fallback)
        bridge._fabric = AsyncMock()
        bridge._fabric.chat = AsyncMock(return_value=_make_fabric_response(
            content="test", model="m", provider="p", task_type="code",
            tokens_used=42, latency_ms=99, cost_estimate_usd=0.07
        ))

        response, task_type = await bridge.chat([{"role": "user", "content": "q"}])
        assert isinstance(response, AIResponse)
        assert response.content == "test"
        assert response.model == "m"
        assert response.provider == "p"
        assert response.tokens_used == 42
        assert task_type == "code"


class TestBridgeFallback:
    @pytest.mark.asyncio
    async def test_uses_fallback_when_fabric_unavailable(self):
        fallback = _make_fallback()
        bridge = _LazyFabricBridge(fallback)
        # No _fabric set; _get_fabric will try to import but fail.
        with patch(
            "app.services.fabric.router.get_fabric_router",
            side_effect=ImportError("no fabric"),
        ):
            bridge._fabric = None
            # Force _get_fabric to run properly.
            original_get = bridge._get_fabric

            def patched_get():
                try:
                    from app.services.fabric.router import get_fabric_router
                    bridge._fabric = get_fabric_router()
                except Exception:
                    pass
                return bridge._fabric

            bridge._get_fabric = patched_get
            response, task_type = await bridge.chat([{"role": "user", "content": "q"}])

        fallback.chat.assert_awaited_once()
        assert response.content == "fallback response"

    @pytest.mark.asyncio
    async def test_fabric_error_falls_back_to_real_router(self):
        fallback = _make_fallback()
        bridge = _LazyFabricBridge(fallback)

        fabric_mock = AsyncMock()
        fabric_mock.chat = AsyncMock(side_effect=RuntimeError("fabric crash"))
        bridge._fabric = fabric_mock

        response, task_type = await bridge.chat([{"role": "user", "content": "q"}])
        fallback.chat.assert_awaited_once()
        assert response.content == "fallback response"


class TestBridgeDelegation:
    def test_available_providers_delegates(self):
        fallback = _make_fallback()
        bridge = _LazyFabricBridge(fallback)
        result = bridge.available_providers()
        fallback.available_providers.assert_called_once()
        assert result == ["openai"]

    def test_operational_providers_delegates(self):
        fallback = _make_fallback()
        bridge = _LazyFabricBridge(fallback)
        bridge.operational_providers()
        fallback.operational_providers.assert_called_once()

    def test_get_provider_status_delegates(self):
        fallback = _make_fallback()
        bridge = _LazyFabricBridge(fallback)
        bridge.get_provider_status()
        fallback.get_provider_status.assert_called_once()


class TestBridgeLazyLoad:
    def test_fabric_is_lazy(self):
        fallback = _make_fallback()
        bridge = _LazyFabricBridge(fallback)
        # Should not import fabric at construction time.
        assert bridge._fabric is None

    def test_get_fabric_caches_result(self):
        fallback = _make_fallback()
        bridge = _LazyFabricBridge(fallback)

        fake_fabric = MagicMock()
        with patch(
            "app.services.fabric.router.get_fabric_router",
            return_value=fake_fabric,
        ):
            first = bridge._get_fabric()
            second = bridge._get_fabric()

        assert first is second
        assert bridge._fabric is fake_fabric
