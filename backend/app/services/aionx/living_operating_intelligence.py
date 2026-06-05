"""AIONX living operating intelligence blueprint.

This module turns the recovered AXIOM/AIONX architecture notes into a live,
queryable operating layer. It does not claim external feeds are already crawling
the internet; it exposes the doctrine, dependencies, cycles, governance, and
current live-system coverage so the dashboard can show what exists and what is
still pending production wiring.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.departments.axiom_operating_model import (
    AXIOM_DEPARTMENTS,
    COMMERCIAL_GATEWAYS,
)
from app.services.aionx.operational_integrity import operational_integrity_status
from app.services.aionx.operational_persistence import operational_persistence_status
from app.services.aionx.sovereign_organs import sovereign_organs_status, system_state_snapshot
from app.services.aionx.supreme_council_layer import supreme_council_status
from app.services.aionx.ultimate_client_journey import (
    preventive_monitoring_status,
    ultimate_journey_status,
)


ADAPTIVE_CYCLES: list[dict[str, Any]] = [
    {
        "code": "SELF_OBSERVE",
        "name": "Self Observe",
        "cadence": "every_15_minutes",
        "purpose": "Scan 25 department health, revenue velocity, conversion, cost burn, client signals, reliability, and memory growth.",
        "outputs": ["health_scorecards", "threshold_alerts", "cortex_events"],
        "authority": "tier_1_measurement",
        "status": "doctrine_live_pending_metric_backbone",
    },
    {
        "code": "SELF_LEARN",
        "name": "Self Learn",
        "cadence": "daily",
        "purpose": "Synthesize lead outcomes, proposal results, client calls, workflow bottlenecks, competitor moves, and technology releases.",
        "outputs": ["learning_records", "knowledge_updates", "civilization_memory"],
        "authority": "tier_1_memory",
        "status": "partially_live_via_memory_and_knowledge_routes",
    },
    {
        "code": "SELF_IMPROVE",
        "name": "Self Improve",
        "cadence": "weekly",
        "purpose": "Rewrite weak prompts, improve workflows, tune scoring, adjust thresholds, and propose process changes.",
        "outputs": ["improvement_backlog", "council_review_items", "implementation_directives"],
        "authority": "tier_2_with_council_review",
        "status": "doctrine_live_pending_scheduler_wiring",
    },
    {
        "code": "SELF_EXPAND",
        "name": "Self Expand",
        "cadence": "monthly",
        "purpose": "Identify new market niches, new capabilities, pricing updates, case studies, and module expansion opportunities.",
        "outputs": ["capability_proposals", "pricing_recommendations", "new_service_specs"],
        "authority": "tier_3_for_new_service_launches",
        "status": "governed_design_live",
    },
    {
        "code": "SELF_ADAPT",
        "name": "Self Adapt",
        "cadence": "continuous",
        "purpose": "Adjust outreach, deployment, retention, positioning, and module priority as live metrics drift.",
        "outputs": ["runtime_adjustments", "strategy_shifts", "captain_alerts_when_threshold_crossed"],
        "authority": "tier_1_or_tier_2_until_irreversible_change",
        "status": "policy_live_pending_full_metric_backbone",
    },
]


TECH_EXPLORATION_SOURCES: list[dict[str, Any]] = [
    {"source": "Anthropic", "domain": "frontier_ai", "signal": "model releases, context windows, agent workflows"},
    {"source": "OpenAI", "domain": "frontier_ai", "signal": "models, tools, orchestration, safety capabilities"},
    {"source": "Google DeepMind", "domain": "frontier_ai", "signal": "research releases, agent planning, multimodal systems"},
    {"source": "Mistral", "domain": "frontier_ai", "signal": "open models, enterprise deployment options"},
    {"source": "GitHub Trending", "domain": "engineering", "signal": "AI, DevOps, security, infra repositories"},
    {"source": "ArXiv", "domain": "research", "signal": "cs.AI, cs.LG, cs.CL, cs.NE papers"},
    {"source": "HuggingFace", "domain": "models", "signal": "new open-source models and benchmarks"},
    {"source": "AWS", "domain": "cloud", "signal": "compute, storage, security, cost, data services"},
    {"source": "GCP", "domain": "cloud", "signal": "AI platform, data, infra, security updates"},
    {"source": "Azure", "domain": "cloud", "signal": "enterprise AI, security, identity, infra updates"},
    {"source": "ProductHunt", "domain": "market", "signal": "new AI products, SaaS trends, customer demand"},
    {"source": "Competitor Pricing", "domain": "market", "signal": "packaging, positioning, margins, offers"},
    {"source": "Enterprise Acquisitions", "domain": "market", "signal": "consolidation, strategic gaps, buyer demand"},
]


TWELVE_STAGE_REVENUE_PIPELINE: list[dict[str, Any]] = [
    {"stage": 1, "name": "World Scan", "owner": "SCOUT", "output": "new target companies"},
    {"stage": 2, "name": "Lead Discovery", "owner": "SCOUT", "output": "enriched lead records"},
    {"stage": 3, "name": "Lead Scoring", "owner": "ORACLE-S", "output": "ranked lead queue"},
    {"stage": 4, "name": "Business Analysis", "owner": "MARKET", "output": "pain and opportunity profile"},
    {"stage": 5, "name": "Case Study Match", "owner": "QUILL", "output": "proof narrative"},
    {"stage": 6, "name": "Outreach Draft", "owner": "HERALD", "output": "personalized email"},
    {"stage": 7, "name": "Council Review", "owner": "AXIOM COUNCIL", "output": "risk and quality decision"},
    {"stage": 8, "name": "Auto Optimize", "owner": "PRISM", "output": "improved offer and message"},
    {"stage": 9, "name": "Send Email", "owner": "HERALD", "output": "compliant send event"},
    {"stage": 10, "name": "Monitor Reply", "owner": "NEXUS-R", "output": "reply and speed-to-lead action"},
    {"stage": 11, "name": "Learn", "owner": "SELF_LEARN", "output": "conversion insight"},
    {"stage": 12, "name": "Update Knowledge", "owner": "MEMORY", "output": "institutional memory update"},
]


MODULE_DEPENDENCIES: dict[str, dict[str, Any]] = {
    "SCOUT": {"depends_on": [], "pauses_if": [], "activates": ["HERALD", "ORACLE-S"]},
    "HERALD": {"depends_on": ["SCOUT"], "pauses_if": ["SCOUT"], "activates": ["NEXUS-R"]},
    "NEXUS-R": {"depends_on": ["HERALD"], "pauses_if": [], "activates": ["ORACLE-S", "BRIDGE"]},
    "ORACLE-S": {"depends_on": ["SCOUT", "NEXUS-R"], "pauses_if": [], "activates": ["QUANT"]},
    "PRISM": {"depends_on": ["NEXUS-R"], "pauses_if": [], "activates": ["ECHO", "SIGNAL"]},
    "ECHO": {"depends_on": ["PRISM"], "pauses_if": ["PRISM"], "activates": ["RADAR"]},
    "PULSE": {"depends_on": ["BRIDGE"], "pauses_if": [], "activates": ["QUILL"]},
    "SIGNAL": {"depends_on": ["PRISM"], "pauses_if": [], "activates": ["BRIDGE"]},
    "BRIDGE": {"depends_on": ["NEXUS-R"], "pauses_if": [], "activates": ["PULSE"]},
    "ATLAS-CI": {"depends_on": [], "pauses_if": [], "activates": ["NEXUS-TF", "RADAR", "CIPHER"]},
    "NEXUS-TF": {"depends_on": ["ATLAS-CI"], "pauses_if": ["ATLAS-CI"], "activates": ["SIGNAL-CD"]},
    "SIGNAL-CD": {"depends_on": ["NEXUS-TF"], "pauses_if": [], "activates": ["HELM", "RADAR"]},
    "HELM": {"depends_on": ["SIGNAL-CD"], "pauses_if": [], "activates": ["RADAR"]},
    "RADAR": {"depends_on": ["ATLAS-CI"], "pauses_if": [], "activates": ["CIPHER", "GUARDIAN"]},
    "CIPHER": {"depends_on": ["RADAR"], "pauses_if": [], "activates": ["GUARDIAN", "LEDGER"]},
    "GUARDIAN": {"depends_on": ["CIPHER"], "pauses_if": [], "activates": ["LEDGER"]},
    "LEDGER": {"depends_on": ["CIPHER"], "pauses_if": [], "activates": []},
    "ORACLE-BI": {"depends_on": ["NEXUS-R"], "pauses_if": [], "activates": ["MARKET", "QUANT"]},
    "MARKET": {"depends_on": [], "pauses_if": [], "activates": ["QUILL"]},
    "QUANT": {"depends_on": ["ORACLE-BI"], "pauses_if": [], "activates": ["QUILL"]},
    "QUILL": {"depends_on": ["ORACLE-BI", "MARKET"], "pauses_if": [], "activates": []},
    "PORTAL": {"depends_on": ["CANVAS"], "pauses_if": [], "activates": ["VISION"]},
    "CANVAS": {"depends_on": ["ORACLE-BI"], "pauses_if": [], "activates": ["PORTAL", "VISION"]},
    "VISION": {"depends_on": ["CANVAS"], "pauses_if": [], "activates": []},
    "AXIOM COUNCIL": {"depends_on": [], "pauses_if": [], "activates": ["all_governed_recommendations"]},
}


METRIC_BACKBONE: list[dict[str, str]] = [
    {"metric": "department_health", "unit": "0_100", "source": "AXIOM pulse", "owner": "SELF_OBSERVE"},
    {"metric": "pipeline_velocity", "unit": "stage_days", "source": "client pipeline", "owner": "Cortex"},
    {"metric": "reply_rate", "unit": "percent", "source": "outreach emails", "owner": "HERALD"},
    {"metric": "positive_reply_rate", "unit": "percent", "source": "reply log", "owner": "NEXUS-R"},
    {"metric": "ai_cost_burn", "unit": "usd_per_day", "source": "AI ops", "owner": "FINANCIER"},
    {"metric": "wisdom_score", "unit": "index", "source": "wisdom snapshots", "owner": "Wisdom Index"},
    {"metric": "operational_iq", "unit": "0_100", "source": "Cortex", "owner": "JARVIS"},
    {"metric": "client_trust", "unit": "0_100", "source": "digital twins", "owner": "Client Trust Index"},
    {"metric": "system_reliability", "unit": "percent", "source": "health checks", "owner": "RADAR"},
    {"metric": "decision_debt", "unit": "usd", "source": "decision debt", "owner": "Council"},
]


async def adaptive_intelligence_status(db: AsyncSession | None = None) -> dict[str, Any]:
    live_jobs: list[str] = []
    if db is not None:
        live_jobs = await _matching_jobs(db, ["adaptive", "learning", "optimization", "aionx"])
    return {
        "status": "operational_doctrine_live",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": "Five self-evolution cycles are now canonical and visible. Production automation remains approval-governed.",
        "cycle_count": len(ADAPTIVE_CYCLES),
        "cycles": ADAPTIVE_CYCLES,
        "live_scheduler_evidence": live_jobs,
        "governance": {
            "captain_boundary": "Captain approves Tier 3 only: contracts, payments, production go-live, new services, strategic pivots.",
            "council_boundary": "Council reviews recommendations and risks; it does not bypass JARVIS or Captain approval.",
            "self_modification_boundary": "No direct self-merging code. Changes must be reviewable, reversible, and approval-gated.",
        },
    }


def technology_exploration_status() -> dict[str, Any]:
    return {
        "status": "watchtower_defined",
        "source_count": len(TECH_EXPLORATION_SOURCES),
        "sources": TECH_EXPLORATION_SOURCES,
        "classification_flow": [
            "discover",
            "classify_relevance_0_100",
            "map_to_capability_modules",
            "estimate_cost_benefit",
            "submit_to_council",
            "adopt_reject_or_shelve",
            "update_memory",
        ],
        "adoption_rule": "Technology can be recommended autonomously, but irreversible adoption remains Tier 2/3 governed.",
    }


def revenue_pipeline_status() -> dict[str, Any]:
    return {
        "status": "canonical_12_stage_pipeline_defined",
        "stage_count": len(TWELVE_STAGE_REVENUE_PIPELINE),
        "stages": TWELVE_STAGE_REVENUE_PIPELINE,
        "relationship_to_batch1": "This is the compact revenue pipeline view; Batch 1 remains the full 33-stage client operating doctrine.",
        "gateways": [
            {"gateway": gateway["name"], "success_metric": gateway["success_metric"], "retainer_range": gateway["retainer_range"]}
            for gateway in COMMERCIAL_GATEWAYS
        ],
    }


def module_dependency_status() -> dict[str, Any]:
    return {
        "status": "resolver_defined",
        "module_count": len(MODULE_DEPENDENCIES),
        "dependencies": MODULE_DEPENDENCIES,
        "failure_rules": [
            "If SCOUT cannot discover or enrich leads, HERALD pauses outbound sends.",
            "If HERALD send/reply handling fails, NEXUS-R receives no conversion signal and forecasting downgrades confidence.",
            "If RADAR detects infra instability, CIPHER and GUARDIAN escalate security posture.",
            "If AXIOM COUNCIL rejects a recommendation, JARVIS shelves it with wake conditions.",
        ],
    }


async def data_backbone_status(db: AsyncSession) -> dict[str, Any]:
    tables = await _existing_tables(db)
    expected_groups = {
        "leads_pipeline": ["leads", "prospect_psychology_profiles", "prospect_emotional_profiles", "follow_up_queue"],
        "outreach_execution": ["outreach_sequences", "outreach_emails", "outreach_log", "reply_log", "email_tracking"],
        "intelligence_memory": ["knowledge_base", "learning_records", "outreach_learnings", "memory_graph_nodes", "memory_graph_edges", "civilization_memory"],
        "analysis_council": ["ai_council_sessions", "expert_council_sessions", "market_intelligence", "competitor_profiles", "research_reports"],
        "client_revenue": ["clients", "companies", "contacts", "deals", "proposals", "invoices", "revenue_forecasts"],
        "operations_governance": ["department_intelligence_officers", "department_milestones", "autonomous_governance_log", "approval_requests", "audit_logs", "apscheduler_jobs"],
        "technology_evolution": ["technology_discoveries", "tech_radar_entries", "innovation_queue", "jarvis_upgrade_plans"],
        "aionx_organs": ["decision_objects", "client_digital_twins", "wisdom_index_snapshots", "sentinel_observations", "convergence_council_sessions", "mission_autopsies"],
    }
    groups = {}
    for group, names in expected_groups.items():
        live = [name for name in names if name in tables]
        groups[group] = {
            "expected": len(names),
            "live": len(live),
            "missing": [name for name in names if name not in tables],
            "tables": live,
        }
    return {
        "status": "live_database_inspected",
        "total_live_tables": len(tables),
        "expected_reference_tables": sum(len(names) for names in expected_groups.values()),
        "groups": groups,
        "backbone_rules": [
            "Every production action must be auditable.",
            "Every client or tenant-facing record must preserve tenant context where the model supports it.",
            "Operational metrics must map to business outcomes, not only service uptime.",
            "Memory writes should be tied to source events and confidence.",
        ],
    }


def gateway_experience_status() -> dict[str, Any]:
    return {
        "status": "three_gateway_experience_defined",
        "client_visibility_rule": "Clients see diagnosis, outcomes, dashboards, and recommendations - not internal departments as a menu.",
        "gateways": COMMERCIAL_GATEWAYS,
        "department_count": len(AXIOM_DEPARTMENTS),
        "ux_surfaces": [
            "AXIOM Outreach: pipeline, reply quality, revenue trajectory, next best action.",
            "AXIOM CloudOps: cost before/after, uptime, deployment velocity, security posture.",
            "AXIOM Council: quarterly intelligence, competitor landscape, forecast, board-ready recommendations.",
        ],
    }


async def captain_interface_status(db: AsyncSession | None = None) -> dict[str, Any]:
    pending_jobs = []
    if db is not None:
        pending_jobs = await _matching_jobs(db, ["briefing", "approval", "council", "aionx"])
    return {
        "status": "captain_operating_boundary_defined",
        "daily_mode": "120-word morning briefing plus one decision if needed.",
        "weekly_mode": "Council intelligence report, 25 department health scores, revenue trajectory, three recommendations.",
        "quarterly_mode": "Captain sets strategic constraints; JARVIS reconfigures modules accordingly.",
        "visible_to_captain": ["Tier 3 approvals", "strategic reports", "health exceptions", "contracts/payments/go-live decisions"],
        "hidden_from_captain": ["routine lead scoring", "CRM hygiene", "Tier 1 outreach", "routine learning", "internal prompt tuning"],
        "live_scheduler_evidence": pending_jobs,
    }


async def full_operating_intelligence(db: AsyncSession) -> dict[str, Any]:
    return {
        "status": "operational_intelligence_surface_live",
        "brand": "AXIOM",
        "internal_engine": "AIONX",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "adaptive_intelligence": await adaptive_intelligence_status(db),
        "technology_exploration": technology_exploration_status(),
        "revenue_pipeline": revenue_pipeline_status(),
        "module_dependencies": module_dependency_status(),
        "data_backbone": await data_backbone_status(db),
        "gateway_experience": gateway_experience_status(),
        "captain_interface": await captain_interface_status(db),
        "operational_integrity": operational_integrity_status(),
        "operational_persistence": await operational_persistence_status(db),
        "sovereign_organs": sovereign_organs_status(),
        "supreme_council": await supreme_council_status(db),
        "system_state": system_state_snapshot(),
        "ultimate_journey": ultimate_journey_status(),
        "preventive_monitoring": preventive_monitoring_status(),
    }


async def _matching_jobs(db: AsyncSession, needles: list[str]) -> list[str]:
    try:
        result = await db.execute(text("SELECT id FROM apscheduler_jobs ORDER BY id"))
        job_ids = [str(row[0]) for row in result.fetchall()]
    except Exception:
        return []
    lowered_needles = [needle.lower() for needle in needles]
    return [job for job in job_ids if any(needle in job.lower() for needle in lowered_needles)]


async def _existing_tables(db: AsyncSession) -> set[str]:
    result = await db.execute(
        text(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            """
        )
    )
    return {str(row[0]) for row in result.fetchall()}
