"""
SOP Systematization — Standard Operating Procedures for JARVIS
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict
from datetime import datetime


class ProcedureCategory(str, Enum):
    EMERGENCY = "emergency"
    DEPLOYMENT = "deployment"
    INCIDENT_RESPONSE = "incident_response"
    CLIENT_ONBOARDING = "client_onboarding"
    REVENUE_ACTIVATION = "revenue_activation"
    DISASTER_RECOVERY = "disaster_recovery"


@dataclass
class Procedure:
    id: str
    category: ProcedureCategory
    title: str
    description: str
    steps: List[str]
    owner: str
    severity: str
    estimated_minutes: int


# Critical Procedures

EMERGENCY_SHUTDOWN = Procedure(
    id="emergency_001",
    category=ProcedureCategory.EMERGENCY,
    title="Emergency System Shutdown",
    description="Graceful shutdown in case of critical threat",
    steps=[
        "1. Notify Captain immediately",
        "2. Stop all API calls",
        "3. Disable scheduled jobs",
        "4. Drain active connections (30s max)",
        "5. Stop services in reverse dependency order",
        "6. Log all state to audit database",
        "7. Wait for Captain approval to restart",
    ],
    owner="JARVIS",
    severity="critical",
    estimated_minutes=5,
)

REGIONAL_FAILOVER = Procedure(
    id="emergency_002",
    category=ProcedureCategory.EMERGENCY,
    title="Regional Failover (ap-south-2 → ap-south-1)",
    description="Automatic failover to backup region",
    steps=[
        "1. Detect primary failure (health timeout 3x)",
        "2. Trigger DNS failover (Route53)",
        "3. Promote read replicas in backup region",
        "4. Validate data sync lag",
        "5. Drain pending transactions",
        "6. Notify all stakeholders",
        "7. Begin primary region recovery",
    ],
    owner="Infrastructure",
    severity="critical",
    estimated_minutes=10,
)

BLUE_GREEN_DEPLOY = Procedure(
    id="deploy_001",
    category=ProcedureCategory.DEPLOYMENT,
    title="Blue-Green Zero-Downtime Deploy",
    description="Safe deployment with automatic rollback",
    steps=[
        "1. Build Docker images (backend + frontend)",
        "2. Run automated tests",
        "3. Deploy green environment (parallel)",
        "4. Run smoke tests on green",
        "5. Shift traffic gradually (5% → 25% → 50% → 100%)",
        "6. Monitor green for 5 minutes",
        "7. Rollback to blue if failures detected",
        "8. Tear down blue after 1 hour",
    ],
    owner="DevOps",
    severity="high",
    estimated_minutes=20,
)

DATABASE_MIGRATION = Procedure(
    id="deploy_002",
    category=ProcedureCategory.DEPLOYMENT,
    title="Safe Database Migration",
    description="Execute Alembic migrations with safety",
    steps=[
        "1. Create database backup",
        "2. Test migration in staging",
        "3. Validate data integrity",
        "4. Schedule off-peak window",
        "5. Run migration with transaction lock",
        "6. Verify data consistency",
        "7. Test rollback capability",
        "8. Commit or rollback based on results",
    ],
    owner="Database",
    severity="critical",
    estimated_minutes=30,
)

SECURITY_BREACH_RESPONSE = Procedure(
    id="incident_001",
    category=ProcedureCategory.INCIDENT_RESPONSE,
    title="Security Breach Response",
    description="Immediate action on security incident",
    steps=[
        "1. Isolate affected systems immediately",
        "2. Notify Captain + Security team",
        "3. Preserve all logs and evidence",
        "4. Activate incident response team",
        "5. Assess scope (data, users affected)",
        "6. Identify and patch attack vector",
        "7. Notify affected clients (legal compliance)",
        "8. Complete post-mortem within 24h",
    ],
    owner="Security",
    severity="critical",
    estimated_minutes=15,
)

PERFORMANCE_INCIDENT = Procedure(
    id="incident_002",
    category=ProcedureCategory.INCIDENT_RESPONSE,
    title="Performance Degradation Response",
    description="Handle sudden performance drops",
    steps=[
        "1. Alert fires (response >2s or error >1%)",
        "2. Identify root cause (slow query, leak, spike)",
        "3. Apply immediate fix (scale, kill query, circuit break)",
        "4. Monitor recovery (5 min clean = success)",
        "5. Schedule permanent fix",
        "6. Deploy in next cycle",
    ],
    owner="Operations",
    severity="high",
    estimated_minutes=10,
)

CLIENT_ONBOARDING_SOP = Procedure(
    id="client_001",
    category=ProcedureCategory.CLIENT_ONBOARDING,
    title="New Client Onboarding Process",
    description="Complete onboarding workflow",
    steps=[
        "1. Capture requirements (meeting + docs)",
        "2. Create tenant in database",
        "3. Generate and send API keys securely",
        "4. Create welcome portal",
        "5. Schedule kickoff meeting",
        "6. Deliver SOW + documentation",
        "7. Track milestones (setup, data sync, go-live)",
        "8. Schedule 30-day health check",
    ],
    owner="Client Success",
    severity="high",
    estimated_minutes=120,
)

DEAL_CLOSURE_SOP = Procedure(
    id="revenue_001",
    category=ProcedureCategory.REVENUE_ACTIVATION,
    title="Deal Closure & First Invoice",
    description="From closed deal to active client",
    steps=[
        "1. Deal marked as won",
        "2. Generate invoice (ALY-YYYYMM-XXXX)",
        "3. Send via email",
        "4. Record in accounting system",
        "5. Set up recurring billing (if retainer)",
        "6. Create client account in portal",
        "7. Send welcome package",
        "8. Schedule kickoff call",
    ],
    owner="Revenue Ops",
    severity="high",
    estimated_minutes=60,
)

BACKUP_RECOVERY_SOP = Procedure(
    id="disaster_001",
    category=ProcedureCategory.DISASTER_RECOVERY,
    title="Backup Recovery Procedure",
    description="Restore from backup after data loss",
    steps=[
        "1. Identify loss scope and recovery point",
        "2. Select appropriate backup",
        "3. Test restore in isolated environment",
        "4. Validate data integrity",
        "5. Notify affected clients",
        "6. Plan switchover (maintenance if needed)",
        "7. Execute switchover",
        "8. Analyze root cause and prevent recurrence",
    ],
    owner="Database",
    severity="critical",
    estimated_minutes=120,
)


SOP_REGISTRY = {
    "emergency_shutdown": EMERGENCY_SHUTDOWN,
    "regional_failover": REGIONAL_FAILOVER,
    "blue_green_deploy": BLUE_GREEN_DEPLOY,
    "db_migration": DATABASE_MIGRATION,
    "security_breach": SECURITY_BREACH_RESPONSE,
    "performance_incident": PERFORMANCE_INCIDENT,
    "client_onboarding": CLIENT_ONBOARDING_SOP,
    "deal_closure": DEAL_CLOSURE_SOP,
    "backup_recovery": BACKUP_RECOVERY_SOP,
}


class SOPManager:
    @staticmethod
    def get_procedure(procedure_id: str) -> Procedure:
        return SOP_REGISTRY.get(procedure_id)
    
    @staticmethod
    def get_critical() -> List[Procedure]:
        return [p for p in SOP_REGISTRY.values() if p.severity == "critical"]
    
    @staticmethod
    def get_by_category(category: ProcedureCategory) -> List[Procedure]:
        return [p for p in SOP_REGISTRY.values() if p.category == category]
