"""K2-4: Plugin Loader — engine manifests and dynamic registration.

Engines are pluggable modules. Each engine ships with a PluginManifest that
declares its name, version, capabilities, and an optional factory callable.
The Plugin Loader:
  1. Accepts manifest registration (static or dynamic)
  2. Loads the engine module (importlib) and calls the factory if provided
  3. Registers the engine with ServiceDiscovery
  4. Publishes a 'plugin.loaded' / 'plugin.unloaded' event

Adding a new engine (#6, #7, …) requires only:
  - Creating the service module
  - Calling plugin_loader.register_manifest(PluginManifest(...))
  - No changes to any core file

Usage:
    loader = get_plugin_loader()
    await loader.register_manifest(PluginManifest(
        name="budget_engine",
        version="1.0.0",
        module_path="app.services.budget.engine",
        factory="create_engine",
        capabilities=["budget", "forecasting"],
    ))
    instance = loader.get_instance("budget_engine")
"""
from __future__ import annotations

import asyncio
import importlib
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)

_loader: Optional["PluginLoader"] = None


@dataclass
class PluginManifest:
    """Declarative descriptor for a pluggable JARVIS engine."""
    name: str
    version: str = "1.0.0"
    module_path: Optional[str] = None      # dotted import path, e.g. "app.services.ai.router"
    factory: Optional[str] = None          # callable name inside the module, e.g. "create_engine"
    capabilities: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    auto_start: bool = True                # call factory immediately on register


@dataclass
class PluginRecord:
    manifest: PluginManifest
    instance: Any = None
    loaded: bool = False
    error: Optional[str] = None


class PluginLoader:
    """Manage pluggable engine lifecycle: register → load → unload.

    Instances are kept in memory by name. Load is idempotent — re-registering
    an already-loaded manifest is a no-op unless `force_reload=True`.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, PluginRecord] = {}
        self._lock = asyncio.Lock()

    # ── Registration ──────────────────────────────────────────────────────

    async def register_manifest(
        self,
        manifest: PluginManifest,
        force_reload: bool = False,
    ) -> PluginRecord:
        """Register *manifest* and optionally load the engine immediately."""
        async with self._lock:
            if manifest.name in self._plugins and not force_reload:
                existing = self._plugins[manifest.name]
                log.debug("plugin_loader.skip name=%s (already loaded)", manifest.name)
                return existing
            record = PluginRecord(manifest=manifest)
            self._plugins[manifest.name] = record

        if manifest.auto_start:
            await self._load(manifest.name)

        return self._plugins[manifest.name]

    async def unload(self, name: str) -> bool:
        """Unload a plugin and deregister from ServiceDiscovery. Returns True if existed."""
        async with self._lock:
            if name not in self._plugins:
                return False
            record = self._plugins.pop(name)

        try:
            from app.services.kernel.event_bus import get_event_bus
            bus = get_event_bus()
            await bus.emit(
                "plugin.unloaded",
                payload={"name": name, "version": record.manifest.version},
                source_engine="plugin_loader",
            )
        except Exception:
            log.debug("plugin_loader.unload: event bus unavailable")

        try:
            from app.services.kernel.service_discovery import get_service_discovery
            await get_service_discovery().deregister(name)
        except Exception:
            log.debug("plugin_loader.unload: service_discovery unavailable")

        log.info("plugin_loader.unload name=%s", name)
        return True

    # ── Queries ───────────────────────────────────────────────────────────

    def get_instance(self, name: str) -> Optional[Any]:
        """Return the live engine instance, or None if not loaded."""
        rec = self._plugins.get(name)
        return rec.instance if rec and rec.loaded else None

    def get_record(self, name: str) -> Optional[PluginRecord]:
        return self._plugins.get(name)

    def list_loaded(self) -> list[str]:
        return [n for n, r in self._plugins.items() if r.loaded]

    def list_all(self) -> list[str]:
        return list(self._plugins.keys())

    def snapshot(self) -> dict[str, dict]:
        return {
            name: {
                "version": rec.manifest.version,
                "loaded": rec.loaded,
                "capabilities": rec.manifest.capabilities,
                "error": rec.error,
                "metadata": rec.manifest.metadata,
            }
            for name, rec in self._plugins.items()
        }

    # ── Internal ──────────────────────────────────────────────────────────

    async def _load(self, name: str) -> None:
        """Import module, call factory, register with ServiceDiscovery."""
        async with self._lock:
            record = self._plugins.get(name)
            if record is None:
                return

        manifest = record.manifest
        instance = None
        error = None

        try:
            if manifest.module_path:
                module = importlib.import_module(manifest.module_path)
                if manifest.factory:
                    factory_fn: Callable = getattr(module, manifest.factory)
                    if asyncio.iscoroutinefunction(factory_fn):
                        instance = await factory_fn()
                    else:
                        instance = factory_fn()
                else:
                    instance = module
            log.info(
                "plugin_loader.loaded name=%s version=%s capabilities=%s",
                manifest.name, manifest.version, manifest.capabilities,
            )
        except Exception as exc:
            error = str(exc)
            log.error("plugin_loader.load_error name=%s error=%s", manifest.name, error)

        async with self._lock:
            if name in self._plugins:
                self._plugins[name].instance = instance
                self._plugins[name].loaded = error is None
                self._plugins[name].error = error

        # Register with ServiceDiscovery regardless of load success
        try:
            from app.services.kernel.service_discovery import get_service_discovery
            disc = get_service_discovery()
            await disc.register(
                name=manifest.name,
                version=manifest.version,
                capabilities=manifest.capabilities,
                metadata={**manifest.metadata, "load_error": error},
            )
        except Exception:
            log.debug("plugin_loader: service_discovery unavailable during load")

        # Publish event
        try:
            from app.services.kernel.event_bus import get_event_bus
            bus = get_event_bus()
            await bus.emit(
                "plugin.loaded" if error is None else "plugin.load_failed",
                payload={
                    "name": manifest.name,
                    "version": manifest.version,
                    "capabilities": manifest.capabilities,
                    "error": error,
                },
                source_engine="plugin_loader",
            )
        except Exception:
            log.debug("plugin_loader: event bus unavailable during load")


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_plugin_loader() -> PluginLoader:
    global _loader
    if _loader is None:
        _loader = PluginLoader()
    return _loader
