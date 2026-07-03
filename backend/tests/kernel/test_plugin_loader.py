"""Tests for K2-4: PluginLoader — manifest registration and load lifecycle."""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.kernel.plugin_loader import PluginLoader, PluginManifest

# The _load() and unload() methods do lazy imports, so we patch the source module
# functions (not the plugin_loader module attributes).
BUS_PATH  = "app.services.kernel.event_bus.get_event_bus"
DISC_PATH = "app.services.kernel.service_discovery.get_service_discovery"


def _mock_bus():
    return MagicMock(return_value=AsyncMock(emit=AsyncMock()))


def _mock_disc_reg():
    return MagicMock(return_value=AsyncMock(register=AsyncMock()))


def _mock_disc_dereg():
    return MagicMock(return_value=AsyncMock(deregister=AsyncMock()))


class TestRegistration:
    @pytest.mark.asyncio
    async def test_register_no_module(self):
        """A manifest without module_path registers but does nothing on load."""
        loader = PluginLoader()
        manifest = PluginManifest(name="stub", auto_start=False)
        rec = await loader.register_manifest(manifest)
        assert rec.manifest.name == "stub"
        assert "stub" in loader.list_all()

    @pytest.mark.asyncio
    async def test_register_idempotent_no_force(self):
        loader = PluginLoader()
        m = PluginManifest(name="eng", auto_start=False)
        r1 = await loader.register_manifest(m)
        r2 = await loader.register_manifest(m)
        assert r1 is r2   # same record returned

    @pytest.mark.asyncio
    async def test_register_force_reload(self):
        loader = PluginLoader()
        m1 = PluginManifest(name="eng", version="1.0", auto_start=False)
        m2 = PluginManifest(name="eng", version="2.0", auto_start=False)
        await loader.register_manifest(m1)
        await loader.register_manifest(m2, force_reload=True)
        rec = loader.get_record("eng")
        assert rec.manifest.version == "2.0"

    @pytest.mark.asyncio
    async def test_unload_removes_entry(self):
        loader = PluginLoader()
        m = PluginManifest(name="eng", auto_start=False)
        await loader.register_manifest(m)
        with patch(BUS_PATH, new=_mock_bus()):
            with patch(DISC_PATH, new=_mock_disc_dereg()):
                removed = await loader.unload("eng")
        assert removed is True
        assert "eng" not in loader.list_all()

    @pytest.mark.asyncio
    async def test_unload_nonexistent_returns_false(self):
        loader = PluginLoader()
        assert await loader.unload("ghost") is False


class TestLoad:
    @pytest.mark.asyncio
    async def test_load_stdlib_module(self):
        """Loading a standard library module (no factory) should succeed."""
        loader = PluginLoader()
        m = PluginManifest(name="json_mod", module_path="json", auto_start=True)

        with patch(BUS_PATH, new=_mock_bus()):
            with patch(DISC_PATH, new=_mock_disc_reg()):
                await loader.register_manifest(m)

        rec = loader.get_record("json_mod")
        assert rec.loaded is True
        assert rec.error is None

    @pytest.mark.asyncio
    async def test_load_bad_module_records_error(self):
        loader = PluginLoader()
        m = PluginManifest(name="broken", module_path="does.not.exist.anywhere", auto_start=True)

        with patch(BUS_PATH, new=_mock_bus()):
            with patch(DISC_PATH, new=_mock_disc_reg()):
                await loader.register_manifest(m)

        rec = loader.get_record("broken")
        assert rec.loaded is False
        assert rec.error is not None

    @pytest.mark.asyncio
    async def test_list_loaded_excludes_failed(self):
        loader = PluginLoader()
        good = PluginManifest(name="good", module_path="json", auto_start=True)
        bad  = PluginManifest(name="bad",  module_path="no.such.thing", auto_start=True)

        for m in (good, bad):
            with patch(BUS_PATH, new=_mock_bus()):
                with patch(DISC_PATH, new=_mock_disc_reg()):
                    await loader.register_manifest(m)

        loaded = loader.list_loaded()
        assert "good" in loaded
        assert "bad" not in loaded

    @pytest.mark.asyncio
    async def test_get_instance_returns_none_when_failed(self):
        loader = PluginLoader()
        m = PluginManifest(name="fail", module_path="nope", auto_start=True)
        with patch(BUS_PATH, new=_mock_bus()):
            with patch(DISC_PATH, new=_mock_disc_reg()):
                await loader.register_manifest(m)
        assert loader.get_instance("fail") is None


class TestSnapshot:
    @pytest.mark.asyncio
    async def test_snapshot_includes_all_plugins(self):
        loader = PluginLoader()
        for name in ("a", "b", "c"):
            m = PluginManifest(name=name, version="1.0", auto_start=False)
            await loader.register_manifest(m)
        snap = loader.snapshot()
        assert set(snap.keys()) == {"a", "b", "c"}
