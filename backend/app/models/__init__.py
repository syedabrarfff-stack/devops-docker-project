from __future__ import annotations

from importlib import import_module

from app.models.base import JarvisBase
from app.models.council import AICouncilMemberWeight, AICouncilSession
from app.models.memory import CivilizationMemory, MemoryOperational, MemoryStrategic
from app.models.outreach import ReplyClassification, ReplyLog
from app.models.revenue import Client, Invoice, InvoiceStatus, RevenueSnapshot


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
    "council",
)


def register_models() -> None:
    """Import every model module so JarvisBase.metadata is complete."""

    for module_name in MODEL_MODULES:
        import_module(f"app.models.{module_name}")


__all__ = [
    "JarvisBase",
    "AICouncilMemberWeight",
    "AICouncilSession",
    "CivilizationMemory",
    "MemoryOperational",
    "MemoryStrategic",
    "ReplyClassification",
    "ReplyLog",
    "Client",
    "Invoice",
    "InvoiceStatus",
    "RevenueSnapshot",
    "register_models",
]
