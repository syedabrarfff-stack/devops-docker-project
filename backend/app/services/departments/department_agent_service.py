"""
Layer 1 — Department Intelligence Officers (DIO)

One DIO per department. Each DIO:
- Monitors all department operations continuously
- Collects KPIs and performance metrics
- Generates milestone PDFs and submits to Council
- Receives improvement PDFs back from Council
- Implements Council recommendations
- Reports to Strategy Oversight Team daily
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.department_intelligence import (
    DepartmentCode,
    DepartmentIntelligenceOfficer,
    DepartmentMilestone,
    MilestoneStatus,
)
from app.services.ai.base_provider import Message, TaskType
from app.services.ai.router import ai_router

logger = logging.getLogger(__name__)

# Complete DIO roster — one per department with full persona, KPIs, escalation rules
DIO_DEFINITIONS = [
    {
        "department_code": DepartmentCode.ENGINEERING,
        "department_name": "Engineering Division",
        "division": "Technology",
        "agent_name": "ATLAS-E1",
        "agent_persona": "Senior Engineering Intelligence Officer",
        "agent_email": "engineering.dio@aliyarsolutions.com",
        "monitored_systems": ["codebase", "CI/CD", "deployments", "API health", "test coverage"],
        "kpi_targets": {
            "deployment_success_rate": 99.5,
            "api_latency_p95_ms": 200,
            "test_coverage_percent": 85,
            "open_critical_bugs": 0,
            "weekly_deployments": 5,
        },
        "escalation_rules": {
            "deployment_failure": "immediate_captain_alert",
            "api_latency_above_500ms": "ops_team_notify",
            "test_coverage_below_70": "council_review",
        },
    },
    {
        "department_code": DepartmentCode.AI_ML,
        "department_name": "AI & Machine Learning Division",
        "division": "Technology",
        "agent_name": "ORACLE-AI",
        "agent_persona": "AI Operations Intelligence Officer",
        "agent_email": "ai.dio@aliyarsolutions.com",
        "monitored_systems": ["ai_router", "provider_health", "cost_tracker", "council_sessions"],
        "kpi_targets": {
            "provider_availability": 99.0,
            "avg_cost_per_call_usd": 0.05,
            "council_session_success_rate": 90.0,
            "fallback_rate_percent": 5.0,
            "monthly_ai_spend_usd": 500,
        },
        "escalation_rules": {
            "all_providers_down": "immediate_captain_alert",
            "monthly_spend_above_800": "captain_approval",
            "council_failure_rate_above_20": "architecture_review",
        },
    },
    {
        "department_code": DepartmentCode.CLOUD_INFRA,
        "department_name": "Cloud Infrastructure Division",
        "division": "Technology",
        "agent_name": "NEXUS-CI",
        "agent_persona": "Cloud Infrastructure Intelligence Officer",
        "agent_email": "cloud.dio@aliyarsolutions.com",
        "monitored_systems": ["AWS ECS", "RDS PostgreSQL", "ElastiCache Redis", "ALB", "S3", "CloudWatch"],
        "kpi_targets": {
            "uptime_percent": 99.9,
            "rds_connection_pool_usage": 70,
            "redis_memory_usage_percent": 60,
            "monthly_aws_spend_usd": 300,
            "backup_success_rate": 100,
        },
        "escalation_rules": {
            "uptime_below_99": "immediate_captain_alert",
            "rds_connections_above_90_percent": "scale_up_trigger",
            "monthly_spend_above_500": "captain_approval",
        },
    },
    {
        "department_code": DepartmentCode.DEVOPS,
        "department_name": "DevOps Division",
        "division": "Technology",
        "agent_name": "SIGNAL-DO",
        "agent_persona": "DevOps Intelligence Officer",
        "agent_email": "devops.dio@aliyarsolutions.com",
        "monitored_systems": ["GitHub Actions", "Docker", "Terraform", "Nginx", "Prometheus", "Grafana"],
        "kpi_targets": {
            "pipeline_success_rate": 98.0,
            "deployment_duration_minutes": 8,
            "infrastructure_drift_issues": 0,
            "container_health_score": 100,
            "incident_mttr_minutes": 30,
        },
        "escalation_rules": {
            "pipeline_failure_3x": "engineering_team_alert",
            "infrastructure_drift": "terraform_review",
            "container_down": "immediate_restart_trigger",
        },
    },
    {
        "department_code": DepartmentCode.SECURITY,
        "department_name": "Security Division",
        "division": "Technology",
        "agent_name": "CIPHER-SEC",
        "agent_persona": "Security Intelligence Officer",
        "agent_email": "security.dio@aliyarsolutions.com",
        "monitored_systems": ["auth_layer", "API_keys", "secrets_manager", "audit_logs", "threat_monitor"],
        "kpi_targets": {
            "failed_auth_attempts_daily": 10,
            "secrets_rotation_days": 90,
            "vulnerability_open_critical": 0,
            "audit_log_coverage": 100,
            "penetration_test_score": 90,
        },
        "escalation_rules": {
            "critical_vulnerability": "immediate_captain_alert",
            "auth_brute_force": "auto_block_trigger",
            "secret_exposed": "immediate_rotation",
        },
    },
    {
        "department_code": DepartmentCode.REVENUE_GROWTH,
        "department_name": "Revenue Growth Division",
        "division": "Commercial",
        "agent_name": "PULSE-RG",
        "agent_persona": "Revenue Growth Intelligence Officer",
        "agent_email": "revenue.dio@aliyarsolutions.com",
        "monitored_systems": ["CRM", "lead_pipeline", "proposals", "outreach_engine", "payment_processor"],
        "kpi_targets": {
            "monthly_leads_qualified": 50,
            "proposals_sent_monthly": 10,
            "demo_conversion_rate": 30.0,
            "proposal_win_rate": 25.0,
            "mrr_target_usd": 10000,
        },
        "escalation_rules": {
            "zero_leads_72h": "captain_alert",
            "proposal_win_rate_below_15": "strategy_council_review",
            "mrr_decline_consecutive_weeks": "immediate_council_session",
        },
    },
    {
        "department_code": DepartmentCode.MARKETING,
        "department_name": "Marketing Division",
        "division": "Commercial",
        "agent_name": "HERALD-MK",
        "agent_persona": "Marketing Intelligence Officer",
        "agent_email": "marketing.dio@aliyarsolutions.com",
        "monitored_systems": ["outreach_campaigns", "email_sequences", "apollo_pipeline", "reply_tracking"],
        "kpi_targets": {
            "outreach_sent_weekly": 100,
            "email_open_rate_percent": 35,
            "reply_rate_percent": 8,
            "positive_reply_rate_percent": 3,
            "campaigns_active": 5,
        },
        "escalation_rules": {
            "reply_rate_below_3": "sequence_optimization_trigger",
            "open_rate_below_20": "subject_line_council_review",
            "campaign_deliverability_issues": "email_infra_alert",
        },
    },
    {
        "department_code": DepartmentCode.CLIENT_SERVICES,
        "department_name": "Client Services Division",
        "division": "Commercial",
        "agent_name": "BRIDGE-CS",
        "agent_persona": "Client Services Intelligence Officer",
        "agent_email": "clients.dio@aliyarsolutions.com",
        "monitored_systems": ["client_portal", "onboarding_flows", "SLA_tracker", "satisfaction_monitor"],
        "kpi_targets": {
            "client_satisfaction_score": 90.0,
            "onboarding_duration_days": 3,
            "sla_compliance_rate": 99.0,
            "client_retention_rate": 95.0,
            "support_response_time_hours": 2,
        },
        "escalation_rules": {
            "client_satisfaction_below_70": "immediate_captain_alert",
            "sla_breach": "ops_team_escalation",
            "churn_risk_detected": "council_review",
        },
    },
    {
        "department_code": DepartmentCode.CLIENT_DELIVERY,
        "department_name": "Client Delivery Division",
        "division": "Commercial",
        "agent_name": "VECTOR-CD",
        "agent_persona": "Delivery Intelligence Officer",
        "agent_email": "delivery.dio@aliyarsolutions.com",
        "monitored_systems": ["project_tracker", "deliverable_queue", "quality_gate", "milestone_board"],
        "kpi_targets": {
            "on_time_delivery_rate": 95.0,
            "deliverable_quality_score": 92.0,
            "revision_requests_per_project": 1.5,
            "project_completion_rate": 100.0,
            "client_approval_rate": 98.0,
        },
        "escalation_rules": {
            "project_overdue_48h": "captain_alert",
            "quality_score_below_80": "review_trigger",
            "client_rejection_3x": "council_intervention",
        },
    },
    {
        "department_code": DepartmentCode.CUSTOMER_SUPPORT,
        "department_name": "Customer Support & Feedback Division",
        "division": "Commercial",
        "agent_name": "ECHO-CS",
        "agent_persona": "Support Intelligence Officer",
        "agent_email": "support.dio@aliyarsolutions.com",
        "monitored_systems": ["support_tickets", "feedback_system", "escalation_queue", "nps_tracker"],
        "kpi_targets": {
            "ticket_resolution_time_hours": 4,
            "first_contact_resolution_rate": 85.0,
            "nps_score": 60,
            "escalation_rate_percent": 5,
            "feedback_response_rate": 100,
        },
        "escalation_rules": {
            "nps_below_40": "captain_alert_and_council",
            "ticket_backlog_above_20": "support_scale_trigger",
            "critical_feedback": "immediate_review",
        },
    },
    {
        "department_code": DepartmentCode.INTELLIGENCE,
        "department_name": "Intelligence Division",
        "division": "Intelligence",
        "agent_name": "RADAR-INT",
        "agent_persona": "Intelligence Operations Officer",
        "agent_email": "intelligence.dio@aliyarsolutions.com",
        "monitored_systems": ["market_intel", "competitor_tracker", "tech_radar", "research_engine"],
        "kpi_targets": {
            "competitor_profiles_maintained": 10,
            "market_reports_monthly": 4,
            "tech_discoveries_weekly": 15,
            "intelligence_accuracy_score": 85.0,
            "strategic_insights_generated": 20,
        },
        "escalation_rules": {
            "competitor_major_move": "immediate_strategy_brief",
            "disruptive_tech_detected": "council_evaluation",
            "market_shift_detected": "captain_brief",
        },
    },
    {
        "department_code": DepartmentCode.PEOPLE_OPS,
        "department_name": "People Operations Division",
        "division": "Operations",
        "agent_name": "PRISM-PO",
        "agent_persona": "People Operations Intelligence Officer",
        "agent_email": "people.dio@aliyarsolutions.com",
        "monitored_systems": ["agent_registry", "performance_tracker", "onboarding_system", "team_health"],
        "kpi_targets": {
            "agent_performance_score_avg": 88.0,
            "onboarding_completion_rate": 100,
            "team_capacity_utilization": 80.0,
            "agent_improvement_cycle_days": 30,
        },
        "escalation_rules": {
            "agent_performance_below_60": "retraining_trigger",
            "team_capacity_above_95": "scaling_recommendation",
        },
    },
    {
        "department_code": DepartmentCode.PMO,
        "department_name": "Project Management Office",
        "division": "Operations",
        "agent_name": "ANCHOR-PMO",
        "agent_persona": "PMO Intelligence Officer",
        "agent_email": "pmo.dio@aliyarsolutions.com",
        "monitored_systems": ["project_registry", "sprint_tracker", "capacity_board", "risk_register"],
        "kpi_targets": {
            "sprint_completion_rate": 90.0,
            "project_on_time_rate": 95.0,
            "risk_items_resolved": 100,
            "cross_team_blockers": 0,
        },
        "escalation_rules": {
            "sprint_failure_2x": "process_review",
            "cross_team_blocker_48h": "captain_alert",
        },
    },
    {
        "department_code": DepartmentCode.FINANCE,
        "department_name": "Finance Division",
        "division": "Operations",
        "agent_name": "LEDGER-FIN",
        "agent_persona": "Finance Intelligence Officer",
        "agent_email": "finance.dio@aliyarsolutions.com",
        "monitored_systems": ["revenue_tracker", "invoice_system", "expense_monitor", "payment_processor"],
        "kpi_targets": {
            "invoice_collection_rate": 100,
            "days_sales_outstanding": 30,
            "monthly_burn_rate_usd": 500,
            "payment_processing_success": 99.9,
            "financial_report_accuracy": 100,
        },
        "escalation_rules": {
            "invoice_overdue_30d": "captain_alert",
            "payment_failure": "immediate_retry_trigger",
            "burn_rate_above_1000": "cost_review",
        },
    },
    {
        "department_code": DepartmentCode.STRATEGY,
        "department_name": "Strategy Division",
        "division": "Executive",
        "agent_name": "COMPASS-STR",
        "agent_persona": "Strategy Intelligence Officer",
        "agent_email": "strategy.dio@aliyarsolutions.com",
        "monitored_systems": ["council_decisions", "strategic_roadmap", "competitive_position", "market_signals"],
        "kpi_targets": {
            "council_sessions_monthly": 20,
            "strategic_initiatives_active": 5,
            "roadmap_completion_rate": 85.0,
            "strategic_decision_quality": 90.0,
        },
        "escalation_rules": {
            "market_position_threat": "immediate_council_session",
            "roadmap_drift_above_20_percent": "captain_review",
        },
    },
]


def _canonical_dio_definitions() -> list[dict[str, Any]]:
    """Build the current DIO roster from the finalized 25-module catalog."""
    from app.services.catalog.catalog_service import CAPABILITY_MODULES

    return [
        {
            "department_code": module["code"].lower(),
            "department_name": f"{module['name']} Department",
            "division": module["division"],
            "agent_name": f"{module['code']}-DIO",
            "agent_persona": f"{module['name']} Department Intelligence Officer",
            "agent_email": f"{module['code'].lower().replace('-', '.')}@aliyarsolutions.com",
            "monitored_systems": module.get("agent_layer", []),
            "kpi_targets": {target: "tracked" for target in module.get("kpi_targets", [])},
            "escalation_rules": {
                "critical_blocker": "captain_review",
                "governance_boundary": "approval_required",
                "performance_drift": "council_review",
            },
        }
        for module in CAPABILITY_MODULES
    ]


def _department_code_value(code: Any) -> str:
    return getattr(code, "value", str(code))


class DepartmentAgentService:
    """Manages all Department Intelligence Officers across the organization."""

    async def initialize_all_dios(self, tenant_id: str) -> list[DepartmentIntelligenceOfficer]:
        """Create or update all DIO records for the tenant."""
        tenant_uuid = uuid.UUID(str(tenant_id))
        created = []

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, str(tenant_uuid))

            definitions = _canonical_dio_definitions()
            canonical_codes = {d["department_code"] for d in definitions}

            for defn in definitions:
                existing = await db.scalar(
                    select(DepartmentIntelligenceOfficer).where(
                        DepartmentIntelligenceOfficer.tenant_id == tenant_uuid,
                        DepartmentIntelligenceOfficer.department_code == _department_code_value(defn["department_code"]),
                    )
                )
                if existing:
                    existing.department_name = defn["department_name"]
                    existing.division = defn["division"]
                    existing.agent_name = defn["agent_name"]
                    existing.agent_persona = defn["agent_persona"]
                    existing.agent_email = defn["agent_email"]
                    existing.monitored_systems = defn["monitored_systems"]
                    existing.kpi_targets = defn["kpi_targets"]
                    existing.escalation_rules = defn["escalation_rules"]
                    existing.is_active = True
                else:
                    dio = DepartmentIntelligenceOfficer(
                        tenant_id=tenant_uuid,
                        department_code=_department_code_value(defn["department_code"]),
                        department_name=defn["department_name"],
                        division=defn["division"],
                        agent_name=defn["agent_name"],
                        agent_persona=defn["agent_persona"],
                        agent_email=defn["agent_email"],
                        monitored_systems=defn["monitored_systems"],
                        kpi_targets=defn["kpi_targets"],
                        escalation_rules=defn["escalation_rules"],
                    )
                    db.add(dio)
                    created.append(dio)

            await db.execute(
                update(DepartmentIntelligenceOfficer)
                .where(
                    DepartmentIntelligenceOfficer.tenant_id == tenant_uuid,
                    DepartmentIntelligenceOfficer.department_code.notin_(canonical_codes),
                )
                .values(is_active=False)
            )
            await db.commit()

        logger.info("DIO initialization: %d canonical departments configured", len(_canonical_dio_definitions()))
        return created

    async def get_all_dios(self, db: AsyncSession, tenant_id: str) -> list[dict]:
        tenant_uuid = uuid.UUID(str(tenant_id))
        result = await db.execute(
            select(DepartmentIntelligenceOfficer)
            .where(DepartmentIntelligenceOfficer.tenant_id == tenant_uuid)
            .where(DepartmentIntelligenceOfficer.is_active.is_(True))
            .order_by(DepartmentIntelligenceOfficer.department_code)
        )
        dios = result.scalars().all()
        return [self._serialize_dio(d) for d in dios]

    async def get_dio_status(self, db: AsyncSession, tenant_id: str, department_code: str) -> dict:
        tenant_uuid = uuid.UUID(str(tenant_id))
        dio = await db.scalar(
            select(DepartmentIntelligenceOfficer).where(
                DepartmentIntelligenceOfficer.tenant_id == tenant_uuid,
                DepartmentIntelligenceOfficer.department_code == department_code,
            )
        )
        if not dio:
            return {"error": f"DIO not found for department: {department_code}"}
        return self._serialize_dio(dio)

    async def collect_department_metrics(self, db: AsyncSession, tenant_id: str) -> dict[str, Any]:
        """Collect current operational metrics across all departments."""
        tenant_uuid = uuid.UUID(str(tenant_id))

        definitions = _canonical_dio_definitions()

        metrics_prompt = f"""You are JARVIS, the operational intelligence core of Aliyar Solutions.

Analyze the current operational state across all {len(definitions)} canonical AIONX departments and generate
a comprehensive metrics snapshot for today: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.

For each department, assess:
1. Current operational health score (0-100)
2. Primary KPI status (on-track / at-risk / critical)
3. Top achievement this period
4. Most critical blocker or risk
5. Recommended priority action

Departments to assess: {', '.join(d['department_name'] for d in definitions)}

Return a JSON object with department_code as keys and metric objects as values.
Each metric object: {{"health": 85, "kpi_status": "on-track", "achievement": "...", "blocker": "...", "action": "..."}}
Return only valid JSON, no markdown."""

        response, _ = await ai_router.chat(
            [Message(role="user", content=metrics_prompt)],
            task_type=TaskType.ANALYSIS,
        )

        import json
        try:
            metrics = json.loads(response.content.strip())
        except Exception:
            metrics = {"raw": response.content}

        return {
            "tenant_id": str(tenant_uuid),
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "department_metrics": metrics,
            "departments_assessed": len(definitions),
        }

    async def submit_milestone(
        self,
        db: AsyncSession,
        tenant_id: str,
        department_code: str,
        title: str,
        description: str,
        milestone_type: str,
        metrics: dict,
        evidence_data: dict,
    ) -> DepartmentMilestone:
        """DIO submits a milestone for Council review."""
        tenant_uuid = uuid.UUID(str(tenant_id))

        dio = await db.scalar(
            select(DepartmentIntelligenceOfficer).where(
                DepartmentIntelligenceOfficer.tenant_id == tenant_uuid,
                DepartmentIntelligenceOfficer.department_code == department_code,
            )
        )
        if not dio:
            raise ValueError(f"DIO not found for department: {department_code}")

        impact_score = await self._calculate_impact_score(title, description, metrics)

        milestone = DepartmentMilestone(
            tenant_id=tenant_uuid,
            dio_id=dio.id,
            department_code=department_code,
            title=title,
            description=description,
            milestone_type=milestone_type,
            metrics=metrics,
            evidence_data=evidence_data,
            impact_score=impact_score,
            status=MilestoneStatus.ACHIEVED.value,
        )
        db.add(milestone)

        dio.milestones_submitted = (dio.milestones_submitted or 0) + 1
        await db.commit()
        await db.refresh(milestone)

        logger.info("Milestone submitted: %s | dept=%s | impact=%.1f", title, department_code, impact_score)
        return milestone

    async def get_milestones(
        self, db: AsyncSession, tenant_id: str, department_code: str | None = None, limit: int = 50
    ) -> list[dict]:
        tenant_uuid = uuid.UUID(str(tenant_id))
        query = (
            select(DepartmentMilestone)
            .where(DepartmentMilestone.tenant_id == tenant_uuid)
            .order_by(DepartmentMilestone.created_at.desc())
            .limit(limit)
        )
        if department_code:
            query = query.where(DepartmentMilestone.department_code == department_code)

        result = await db.execute(query)
        return [self._serialize_milestone(m) for m in result.scalars().all()]

    async def implement_council_recommendation(
        self, db: AsyncSession, tenant_id: str, milestone_id: str, notes: str
    ) -> dict:
        tenant_uuid = uuid.UUID(str(tenant_id))
        milestone = await db.get(DepartmentMilestone, uuid.UUID(milestone_id))
        if not milestone or milestone.tenant_id != tenant_uuid:
            raise ValueError("Milestone not found")

        milestone.status = MilestoneStatus.IMPLEMENTED.value
        milestone.implementation_notes = notes
        milestone.implemented_at = datetime.now(timezone.utc)

        dio = await db.get(DepartmentIntelligenceOfficer, milestone.dio_id)
        if dio:
            dio.improvements_implemented = (dio.improvements_implemented or 0) + 1
            dio.performance_score = min(1.0, (dio.performance_score or 1.0) + 0.02)

        await db.commit()
        return {"milestone_id": milestone_id, "status": "implemented", "implemented_at": milestone.implemented_at.isoformat()}

    async def _calculate_impact_score(self, title: str, description: str, metrics: dict) -> float:
        prompt = f"""Rate the impact of this milestone from 0-100 for Aliyar Solutions:
Title: {title}
Description: {description[:300]}
Metrics: {str(metrics)[:200]}
Return only a single number between 0 and 100."""

        try:
            response, _ = await ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=TaskType.FAST,
            )
            score = float(response.content.strip().split()[0])
            return max(0.0, min(100.0, score))
        except Exception:
            return 50.0

    def _serialize_dio(self, d: DepartmentIntelligenceOfficer) -> dict:
        return {
            "id": str(d.id),
            "department_code": d.department_code,
            "department_name": d.department_name,
            "division": d.division,
            "agent_name": d.agent_name,
            "agent_persona": d.agent_persona,
            "agent_email": d.agent_email,
            "monitored_systems": d.monitored_systems or [],
            "kpi_targets": d.kpi_targets or {},
            "milestones_submitted": d.milestones_submitted or 0,
            "improvements_received": d.improvements_received or 0,
            "improvements_implemented": d.improvements_implemented or 0,
            "performance_score": d.performance_score or 1.0,
            "last_report_at": d.last_report_at.isoformat() if d.last_report_at else None,
            "next_report_at": d.next_report_at.isoformat() if d.next_report_at else None,
            "is_active": d.is_active,
        }

    def _serialize_milestone(self, m: DepartmentMilestone) -> dict:
        return {
            "id": str(m.id),
            "dio_id": str(m.dio_id),
            "department_code": m.department_code,
            "title": m.title,
            "description": m.description,
            "milestone_type": m.milestone_type,
            "metrics": m.metrics or {},
            "impact_score": m.impact_score,
            "milestone_pdf_url": m.milestone_pdf_url,
            "improvement_pdf_url": m.improvement_pdf_url,
            "council_score": m.council_score,
            "council_verdict": m.council_verdict,
            "council_recommendations": m.council_recommendations or [],
            "status": m.status,
            "implementation_notes": m.implementation_notes,
            "implemented_at": m.implemented_at.isoformat() if m.implemented_at else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }


department_agent_service = DepartmentAgentService()
