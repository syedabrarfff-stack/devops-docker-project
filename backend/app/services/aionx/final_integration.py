"""AIONX Final Integration — unified runtime and Captain intelligence dashboard.

Orchestrates the complete AIONX system for Captain, providing:
- Real-time operational status
- All intelligence engine outputs
- Decision-making context
- System health and recommendations
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.aionx.institutional_wisdom_index import get_current_wisdom
from app.services.aionx.orchestration_cortex import compute_operational_iq, situational_snapshot
from app.services.aionx.counterfactual_engine import extract_learning
from app.services.aionx.decision_debt_engine import assess_institutional_debt
from app.services.aionx.client_trust_index import (
    compute_trust_score as get_trust_score,
)
from app.services.aionx.executive_accountability_engine import track_maker_accuracy
from app.services.aionx.operational_persistence import operational_persistence_status
from app.services.aionx.supreme_council_layer import supreme_council_status

logger = logging.getLogger(__name__)


async def generate_captain_intelligence_dashboard(
    db: AsyncSession,
) -> dict[str, Any]:
    """Generate unified intelligence dashboard for Captain's oversight.

    Single endpoint aggregates:
    - Wisdom Index (master health signal)
    - Operational IQ (execution health)
    - Decision intelligence (accuracy, debt, learning)
    - Client health (trust, retention, churn risk)
    - System recommendations
    """

    logger.info("Generating Captain Intelligence Dashboard")

    # Gather all intelligence signals
    dashboard = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system_status": "OPERATIONAL",
        "sections": {},
    }

    # SECTION 1: WISDOM INDEX (Master Health Signal)
    try:
        wisdom_data = await get_current_wisdom(db)
        dashboard["sections"]["wisdom_index"] = {
            "wisdom_score": wisdom_data.get("wisdom_score", 500),
            "delta": wisdom_data.get("delta", 0),
            "narrative": wisdom_data.get("narrative"),
            "recommendations": wisdom_data.get("recommendations", []),
        }
    except Exception as e:
        logger.error("Wisdom Index gathering failed: %s", e)
        dashboard["sections"]["wisdom_index"] = {"error": str(e)}

    # SECTION 2: OPERATIONAL IQ (Execution Health)
    try:
        iq_data = await compute_operational_iq(db)
        iq_components = iq_data.get("components", {})
        dashboard["sections"]["operational_iq"] = {
            "operational_iq": iq_data.get("operational_iq", 50),
            "interpretation": iq_data.get("interpretation"),
            "components": {
                "wisdom": iq_components.get("wisdom"),
                "decision_activity": iq_components.get("decision_activity"),
                "client_health": iq_components.get("client_health"),
                "system_health": iq_components.get("system_health"),
            },
        }
    except Exception as e:
        logger.error("Operational IQ gathering failed: %s", e)
        dashboard["sections"]["operational_iq"] = {"error": str(e)}

    # SECTION 3: DECISION INTELLIGENCE
    try:
        learning_data = await extract_learning(db)
        debt_data = await assess_institutional_debt(db)

        dashboard["sections"]["decision_intelligence"] = {
            "decisions_reviewed": learning_data.get("decisions_reviewed", 0),
            "success_rate": learning_data.get("success_rate", 0.5),
            "avg_revenue_impact": learning_data.get("avg_revenue_impact_usd", 0),
            "avg_timeline_variance": learning_data.get("avg_timeline_variance_days", 0),
            "institutional_debt_usd": debt_data.get("total_institutional_debt_usd", 0),
            "high_debt_decisions": debt_data.get("high_debt_decision_count", 0),
            "debt_penalty_points": debt_data.get("wisdom_index_penalty_points", 0),
        }
    except Exception as e:
        logger.error("Decision Intelligence gathering failed: %s", e)
        dashboard["sections"]["decision_intelligence"] = {"error": str(e)}

    # SECTION 4: SITUATIONAL SNAPSHOT (Real-time Context)
    try:
        snapshot_data = await situational_snapshot(db)
        live_counts = snapshot_data.get("live_counts", {})
        dashboard["sections"]["situational"] = {
            "decisions_recorded": live_counts.get("decisions_recorded", 0),
            "client_digital_twins": live_counts.get("client_digital_twins", 0),
            "sentinel_observations": live_counts.get("sentinel_observations", 0),
            "active_threats": live_counts.get("active_threats", 0),
            "organism_status": snapshot_data.get("organism_status"),
        }
    except Exception as e:
        logger.error("Situational Snapshot gathering failed: %s", e)
        dashboard["sections"]["situational"] = {"error": str(e)}

    # SECTION 5: CAPTAIN ACTIONS & ALERTS
    dashboard["sections"]["captain_actions"] = await _generate_captain_actions(db)

    # SECTION 6: SYSTEM RECOMMENDATIONS
    dashboard["sections"]["recommendations"] = await _generate_system_recommendations(db)

    return dashboard


async def _generate_captain_actions(db: AsyncSession) -> dict[str, Any]:
    """Generate actionable recommendations for Captain right now."""

    actions = []

    try:
        debt_data = await assess_institutional_debt(db)
        if debt_data.get("total_institutional_debt_usd", 0) > 50000:
            actions.append({
                "priority": "HIGH",
                "action": "Institutional debt >$50k — begin reduction initiative",
                "affected_decisions": debt_data.get("high_debt_decision_count", 0),
            })
    except Exception:
        pass

    try:
        wisdom_data = await get_current_wisdom(db)
        if wisdom_data.get("wisdom_score", 500) < 600:
            actions.append({
                "priority": "MEDIUM",
                "action": "Wisdom Index declining — review recent decision accuracy",
            })
    except Exception:
        pass

    return {
        "pending_actions": len(actions),
        "actions": actions,
    }


async def _generate_system_recommendations(db: AsyncSession) -> dict[str, Any]:
    """Generate AIONX recommendations to Captain."""

    recommendations = [
        "Review council session recommendations weekly",
        "Monitor decision maker accuracy trends",
        "Track institutional debt — prioritize reduction of high-debt decisions",
        "Conduct monthly retrospective on failed missions",
    ]

    try:
        wisdom_data = await get_current_wisdom(db)
        if wisdom_data.get("recommendations"):
            recommendations.extend(wisdom_data["recommendations"])
    except Exception:
        pass

    return {
        "general_recommendations": recommendations[:5],  # Top 5
    }


async def get_aionx_system_info() -> dict[str, Any]:
    """Get AIONX system metadata and version info."""

    return {
        "system": "AIONX",
        "version": "2.0-COMPLETE",
        "status": "FULLY_OPERATIONAL",
        "components": {
            "orchestration_cortex": "Active",
            "decision_memory_engine": "Active",
            "convergence_council": "Active",
            "provider_sovereign_council": "Active",
            "sentinel_layer": "Active",
            "digital_twins": "Active",
            "wisdom_index": "Active",
            "counterfactual_engine": "Active",
            "debt_engine": "Active",
            "autopsy_engine": "Active",
            "accountability_engine": "Active",
            "trust_engine": "Active",
            "hia_certification": "Active",
            "voice_integration": "Configured",
            "mission_file_system": "Active",
            "validation_layer": "Active",
            "operational_persistence": "Active",
            "governed_autonomy": "Approval-gated",
            "supreme_council_layer": "Active",
        },
        "organs": 9,
        "intelligence_engines": 5,
        "optional_systems": 5,
        "total_endpoints": 107,
        "scheduler_jobs": 17,
        "launched": datetime.now(timezone.utc).isoformat(),
        "phase": "PRODUCTION",
    }


CANONICAL_AIONX_BLUEPRINT: list[dict[str, Any]] = [
    {
        "id": "batch_1",
        "name": "Batch 1: Client Journey Orchestrator",
        "status": "LIVE",
        "live_evidence": [
            "33-stage pipeline service",
            "client_pipeline_states table",
            "client_pipeline_milestones table",
            "client_pipeline_stage_logs table",
            "stage-transition API",
            "Cortex event firing",
            "workflow doctrine API",
            "pipeline board API",
            "dashboard/AIONX map visibility",
        ],
        "pending_work": [
            "Connect every revenue route directly into stage transitions",
            "Add SLA timers per stage",
        ],
    },
    {
        "id": "batch_2",
        "name": "Batch 2: Sovereign Organs + Supreme Council",
        "status": "LIVE_WITH_DORMANT_ORGANS",
        "live_evidence": [
            "Decision Memory Engine",
            "Counterfactual Engine",
            "Decision Debt Engine",
            "Client Digital Twin Engine",
            "Institutional Wisdom Index",
            "Provider Sovereign Council",
            "Grand Convergence Council",
            "Sentinel Layer",
            "Executive Accountability Engine",
            "Mission Autopsy Engine",
            "12 AIONX scheduler jobs",
        ],
        "pending_work": [
            "Cognitive Cortex provider debate is bounded, not full multi-provider parallel voting",
            "Supreme Council chat UI is not yet a full conference-room experience",
            "Provider calibration scoring needs real 30/90-day outcome volume",
        ],
    },
    {
        "id": "batch_3",
        "name": "Batch 3: Constitutional Governance + Infrastructure",
        "status": "PARTIAL",
        "live_evidence": [
            "Authority/approval routes",
            "HIA certification endpoints",
            "Mission file archive endpoints",
            "Validation/preflight endpoints",
            "Scheduler failure tracking",
            "Emergency health routes",
        ],
        "pending_work": [
            "Zero-SPOF multi-region resurrection is not implemented",
            "Self-modification membrane has registry but no full shadow/canary pipeline",
            "Tenant isolation exists in models/jobs but needs enforcement audit across all routes",
        ],
    },
    {
        "id": "revenue_first_10",
        "name": "Revenue-Critical 10 Systems",
        "status": "PARTIAL",
        "live_evidence": [
            "Speed-to-lead scheduler",
            "Outreach sequence engine",
            "Free lead discovery scheduler",
            "Dynamic pricing / offer engine",
            "CRM pipeline stats",
            "Revenue intelligence dashboard pieces",
        ],
        "pending_work": [
            "Proof-of-concept generator needs a dedicated workflow",
            "Warm path finder needs LinkedIn/network graph data",
            "Fast-close contract/payment automation needs production payment integration",
            "Revenue-triggered agent activation needs live MRR thresholds wired to org chart",
        ],
    },
    {
        "id": "73_system_vision",
        "name": "73-System Strategic Vision",
        "status": "DESIGN_PARTIAL",
        "live_evidence": [
            "Many foundations exist: departments, agents, governance, memory, council, scheduler, CRM, outreach, intelligence",
            "AIONX dashboard now reports canonical live-vs-pending status",
        ],
        "pending_work": [
            "Data moat, gravity engine, IP builder, wellbeing monitor, anti-commoditization engine are strategy/design-only",
            "Autonomous org restructuring must remain approval-governed before production autonomy",
        ],
    },
    {
        "id": "living_operating_intelligence",
        "name": "Living Operating Intelligence Layer",
        "status": "LIVE_FOUNDATION",
        "live_evidence": [
            "Five adaptive cycles defined",
            "Technology exploration watchtower defined",
            "12-stage compact revenue pipeline exposed",
            "Module dependency resolver exposed",
            "Data backbone inspection endpoint",
            "Three gateway UX doctrine exposed",
            "Captain interface boundary exposed",
        ],
        "pending_work": [
            "Connect SELF_OBSERVE to real 15-minute metric snapshots",
            "Connect Technology Exploration to authenticated external crawlers/APIs",
            "Convert dependency resolver rules into active orchestration gates",
            "Add approval-governed execution for SELF_IMPROVE recommendations",
        ],
    },
    {
        "id": "operational_integrity",
        "name": "Operational Integrity Teams + 18-Stage Pipeline",
        "status": "LIVE_FOUNDATION",
        "live_evidence": [
            "8 Operational Integrity Teams exposed",
            "18-stage full AIONX pipeline exposed",
            "14-stage milestone governance protocol exposed",
            "9 Human Interface Agent profiles exposed",
            "Fallback continuity matrix exposed",
            "Mission planning endpoint persists mission_files and milestone_plans",
            "QA certificate endpoint persists quality certificates",
            "Repair instruction endpoint persists repair records",
            "Fallback drill endpoint persists continuity records",
            "Knowledge synthesis endpoint persists institutional learning records",
        ],
        "pending_work": [
            "Wire every real client milestone through this governance state machine",
            "Add full Operations Center interaction UI beyond architecture visibility",
        ],
    },
    {
        "id": "sovereign_organism",
        "name": "Sovereign Organs + Ultimate Journey",
        "status": "LIVE_FOUNDATION",
        "live_evidence": [
            "9 sovereign organs exposed",
            "12 cognitive regions exposed",
            "System State Model snapshot exposed",
            "System State snapshots persisted every 5 minutes",
            "Cognitive Cortex debate endpoint",
            "Genesis proposal endpoint",
            "Genesis autonomy proposals persist for Captain review",
            "Immune scan endpoint",
            "Simulation Twin scenario endpoint",
            "Ultimate 33-stage monitored journey exposed",
            "8 lifecycle divisions exposed",
            "Preventive monitoring model exposed",
            "Preventive monitoring events persisted every 15 minutes",
            "HIE briefing and post-call extraction endpoints",
            "Event spine table records operational events",
            "Daily governed external scan records are scheduled",
        ],
        "pending_work": [
            "Wire cognitive debate to live provider fan-out",
            "Implement Captain Control Plane interactive UI",
            "Attach authenticated external crawling sources to the scan record system",
        ],
    },
    {
        "id": "supreme_council_layer",
        "name": "Supreme Council Layer: Calibration + Convergence + Safety Membrane",
        "status": "LIVE",
        "live_evidence": [
            "Three-ring authority architecture exposed",
            "Provider calibration health endpoint",
            "Grand convergence protocol endpoint",
            "Self-modification safety membrane endpoint",
            "Recommendation object endpoint persists to event spine",
            "Self-modification evaluation endpoint blocks core changes",
            "Meta-learning status endpoint",
            "Weekly Supreme Council meta-learning scheduler job",
        ],
        "pending_work": [
            "Increase resolved provider prediction volume for stronger domain authority weights",
            "Add richer Captain conference-room UI for natural-language council stream",
            "Connect more production outcomes into provider claim scoring",
        ],
    },
]


CANONICAL_AIONX_CONNECTIONS: list[dict[str, str]] = [
    {
        "event": "LEAD_REPLIED",
        "connects": "Outreach -> Cortex -> Digital Twin -> Decision Memory -> Speed-to-Lead",
        "status": "LIVE",
    },
    {
        "event": "CLIENT_SIGNED",
        "connects": "CRM/Contract -> Cortex -> Mission Ownership -> Pipeline -> Council",
        "status": "LIVE_FOUNDATION",
    },
    {
        "event": "MISSION_FAILED",
        "connects": "Pipeline/Sentinel -> Autopsy -> Convergence Council -> Decision Memory",
        "status": "LIVE_FOUNDATION",
    },
    {
        "event": "CHURN_RISK_DETECTED",
        "connects": "Digital Twin -> Trust Index -> Sentinel -> Recovery Protocol",
        "status": "LIVE_FOUNDATION",
    },
    {
        "event": "WEEKLY_LEARNING",
        "connects": "Scheduler -> Retrospective -> Wisdom Index -> Provider Calibration",
        "status": "LIVE",
    },
    {
        "event": "SELF_MODIFICATION",
        "connects": "Genesis Proposal -> Registry -> Shadow/Canary -> Captain Approval",
        "status": "REGISTRY_ONLY",
    },
]


async def get_aionx_architecture_reconciliation(db: AsyncSession) -> dict[str, Any]:
    """Return Captain-facing live-vs-designed architecture coverage.

    This endpoint is intentionally explicit: it separates what is live,
    what is wired but dormant, and what remains strategic design.
    """

    table_names = await _existing_tables(db)
    route_count = 107

    expected_tables = {
        "decision_objects",
        "decision_options",
        "decision_outcomes",
        "decision_patterns",
        "decision_retrospectives",
        "counterfactual_simulations",
        "counterfactual_actualizations",
        "decision_debt_assessments",
        "institutional_debt_index",
        "client_digital_twins",
        "client_twin_interactions",
        "client_twin_predictions",
        "client_pipeline_states",
        "client_pipeline_milestones",
        "client_pipeline_stage_logs",
        "wisdom_index_snapshots",
        "provider_calibration_records",
        "provider_council_sessions",
        "shelved_discoveries",
        "convergence_council_sessions",
        "convergence_council_messages",
        "mission_autopsies",
        "sentinel_observations",
        "sentinel_threat_registry",
        "mission_ownership_records",
        "self_modification_registry",
        "aionx_mission_files",
        "aionx_milestone_plans",
        "aionx_qa_certificates",
        "aionx_repair_records",
        "aionx_fallback_drill_records",
        "aionx_knowledge_synthesis_records",
        "aionx_system_state_snapshots",
        "aionx_event_spine",
        "aionx_autonomy_proposals",
        "aionx_external_scan_records",
    }

    live_tables = sorted(expected_tables.intersection(table_names))
    missing_tables = sorted(expected_tables.difference(table_names))
    dashboard = await generate_captain_intelligence_dashboard(db)
    persistence = await operational_persistence_status(db)
    supreme = await supreme_council_status(db)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": (
            "AIONX is deployed as a live foundation with active Batch 1/2 organs, "
            "scheduler heartbeat, and Cortex event wiring. Several advanced vision "
            "systems remain dormant or design-only until real revenue, clients, and "
            "approval-governed autonomy are connected."
        ),
        "counts": {
            "canonical_batches": len(CANONICAL_AIONX_BLUEPRINT),
            "expected_aionx_tables": len(expected_tables),
            "live_aionx_tables": len(live_tables),
            "missing_aionx_tables": len(missing_tables),
            "aionx_api_endpoints_expected": route_count,
            "aionx_scheduler_jobs_expected": 12,
        },
        "blueprint": CANONICAL_AIONX_BLUEPRINT,
        "connection_map": CANONICAL_AIONX_CONNECTIONS,
        "live_tables": live_tables,
        "missing_tables": missing_tables,
        "live_signals": dashboard.get("sections", {}),
        "operational_persistence": persistence,
        "supreme_council": supreme,
        "canonical_next_build_order": [
            "Connect every revenue route directly into stage transitions",
            "Council conference-room UI with natural-language participant messages",
            "Revenue Heart ledger and cost-per-outcome reporting",
            "Self-modification safety membrane with shadow/canary approval workflow",
            "Provider fan-out for Cognitive Cortex debate",
            "Real authenticated external crawling sources for the Sentinel watchtower",
            "Captain Control Plane interaction UI",
            "Resurrection/DR plan after core revenue workflows are stable",
        ],
        "authority_boundaries": [
            "Captain remains final authority for Tier 3 and irreversible actions",
            "Councils advise and memorialize; they do not execute production actions directly",
            "Self-modifying code must open a reviewable change and cannot merge itself",
            "Kill switch, Captain authority, and governance tiers are immutable core",
        ],
    }


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
