from __future__ import annotations

from importlib import import_module

from app.models.base import JarvisBase
from app.models.council import AICouncilMemberWeight, AICouncilSession
from app.models.intelligence import BriefingHistory, CompetitorProfile, MarketIntelligence, TechRadarEntry
from app.models.memory import CivilizationMemory, MemoryOperational, MemoryStrategic
from app.models.outreach import ReplyClassification, ReplyLog
from app.models.revenue import Client, Invoice, InvoiceStatus, RevenueSnapshot
from app.models.tenant import PlanTier, Tenant, TenantApiKey, User, UserRole


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
    "BriefingHistory",
    "CompetitorProfile",
    "MarketIntelligence",
    "TechRadarEntry",
    "CivilizationMemory",
    "MemoryOperational",
    "MemoryStrategic",
    "ReplyClassification",
    "ReplyLog",
    "Client",
    "Invoice",
    "InvoiceStatus",
    "RevenueSnapshot",
    "PlanTier",
    "Tenant",
    "TenantApiKey",
    "User",
    "UserRole",
    "register_models",
]
