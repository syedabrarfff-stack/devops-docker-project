from __future__ import annotations

from importlib import import_module

from app.models.base import JarvisBase
from app.models.council import AICouncilMemberWeight, AICouncilSession
from app.models.compliance import DoNotContact, OutreachPauseState, ProcessedWebhook
from app.models.demo import DemoPackage
from app.models.economics import AICostLedger, InfrastructureCostConfig
from app.models.intelligence import BriefingHistory, CompetitorProfile, MarketIntelligence, TechRadarEntry
from app.models.innovation import InnovationQueueItem, InnovationStatus
from app.models.civilization import CivilizationLedger
from app.models.revenue_activation import MarketPulseItem, OutreachLearning, SpeedToLeadEvent
from app.models.captain_intelligence import (
    CaptainBrainDump,
    CaptainEmailIntelligence,
    CaptainPushback,
    PredictedAction,
)
from app.models.connector_hub import ConnectorHubIngestion, ConnectorHubPackage
from app.models.communication import (
    CommunicationChannel,
    CommunicationChannelStatus,
    CommunicationDirection,
    CommunicationEvent,
)
from app.models.aionx_organs import (
    DecisionObject,
    DecisionOption,
    DecisionOutcome,
    DecisionPattern,
    DecisionRetrospective,
    CounterfactualSimulation,
    CounterfactualActualization,
    DecisionDebtAssessment,
    InstitutionalDebtIndex,
    ClientDigitalTwin,
    ClientTwinInteraction,
    ClientTwinPrediction,
    ClientPipelineState,
    ClientPipelineMilestone,
    ClientPipelineStageLog,
    WisdomIndexSnapshot,
    ProviderCalibrationRecord,
    ProviderCouncilSession,
    ShelvedDiscovery,
    ConvergenceCouncilSession,
    ConvergenceCouncilMessage,
    MissionAutopsy,
    SentinelObservation,
    SentinelThreat,
    MissionOwnershipRecord,
    SelfModificationRecord,
)
from app.models.department_intelligence import (
    ClientCallIntelligence,
    DepartmentIntelligenceOfficer,
    DepartmentMilestone,
    StrategyReport,
    TechnologyDiscovery,
)
from app.models.memory import (
    CivilizationMemory,
    MemoryGraphEdge,
    MemoryGraphNode,
    MemoryOperational,
    MemoryStrategic,
)
from app.models.outreach import ReplyClassification, ReplyLog
from app.models.revenue import Client, Invoice, InvoiceStatus, RevenueSnapshot
from app.models.tenant import PlanTier, Tenant, TenantApiKey, User, UserRole
from app.models.approval import ApprovalRequest, ApprovalStatus, AuditLog
from app.models.conversation import Conversation
from app.models.crm import Company, Contact, Deal
from app.models.lead import Lead, LeadStatus
from app.models.tasks import AgentMessage, AgentTask
from app.models.scheduling import JobFailure, ScheduledJob
from app.models.notifications import NotificationLog
from app.models.governance import AgentPermission, Contract, ContractTemplate, IncidentReport, Proposal
from app.models.knowledge import KnowledgeBase, LearningRecord, SOPDocument
from app.models.service_catalog import ServiceDivision
from app.models.ai_audit import AIRequestLog
from app.models.team_member import TeamMember
from app.models.gmail import GmailMessage
from app.models.credentials import OAuthToken, SecureCredential
from app.models.trust_engine import ExecutiveOpportunityBrief, LeadEngagementEvent, ReferralRequest


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
    "department_intelligence",
    "demo",
    "economics",
    "innovation",
    "civilization",
    "revenue_activation",
    "compliance",
    "captain_intelligence",
    "connector_hub",
    "communication",
    "aionx_organs",
    "credentials",
    "trust_engine",
)


def register_models() -> None:
    """Import every model module so JarvisBase.metadata is complete."""

    for module_name in MODEL_MODULES:
        import_module(f"app.models.{module_name}")


__all__ = [
    "JarvisBase",
    "AICouncilMemberWeight",
    "AICouncilSession",
    "DoNotContact",
    "OutreachPauseState",
    "ProcessedWebhook",
    "DemoPackage",
    "AICostLedger",
    "InfrastructureCostConfig",
    "InnovationQueueItem",
    "InnovationStatus",
    "CivilizationLedger",
    "MarketPulseItem",
    "OutreachLearning",
    "SpeedToLeadEvent",
    "BriefingHistory",
    "CompetitorProfile",
    "MarketIntelligence",
    "TechRadarEntry",
    "CivilizationMemory",
    "MemoryGraphEdge",
    "MemoryGraphNode",
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
    "CaptainBrainDump",
    "CaptainEmailIntelligence",
    "CaptainPushback",
    "PredictedAction",
    "ConnectorHubIngestion",
    "ConnectorHubPackage",
    "CommunicationChannel",
    "CommunicationChannelStatus",
    "CommunicationDirection",
    "CommunicationEvent",
    "ClientPipelineState",
    "ClientPipelineMilestone",
    "ClientPipelineStageLog",
    "ClientCallIntelligence",
    "DepartmentIntelligenceOfficer",
    "DepartmentMilestone",
    "StrategyReport",
    "TechnologyDiscovery",
    "ApprovalRequest",
    "ApprovalStatus",
    "AuditLog",
    "Conversation",
    "Company",
    "Contact",
    "Deal",
    "Lead",
    "LeadStatus",
    "AgentMessage",
    "AgentTask",
    "JobFailure",
    "ScheduledJob",
    "NotificationLog",
    "AgentPermission",
    "Contract",
    "ContractTemplate",
    "IncidentReport",
    "Proposal",
    "KnowledgeBase",
    "LearningRecord",
    "SOPDocument",
    "ServiceDivision",
    "AIRequestLog",
    "TeamMember",
    "GmailMessage",
    "OAuthToken",
    "SecureCredential",
    "ExecutiveOpportunityBrief",
    "LeadEngagementEvent",
    "ReferralRequest",
]
