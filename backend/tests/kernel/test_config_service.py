"""Tests for K2-1: ConfigService — feature flags, hot-reload, defaults."""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.kernel.config_service import ConfigService, _DEFAULTS


def make_service():
    """ConfigService backed by a factory that returns a mock session."""
    factory = MagicMock()  # session_factory (not async itself)
    svc = ConfigService(factory)
    return svc


class TestDefaults:
    @pytest.mark.asyncio
    async def test_get_missing_key_returns_default(self):
        svc = make_service()
        # Seed the cache directly — avoids real DB.
        svc._cache = {}
        svc._cache_loaded_at = 1.0
        result = await svc.get("nonexistent.key", default="fallback")
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_builtin_defaults_returned(self):
        svc = make_service()
        svc._cache = dict(_DEFAULTS)
        svc._cache_loaded_at = 1.0
        val = await svc.get("feature.failover_auto_switch")
        assert val is False

    @pytest.mark.asyncio
    async def test_get_bool_coerces(self):
        svc = make_service()
        svc._cache = {"x": 1}
        svc._cache_loaded_at = 1.0
        assert await svc.get_bool("x") is True

    @pytest.mark.asyncio
    async def test_get_float_coerces(self):
        svc = make_service()
        svc._cache = {"x": "3.14"}
        svc._cache_loaded_at = 1.0
        assert await svc.get_float("x") == pytest.approx(3.14)

    @pytest.mark.asyncio
    async def test_get_int_coerces(self):
        svc = make_service()
        svc._cache = {"x": 9.9}
        svc._cache_loaded_at = 1.0
        assert await svc.get_int("x") == 9


class TestCacheUpdate:
    @pytest.mark.asyncio
    async def test_set_updates_cache_immediately(self):
        svc = make_service()
        svc._cache = {}
        svc._cache_loaded_at = 1.0

        # Patch factory to return a session context manager.
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        svc._factory = MagicMock(return_value=mock_session)

        await svc.set("feature.new_flag", True, updated_by="captain")
        assert svc._cache["feature.new_flag"] is True

    @pytest.mark.asyncio
    async def test_delete_removes_from_cache(self):
        svc = make_service()
        svc._cache = {"old.key": 42}
        svc._cache_loaded_at = 1.0

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        svc._factory = MagicMock(return_value=mock_session)

        deleted = await svc.delete("old.key")
        assert deleted is True
        assert "old.key" not in svc._cache

    @pytest.mark.asyncio
    async def test_delete_returns_false_if_missing(self):
        svc = make_service()
        svc._cache = {}
        svc._cache_loaded_at = 1.0

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        svc._factory = MagicMock(return_value=mock_session)

        assert await svc.delete("does.not.exist") is False


class TestReload:
    @pytest.mark.asyncio
    async def test_reload_merges_defaults_with_db(self):
        svc = make_service()

        row1 = MagicMock()
        row1.key = "custom.flag"
        row1.value = {"v": True}

        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[row1])
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(return_value=mock_result)
        svc._factory = MagicMock(return_value=mock_session)

        count = await svc.reload()
        assert count == 1
        assert svc._cache["custom.flag"] is True
        # Built-in defaults still present
        assert "feature.failover_auto_switch" in svc._cache

    @pytest.mark.asyncio
    async def test_get_all_returns_full_cache(self):
        svc = make_service()
        svc._cache = {"a": 1, "b": 2}
        svc._cache_loaded_at = 1.0
        result = await svc.get_all()
        assert result == {"a": 1, "b": 2}
        # Must be a copy, not the live dict
        result["c"] = 3
        assert "c" not in svc._cache
