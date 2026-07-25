"""
Aliyar Solutions Service Catalog - canonical 10 AIONX capability modules.

Trimmed from 25 to 10 (Captain directive): the 10 kept are the fastest-closing,
highest-velocity offers for UK/US/CA/AU/EU SMB and mid-market buyers, plus the
two operational backbones (NEXUS-R, ATLAS-CI/SIGNAL-CD) the sellable modules
depend on. See docs/architecture/CATALOG_TRIM_2026-07.md for the removed-module
list and rationale.
"""
import logging
import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, func, select, update
from app.models.service_catalog import ServiceDivision

logger = logging.getLogger(__name__)
SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

# Canonical 25-module product architecture.

CAPABILITY_MODULES = [
    {
        "code": "SCOUT",
        "name": "Lead Intelligence",
        "division": "Revenue Operations",
        "human_interface_executive": "James Whitfield",
        "agent_layer": ["Lead discovery", "ICP scoring", "market signal analysis"],
        "kpi_targets": ["20 qualified discoveries/day", "lead quality trend", "source conversion"],
        "description": "Finds, enriches, scores, and prioritizes prospects before outreach begins.",
    },
    {
        "code": "HERALD",
        "name": "Outreach",
        "division": "Revenue Operations",
        "human_interface_executive": "Darren Mitchell",
        "agent_layer": ["Email sequencing", "reply handling", "personalization"],
        "kpi_targets": ["48 emails/day max", "reply rate", "positive intent rate"],
        "description": "Runs governed outreach with compliant sequencing, personalization, and response routing.",
    },
    {
        "code": "NEXUS-R",
        "name": "CRM Intelligence",
        "division": "Revenue Operations",
        "human_interface_executive": "Emma Collins",
        "agent_layer": ["CRM hygiene", "pipeline intelligence", "contact history"],
        "kpi_targets": ["clean lifecycle states", "deal velocity", "stale lead reduction"],
        "description": "Maintains revenue truth across CRM, contacts, deals, lifecycle state, and client context.",
    },
    {
        "code": "PRISM",
        "name": "Workflow Automation",
        "division": "AI Automation",
        "human_interface_executive": "Sophia Reynolds",
        "agent_layer": ["process mapping", "workflow design", "automation deployment"],
        "kpi_targets": ["manual hours removed", "automation uptime", "handoff accuracy"],
        "description": "Turns repeatable business operations into governed automated workflows.",
    },
    {
        "code": "PULSE",
        "name": "Voice Systems",
        "division": "AI Automation",
        "human_interface_executive": "Lucas Reed",
        "agent_layer": ["voice intake", "call transcription", "speech synthesis"],
        "kpi_targets": ["call coverage", "handoff accuracy", "voice response latency"],
        "description": "Creates voice-first client and operations interfaces for calls, reception, and briefings.",
    },
    {
        "code": "ATLAS-CI",
        "name": "AWS Architecture",
        "division": "Cloud & DevOps",
        "human_interface_executive": "David Carter",
        "agent_layer": ["cloud topology", "runtime design", "AWS governance"],
        "kpi_targets": ["uptime", "cost efficiency", "deployment readiness"],
        "description": "Designs AWS runtime foundations, networking, compute, storage, and production governance.",
    },
    {
        "code": "SIGNAL-CD",
        "name": "CI/CD",
        "division": "Cloud & DevOps",
        "human_interface_executive": "Nathan Scott",
        "agent_layer": ["build pipelines", "deployment gates", "rollback paths"],
        "kpi_targets": ["deploy success", "rollback time", "test gate coverage"],
        "description": "Automates build, test, deployment, rollback, and release governance.",
    },
    {
        "code": "CIPHER",
        "name": "Security Operations",
        "division": "Security & Compliance",
        "human_interface_executive": "Daniel Brooks",
        "agent_layer": ["access review", "threat monitoring", "security posture"],
        "kpi_targets": ["risk reduction", "IAM hygiene", "threat response"],
        "description": "Protects cloud, application, and operational surfaces with continuous security discipline.",
    },
    {
        "code": "QUILL",
        "name": "Executive Briefings",
        "division": "Intelligence & Data",
        "human_interface_executive": "Sophia Reynolds",
        "agent_layer": ["briefing synthesis", "meeting packs", "strategic narrative"],
        "kpi_targets": ["briefing quality", "prep time saved", "context completeness"],
        "description": "Packages complex operational context into clear Captain, client, and council briefings.",
    },
    {
        "code": "CANVAS",
        "name": "Dashboards",
        "division": "Digital Products",
        "human_interface_executive": "Michael Hayes",
        "agent_layer": ["dashboard UI", "live metrics", "decision screens"],
        "kpi_targets": ["load speed", "metric accuracy", "executive usability"],
        "description": "Creates operational dashboards that make system, client, and revenue state readable.",
    },
]


def get_capability_modules() -> dict:
    grouped: dict[str, list[dict]] = {}
    hia_index: dict[str, int] = {}
    for index, module in enumerate(CAPABILITY_MODULES, start=1):
        item = {"sort_order": index, **module}
        grouped.setdefault(module["division"], []).append(item)
        hia = module["human_interface_executive"]
        hia_index[hia] = hia_index.get(hia, 0) + 1

    return {
        "total": len(CAPABILITY_MODULES),
        "division_count": len(grouped),
        "hia_count": len(hia_index),
        "modules": [{"sort_order": index, **module} for index, module in enumerate(CAPABILITY_MODULES, start=1)],
        "groups": [
            {"division": division, "count": len(modules), "modules": modules}
            for division, modules in grouped.items()
        ],
        "governance_model": {
            "internal_owner": "Department Intelligence Officer",
            "client_voice": "Human Interface Executive",
            "execution_layer": "AI agents",
            "cadence": "Weekly Council cycle",
            "visibility": "Real-time health dashboard",
        },
        "operating_system": {
            "operational_integrity_layers": OPERATIONAL_INTEGRITY_LAYERS,
            "client_lifecycle_divisions": CLIENT_LIFECYCLE_DIVISIONS,
            "sovereign_organs": SOVEREIGN_ORGANS,
            "constitutional_systems": CONSTITUTIONAL_SYSTEMS,
            "adaptive_learning_loop": ADAPTIVE_LEARNING_LOOP,
            "authority_boundaries": AUTHORITY_BOUNDARIES,
            "integration_spine": INTEGRATION_SPINE,
        },
    }


OPERATIONAL_INTEGRITY_LAYERS = [
    {"layer": 1, "name": "Mission Control", "function": "Creates Mission Files, decomposes projects, maps dependencies, tracks timelines."},
    {"layer": 2, "name": "Cross-Department Review Board", "function": "Runs external validation, integration checks, and gap detection across modules."},
    {"layer": 3, "name": "Quality Assurance Team", "function": "Provides independent validation, defect detection, and certification authority."},
    {"layer": 4, "name": "Repair & Recovery Team", "function": "Diagnoses defects precisely, issues repair instructions, verifies recovery loops."},
    {"layer": 5, "name": "Fallback & Continuity Team", "function": "Detects agent failure and activates backup execution within 120 seconds."},
    {"layer": 6, "name": "Department Health Monitoring", "function": "Scores all 25 modules, trends performance, catches structural issues early."},
    {"layer": 7, "name": "Knowledge Synthesis Team", "function": "Extracts lessons, SOPs, case studies, and reusable delivery doctrine."},
    {"layer": 8, "name": "Preventive Monitoring Engine", "function": "Predicts failures, alerts before SLA breach, and triggers proactive scaling."},
]


CLIENT_LIFECYCLE_DIVISIONS = [
    {"name": "Onboarding", "function": "Converts signed clients into mission files, stakeholders, timelines, and success metrics."},
    {"name": "Success", "function": "Tracks value realization, health, expansion opportunities, and relationship depth."},
    {"name": "Support", "function": "Handles issues, SLA response, escalations, and client-care continuity."},
    {"name": "Feedback & VOC", "function": "Extracts client voice, sentiment, objections, product demand, and improvement signals."},
    {"name": "Reputation", "function": "Transforms delivered value into proof, testimonials, reviews, and case studies."},
    {"name": "Referral", "function": "Identifies warm introduction paths and referral expansion after relationship maturity."},
    {"name": "Postmortem", "function": "Runs structured retrospectives after project completion or major milestones."},
    {"name": "Knowledge Extraction", "function": "Feeds learnings into SOPs, memory, outreach intelligence, and adaptive evolution."},
]


SOVEREIGN_ORGANS = [
    "Decision Memory Engine",
    "Counterfactual Engine",
    "Decision Debt Engine",
    "Client Digital Twin Engine",
    "Cognitive Cortex",
    "Council of Giants",
    "Executive Accountability Engine",
    "Mission Autopsy Engine",
    "Institutional Wisdom Index",
]


CONSTITUTIONAL_SYSTEMS = [
    "Human Interface Agent System",
    "Zero Single Point of Failure Redundancy",
    "Constitutional Governance Enforcement",
    "Knowledge Synthesis Layer",
    "Adaptive Learning Loop",
    "Client Trust Index",
    "Technology Exploration Engine",
    "Repair & Recovery Automation",
    "Department Intelligence Officers",
    "Multi-Tenant Isolation & Security",
]


ADAPTIVE_LEARNING_LOOP = [
    "Self-Observe",
    "Self-Learn",
    "Self-Improve",
    "Self-Expand",
    "Self-Adapt",
]


AUTHORITY_BOUNDARIES = {
    "captain": "Final authority over irreversible actions, major contracts, go-live approval, strategic pivots, refunds, and new service launches.",
    "jarvis_tier_1": "May execute routine internal optimization, monitoring, low-risk improvements, and information synthesis autonomously.",
    "jarvis_tier_2": "May execute material but reversible actions with Captain notification and full audit logging.",
    "jarvis_tier_3": "Must request Captain approval before irreversible, financial, public, security-sensitive, or strategic actions.",
    "immutable_membrane": "JARVIS cannot modify its own safety membrane, governance tiers, kill switch, or Captain authority.",
}


INTEGRATION_SPINE = [
    "Captain Control Plane",
    "JARVIS Executive Orchestrator",
    "Emotional Core",
    "Governance Tiers",
    "AI Council",
    "Adaptive Intelligence",
    "Technology Exploration",
    "Operational Integrity Teams",
    "10 Capability Modules",
    "Client Lifecycle Divisions",
    "Preventive Monitoring",
]


def _module_to_service_division(module: dict, sort_order: int) -> dict:
    return {
        "code": module["code"],
        "name": module["name"],
        "division_group": module["division"],
        "description": module["description"],
        "deliverables": [
            f"DIO monitoring for {module['name']}",
            f"HIA client interface via {module['human_interface_executive']}",
            "AI execution team",
            "Weekly Council cycle",
            "Real-time health dashboard",
        ],
        "technologies": module["agent_layer"],
        "target_industries": ["B2B Services", "SaaS", "Operations-led SMB", "Enterprise"],
        "pricing_model": "module",
        "price_range_usd": {},
        "duration_estimate": "Scoped by mission file",
        "is_featured": True,  # all 10 are the curated flagship catalog — no B-list
        "sort_order": sort_order,
    }


CANONICAL_SERVICE_DIVISIONS = [
    _module_to_service_division(module, index)
    for index, module in enumerate(CAPABILITY_MODULES, start=1)
]

# Keep this name for older import paths, but it now points to the 25 finalized modules.
SEED_DIVISIONS = CANONICAL_SERVICE_DIVISIONS


async def seed_catalog(db: AsyncSession) -> int:
    """Seed the canonical 25-module catalog if empty. Returns inserted count."""
    result = await db.execute(select(ServiceDivision).limit(1))
    if result.scalar_one_or_none():
        return 0

    for item in SEED_DIVISIONS:
        db.add(ServiceDivision(tenant_id=SYSTEM_TENANT_ID, **item))
    await db.commit()
    return len(SEED_DIVISIONS)


async def sync_canonical_catalog(db: AsyncSession) -> dict:
    """Replace any legacy catalog rows with the finalized 25 capability modules."""
    before = await db.scalar(select(func.count()).select_from(ServiceDivision))
    await db.execute(delete(ServiceDivision))
    for item in CANONICAL_SERVICE_DIVISIONS:
        db.add(ServiceDivision(tenant_id=SYSTEM_TENANT_ID, **item))
    await db.commit()
    return {
        "status": "canonical_synced",
        "removed": int(before or 0),
        "inserted": len(CANONICAL_SERVICE_DIVISIONS),
        "canonical_total": len(CANONICAL_SERVICE_DIVISIONS),
    }


async def get_all_divisions(
    db: AsyncSession,
    group: Optional[str] = None,
    featured_only: bool = False,
    active_only: bool = True,
) -> List[ServiceDivision]:
    q = select(ServiceDivision)
    if active_only:
        q = q.where(ServiceDivision.is_active == True)
    if group:
        q = q.where(ServiceDivision.division_group == group)
    if featured_only:
        q = q.where(ServiceDivision.is_featured == True)
    q = q.order_by(ServiceDivision.sort_order).limit(200)
    result = await db.execute(q)
    return result.scalars().all()


async def get_division_by_code(db: AsyncSession, code: str) -> Optional[ServiceDivision]:
    result = await db.execute(
        select(ServiceDivision).where(ServiceDivision.code == code)
    )
    return result.scalar_one_or_none()


async def get_groups(db: AsyncSession) -> List[str]:
    result = await db.execute(
        select(ServiceDivision.division_group).distinct().order_by(ServiceDivision.division_group)
    )
    return [row[0] for row in result.fetchall()]


async def update_division(
    db: AsyncSession,
    code: str,
    **kwargs,
) -> Optional[ServiceDivision]:
    await db.execute(
        update(ServiceDivision).where(ServiceDivision.code == code).values(**kwargs)
    )
    await db.commit()
    return await get_division_by_code(db, code)


async def get_catalog_stats(db: AsyncSession) -> dict:
    divisions = await get_all_divisions(db, active_only=False)
    total = len(divisions)
    active = sum(1 for d in divisions if d.is_active)
    featured = sum(1 for d in divisions if d.is_featured)
    groups: dict = {}
    for d in divisions:
        groups[d.division_group] = groups.get(d.division_group, 0) + 1
    return {
        "total": total,
        "active": active,
        "featured": featured,
        "groups": groups,
    }
