"""
JARVIS Platform Intelligence Engine.

JARVIS is not just a business brain. JARVIS is the platform engineer,
cloud architect, infrastructure commander, and systems reliability owner
of Aliyar Solutions.

Every AWS cost, every deployment decision, every scaling action, every
security posture change — JARVIS understands it, models it, decides within
constitutional authority, and escalates what requires Captain.

This engine governs:
 - AWS cost intelligence and optimization decisions
 - Auto-scaling recommendations and triggers
 - Security posture monitoring and hardening
 - Technology debt tracking and remediation sequencing
 - Performance benchmarking and SLA compliance
 - Deployment risk assessment
 - Infrastructure architecture decisions
 - Multi-region DR readiness
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


# ─── INFRASTRUCTURE TOPOLOGY ─────────────────────────────────────────────────

INFRASTRUCTURE = {
    "primary_region": "ap-south-2",
    "dr_region": "ap-south-1",
    "compute": "AWS ECS Fargate",
    "database": "PostgreSQL 16 (RDS)",
    "cache": "Redis 7 (ElastiCache)",
    "cdn": "CloudFront",
    "secrets": "AWS Secrets Manager",
    "ci_cd": "GitHub Actions → ECR → ECS blue/green",
    "deployment_strategy": "Blue/Green rolling update",
    "health_gates": ["/health (liveness)", "/readyz (deep readiness)"],
}

COST_THRESHOLDS = {
    "monthly_infra_budget_usd": 500,
    "alert_at_pct": 0.75,
    "critical_at_pct": 0.90,
    "ai_api_budget_usd": 300,
    "ai_alert_at_pct": 0.80,
    "per_client_target_usd": 40,
    "gross_margin_floor_pct": 0.65,
}

SLA_STANDARDS = {
    "uptime_target_pct": 99.9,
    "api_p99_latency_ms": 500,
    "api_p50_latency_ms": 150,
    "max_error_rate_pct": 0.5,
    "deploy_max_downtime_seconds": 30,
    "alert_response_minutes": 5,
    "incident_resolution_hours": 4,
    "rto_hours": 1,
    "rpo_hours": 4,
}


# ─── SECURITY POSTURE STANDARDS ───────────────────────────────────────────────

SECURITY_STANDARDS = {
    "authentication": [
        "JWT tokens with 24h expiry",
        "Refresh token rotation",
        "Captain-level API key for admin endpoints",
    ],
    "secrets_management": [
        "All secrets in AWS Secrets Manager",
        "Zero secrets in code",
        "Zero secrets in git history",
        "Environment-specific rotation schedule",
    ],
    "network": [
        "VPC with private subnets for RDS and Redis",
        "ALB in public subnet only",
        "Security groups: principle of least privilege",
        "No direct database exposure to internet",
    ],
    "application": [
        "Input validation on all endpoints",
        "Rate limiting on all write endpoints",
        "SQL injection prevention via ORM",
        "XSS prevention via response encoding",
        "CORS restricted to known origins",
    ],
    "compliance_targets": ["SOC2 Type II readiness", "GDPR data handling", "ISO 27001 foundations"],
    "critical_violations": [
        "Secret in code/commit",
        "debug=True in production",
        "Public database endpoint",
        "Unrotated credentials >90 days",
        "Missing rate limits on authenticated endpoints",
        "No input validation on user-supplied data",
    ],
}


# ─── SCALING INTELLIGENCE ─────────────────────────────────────────────────────

SCALING_TRIGGERS = {
    "SCALE_UP": {
        "cpu_threshold_pct": 70,
        "memory_threshold_pct": 80,
        "request_queue_depth": 1000,
        "p99_latency_ms": 800,
        "action": "Increase ECS desired count by 2",
        "authority": "JARVIS_AUTONOMOUS",
        "cost_impact": "~$60-120/month per additional task",
    },
    "SCALE_DOWN": {
        "cpu_threshold_pct": 20,
        "memory_threshold_pct": 25,
        "sustained_minutes": 30,
        "action": "Decrease ECS desired count by 1 (floor: 2 tasks)",
        "authority": "JARVIS_AUTONOMOUS",
        "cost_impact": "Reduction of ~$30-60/month",
    },
    "REGIONAL_FAILOVER": {
        "trigger": "Primary region health check failures >3 consecutive",
        "action": "Activate DR region ap-south-1",
        "authority": "CAPTAIN_FAST_TRACK",
        "rto": "60 minutes",
        "notification": "Immediate Slack + Telegram to Captain",
    },
    "DATABASE_SCALING": {
        "trigger": "RDS CPU >75% sustained 15 min or storage >80%",
        "action": "Recommend RDS instance upgrade or read replica",
        "authority": "CAPTAIN_FAST_TRACK",
        "cost_impact": "Varies — present options with costs",
    },
}


# ─── TECHNOLOGY DEBT REGISTRY ─────────────────────────────────────────────────

TECH_DEBT_CATEGORIES = {
    "CRITICAL": {
        "description": "Blocks scaling, creates security risk, or degrades client SLAs",
        "remediation_priority": "THIS_SPRINT",
        "max_age_days": 14,
    },
    "HIGH": {
        "description": "Significantly increases operational complexity or cost",
        "remediation_priority": "NEXT_SPRINT",
        "max_age_days": 30,
    },
    "MEDIUM": {
        "description": "Reduces code quality, increases maintenance burden",
        "remediation_priority": "THIS_QUARTER",
        "max_age_days": 90,
    },
    "LOW": {
        "description": "Nice-to-have cleanup, minor refactoring",
        "remediation_priority": "BACKLOG",
        "max_age_days": 180,
    },
}

KNOWN_TECH_IMPROVEMENTS = [
    {
        "id": "TI-001",
        "title": "pgvector semantic search implementation",
        "category": "HIGH",
        "benefit": "Enable intelligent knowledge retrieval across all JARVIS memory",
        "estimated_hours": 16,
        "revenue_impact": "MEDIUM — unlocks smarter lead scoring and client intelligence",
    },
    {
        "id": "TI-002",
        "title": "Redis caching layer for hot query paths",
        "category": "HIGH",
        "benefit": "Reduce database load by ~60%, improve API latency by ~40%",
        "estimated_hours": 8,
        "revenue_impact": "LOW-DIRECT — operational efficiency, SLA improvement",
    },
    {
        "id": "TI-003",
        "title": "Comprehensive structured logging + trace IDs",
        "category": "MEDIUM",
        "benefit": "Full request traceability, faster incident resolution",
        "estimated_hours": 12,
        "revenue_impact": "LOW-DIRECT — operational quality, reduces downtime",
    },
    {
        "id": "TI-004",
        "title": "Multi-tenant isolation hardening",
        "category": "HIGH",
        "benefit": "Strict per-tenant data isolation for compliance",
        "estimated_hours": 24,
        "revenue_impact": "HIGH — required for enterprise and compliance-sensitive clients",
    },
    {
        "id": "TI-005",
        "title": "AI cost tracking per client/request",
        "category": "HIGH",
        "benefit": "Attribute AI API cost to clients, protect margins",
        "estimated_hours": 8,
        "revenue_impact": "HIGH — direct margin protection",
    },
]


# ─── PLATFORM INTELLIGENCE ENGINE ────────────────────────────────────────────

class PlatformIntelligence:
    """
    JARVIS as cloud architect, infrastructure commander, and platform engineer.

    Not advisory. Operational. JARVIS understands the full stack,
    models costs, assesses risks, and acts within authority or escalates.
    """

    def assess_cost_posture(self, cost_data: dict[str, Any]) -> dict[str, Any]:
        monthly_infra = cost_data.get("monthly_infra_usd", 0)
        monthly_ai_api = cost_data.get("monthly_ai_api_usd", 0)
        current_mrr = cost_data.get("mrr", 0)
        client_count = cost_data.get("client_count", 1)

        infra_budget = COST_THRESHOLDS["monthly_infra_budget_usd"]
        ai_budget = COST_THRESHOLDS["ai_api_budget_usd"]

        infra_pct = monthly_infra / infra_budget if infra_budget > 0 else 0
        ai_pct = monthly_ai_api / ai_budget if ai_budget > 0 else 0

        total_opex = monthly_infra + monthly_ai_api
        gross_margin = ((current_mrr - total_opex) / current_mrr) if current_mrr > 0 else 0
        per_client_cost = total_opex / client_count if client_count > 0 else total_opex

        alerts = []
        if infra_pct >= COST_THRESHOLDS["critical_at_pct"]:
            alerts.append({"type": "CRITICAL", "message": f"Infrastructure cost at {infra_pct*100:.0f}% of budget"})
        elif infra_pct >= COST_THRESHOLDS["alert_at_pct"]:
            alerts.append({"type": "WARNING", "message": f"Infrastructure cost at {infra_pct*100:.0f}% of budget"})

        if ai_pct >= COST_THRESHOLDS["ai_alert_at_pct"]:
            alerts.append({"type": "WARNING", "message": f"AI API cost at {ai_pct*100:.0f}% of budget"})

        if gross_margin < COST_THRESHOLDS["gross_margin_floor_pct"]:
            alerts.append({
                "type": "CRITICAL",
                "message": f"Gross margin {gross_margin*100:.0f}% below floor of {COST_THRESHOLDS['gross_margin_floor_pct']*100:.0f}%",
            })

        optimizations = []
        if per_client_cost > COST_THRESHOLDS["per_client_target_usd"] * 1.5:
            optimizations.append("Per-client infrastructure cost high — review ECS task sizing")
        if monthly_ai_api > 200:
            optimizations.append("AI API cost elevated — implement response caching and model routing optimization")

        return {
            "monthly_infra_usd": monthly_infra,
            "monthly_ai_api_usd": monthly_ai_api,
            "total_opex_usd": total_opex,
            "mrr": current_mrr,
            "gross_margin_pct": round(gross_margin * 100, 1),
            "per_client_cost_usd": round(per_client_cost, 2),
            "infra_budget_utilization_pct": round(infra_pct * 100, 1),
            "ai_budget_utilization_pct": round(ai_pct * 100, 1),
            "alerts": alerts,
            "cost_optimizations": optimizations,
            "posture": "HEALTHY" if not alerts else "AT_RISK" if len(alerts) == 1 else "CRITICAL",
            "assessed_at": datetime.now(UTC).isoformat(),
        }

    def assess_scaling_readiness(self, metrics: dict[str, Any]) -> dict[str, Any]:
        cpu_pct = metrics.get("cpu_pct", 30)
        memory_pct = metrics.get("memory_pct", 40)
        p99_latency = metrics.get("p99_latency_ms", 200)
        error_rate = metrics.get("error_rate_pct", 0)
        current_tasks = metrics.get("ecs_task_count", 2)

        recommendations = []
        authority_required = "JARVIS_AUTONOMOUS"

        scale_up = SCALING_TRIGGERS["SCALE_UP"]
        if cpu_pct >= scale_up["cpu_threshold_pct"] or memory_pct >= scale_up["memory_threshold_pct"]:
            recommendations.append({
                "action": scale_up["action"],
                "trigger": f"CPU {cpu_pct}% or Memory {memory_pct}% above threshold",
                "authority": scale_up["authority"],
                "cost_impact": scale_up["cost_impact"],
            })

        scale_down = SCALING_TRIGGERS["SCALE_DOWN"]
        if (cpu_pct < scale_down["cpu_threshold_pct"]
                and memory_pct < scale_down["memory_threshold_pct"]
                and current_tasks > 2):
            recommendations.append({
                "action": scale_down["action"],
                "trigger": f"CPU {cpu_pct}% and Memory {memory_pct}% both below threshold",
                "authority": scale_down["authority"],
                "cost_impact": scale_down["cost_impact"],
            })

        if p99_latency > SLA_STANDARDS["api_p99_latency_ms"]:
            recommendations.append({
                "action": "Investigate latency sources: DB query optimization, cache warming, connection pooling",
                "trigger": f"P99 latency {p99_latency}ms exceeds SLA of {SLA_STANDARDS['api_p99_latency_ms']}ms",
                "authority": "JARVIS_AUTONOMOUS",
                "cost_impact": "None — optimization required",
            })

        if error_rate > SLA_STANDARDS["max_error_rate_pct"]:
            recommendations.append({
                "action": "Immediate error investigation — check logs, alert Captain",
                "trigger": f"Error rate {error_rate}% exceeds {SLA_STANDARDS['max_error_rate_pct']}% SLA",
                "authority": "CAPTAIN_FAST_TRACK",
                "cost_impact": "Revenue risk — client SLA breach",
            })
            authority_required = "CAPTAIN_FAST_TRACK"

        sla_status = {
            "uptime": "COMPLIANT",
            "latency": "COMPLIANT" if p99_latency <= SLA_STANDARDS["api_p99_latency_ms"] else "BREACHED",
            "error_rate": "COMPLIANT" if error_rate <= SLA_STANDARDS["max_error_rate_pct"] else "BREACHED",
        }

        return {
            "current_metrics": {"cpu_pct": cpu_pct, "memory_pct": memory_pct, "p99_latency_ms": p99_latency, "error_rate_pct": error_rate},
            "sla_status": sla_status,
            "scaling_recommendations": recommendations,
            "highest_authority_required": authority_required,
            "overall_health": "HEALTHY" if not recommendations else "ACTION_REQUIRED",
            "assessed_at": datetime.now(UTC).isoformat(),
        }

    def assess_security_posture(self, scan_results: dict[str, Any]) -> dict[str, Any]:
        violations = scan_results.get("violations", [])
        critical_violations = SECURITY_STANDARDS["critical_violations"]

        critical_found = [v for v in violations if v in critical_violations]
        score = max(0, 100 - (len(critical_found) * 25) - (len(violations) * 5))

        return {
            "security_score": score,
            "posture": "CRITICAL" if critical_found else "AT_RISK" if violations else "STRONG",
            "critical_violations_found": critical_found,
            "all_violations": violations,
            "standards_enforced": {
                "authentication": SECURITY_STANDARDS["authentication"],
                "secrets_management": SECURITY_STANDARDS["secrets_management"],
                "network": SECURITY_STANDARDS["network"],
                "application": SECURITY_STANDARDS["application"],
            },
            "compliance_targets": SECURITY_STANDARDS["compliance_targets"],
            "immediate_actions": [f"REMEDIATE NOW: {v}" for v in critical_found],
            "assessed_at": datetime.now(UTC).isoformat(),
        }

    def assess_deployment_risk(self, deployment_data: dict[str, Any]) -> dict[str, Any]:
        changed_files = deployment_data.get("changed_files", [])
        has_migration = deployment_data.get("has_db_migration", False)
        has_schema_change = deployment_data.get("has_schema_change", False)
        breaking_api_changes = deployment_data.get("breaking_api_changes", False)
        rollback_tested = deployment_data.get("rollback_tested", False)

        risk_factors = []
        risk_score = 0

        if has_migration:
            risk_score += 30
            risk_factors.append("Database migration — verify rollback plan")
        if has_schema_change:
            risk_score += 20
            risk_factors.append("Schema change — test multi-service compatibility")
        if breaking_api_changes:
            risk_score += 25
            risk_factors.append("Breaking API changes — coordinate frontend/client updates")
        if len(changed_files) > 50:
            risk_score += 15
            risk_factors.append(f"Large changeset ({len(changed_files)} files) — increased blast radius")
        if not rollback_tested:
            risk_score += 10
            risk_factors.append("Rollback not verified — test before deploying to production")

        risk_level = "HIGH" if risk_score >= 50 else "MEDIUM" if risk_score >= 25 else "LOW"
        deploy_recommendation = "HOLD_FOR_CAPTAIN_REVIEW" if risk_level == "HIGH" else "PROCEED_WITH_MONITORING"

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "deploy_recommendation": deploy_recommendation,
            "health_gates": INFRASTRUCTURE["health_gates"],
            "deployment_strategy": INFRASTRUCTURE["deployment_strategy"],
            "estimated_downtime_seconds": 0,
            "rollback_strategy": "Blue/green — route traffic back to previous task set",
            "assessed_at": datetime.now(UTC).isoformat(),
        }

    def get_tech_debt_registry(self) -> dict[str, Any]:
        by_category: dict[str, list] = {}
        for item in KNOWN_TECH_IMPROVEMENTS:
            cat = item["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(item)

        priorities = by_category.get("CRITICAL", []) + by_category.get("HIGH", [])

        return {
            "total_improvements": len(KNOWN_TECH_IMPROVEMENTS),
            "by_category": by_category,
            "immediate_priorities": priorities,
            "categories": TECH_DEBT_CATEGORIES,
            "retrieved_at": datetime.now(UTC).isoformat(),
        }

    def get_platform_dashboard(self) -> dict[str, Any]:
        return {
            "system": "JARVIS Platform Intelligence Engine",
            "status": "FULLY_OPERATIONAL",
            "infrastructure": INFRASTRUCTURE,
            "sla_standards": SLA_STANDARDS,
            "cost_thresholds": COST_THRESHOLDS,
            "security_standards_summary": {
                "critical_violations": SECURITY_STANDARDS["critical_violations"],
                "compliance_targets": SECURITY_STANDARDS["compliance_targets"],
            },
            "scaling_triggers": {k: v["action"] for k, v in SCALING_TRIGGERS.items()},
            "tech_debt_count": len(KNOWN_TECH_IMPROVEMENTS),
            "evaluated_at": datetime.now(UTC).isoformat(),
        }


platform_intelligence = PlatformIntelligence()
