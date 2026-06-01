from __future__ import annotations

from importlib import import_module

from app.models.base import JarvisBase


MODEL_MODULES = (
    "tenant",
    "conversation",
    "approval",
    "crm",
    "lead",
    "outreach",
    "revenue",
    "memory",
    "tasks",
    "scheduling",
    "notifications",
    "intelligence",
    "governance",
    "knowledge",
    "service_catalog",
    "ai_audit",
    "team_member",
    "gmail",
)


def register_models() -> None:
    """Import every model module so JarvisBase.metadata is complete."""

    for module_name in MODEL_MODULES:
        import_module(f"app.models.{module_name}")
