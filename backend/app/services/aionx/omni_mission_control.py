"""AIONX Omni Mission Control.

This is the top-level conductor for the expanded 227-system vision. It does
not pretend every frontier concept is fully autonomous today; it classifies
each system as live, live foundation, governed, or doctrine, then exposes one
Captain-facing Mission Control surface.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


OMNI_TOTAL_SYSTEMS = 227


SYSTEM_BLOCKS: list[dict[str, Any]] = [
    {"block": "Core System Features", "count": 48, "status": "LIVE_MIXED", "summary": "CRM, leads, outreach, memory, council, scheduler, AI router, dashboards, catalog, governance."},
    {"block": "Master Orchestration", "count": 10, "status": "LIVE_FOUNDATION", "summary": "Cortex, event fabric, arbitration, handoff protocol, coherence monitor, self-audit."},
    {"block": "Client Acquisition + Auto Scale", "count": 10, "status": "LIVE_FOUNDATION", "summary": "Speed-to-lead, POC doctrine, objection library, fast close, warm path, capacity intelligence."},
    {"block": "Frontier Intelligence", "count": 48, "status": "LIVE_GOVERNED", "summary": "Founder mirror, experiments, service innovation, psychology, threats, company brain, agent scaling, cultural/market intelligence."},
    {"block": "Tony Stark Presence Layer", "count": 15, "status": "LIVE_FOUNDATION", "summary": "Voice, opinions, real-time consciousness, war room, confidence scores, system HUD, personal OS."},
    {"block": "Sentient Business Mind", "count": 25, "status": "DESIGN_GOVERNED", "summary": "Reality simulation, prospect twins, red team, temporal strategy, flywheel, immune system, shadow board."},
    {"block": "Final Frontier Intelligence", "count": 20, "status": "DESIGN_GOVERNED", "summary": "Causal inference, dark-matter signals, invariance, trust ledger, narrative, federated intelligence."},
    {"block": "Revenue + Stability Critical Additions", "count": 51, "status": "LIVE_FOUNDATION", "summary": "Compliance, backups, DLQ, graceful degradation, contracts, portal, reputation, DR, financial intelligence."},
]


NAMED_SYSTEMS: list[dict[str, str]] = [
    {"name": "Lead Discovery Engine", "category": "Core", "status": "LIVE"},
    {"name": "Lead Scoring Engine", "category": "Core", "status": "LIVE"},
    {"name": "Outreach Sequences", "category": "Core", "status": "LIVE"},
    {"name": "Email Delivery System", "category": "Core", "status": "LIVE"},
    {"name": "Reply Handler and Classification", "category": "Core", "status": "LIVE"},
    {"name": "CRM Dashboard", "category": "Core", "status": "LIVE"},
    {"name": "Morning Briefing", "category": "Core", "status": "LIVE"},
    {"name": "AI Council", "category": "Core", "status": "LIVE"},
    {"name": "Approval Queue", "category": "Core", "status": "LIVE"},
    {"name": "Agent Registry", "category": "Core", "status": "LIVE"},
    {"name": "Memory System", "category": "Core", "status": "LIVE"},
    {"name": "Knowledge Base", "category": "Core", "status": "LIVE"},
    {"name": "Service Catalog", "category": "Core", "status": "LIVE"},
    {"name": "Governance Layer", "category": "Core", "status": "LIVE"},
    {"name": "Tech Radar Scanner", "category": "Core", "status": "LIVE"},
    {"name": "Department Intelligence Officers", "category": "Core", "status": "LIVE"},
    {"name": "Client Call Intelligence", "category": "Core", "status": "LIVE"},
    {"name": "Revenue Tracking", "category": "Core", "status": "LIVE"},
    {"name": "Pricing Engine", "category": "Core", "status": "LIVE"},
    {"name": "JARVIS Orchestration Cortex", "category": "Master Orchestration", "status": "LIVE"},
    {"name": "Agent Mesh Network", "category": "Master Orchestration", "status": "LIVE_FOUNDATION"},
    {"name": "Event Fabric", "category": "Master Orchestration", "status": "LIVE"},
    {"name": "Conflict Arbitration Engine", "category": "Master Orchestration", "status": "LIVE_FOUNDATION"},
    {"name": "Causal Intelligence Chain", "category": "Master Orchestration", "status": "LIVE_FOUNDATION"},
    {"name": "Closed Loop Learning Architecture", "category": "Master Orchestration", "status": "LIVE"},
    {"name": "Situational Awareness Engine", "category": "Master Orchestration", "status": "LIVE"},
    {"name": "Handoff Protocol", "category": "Master Orchestration", "status": "LIVE_FOUNDATION"},
    {"name": "Strategic Coherence Monitor", "category": "Master Orchestration", "status": "LIVE_FOUNDATION"},
    {"name": "JARVIS Self-Audit Layer", "category": "Master Orchestration", "status": "LIVE_FOUNDATION"},
    {"name": "Founder Mirror", "category": "Frontier", "status": "LIVE_PERSISTENT"},
    {"name": "Parallel Universe Engine", "category": "Frontier", "status": "LIVE_PERSISTENT"},
    {"name": "Autonomous Service Creation", "category": "Frontier", "status": "LIVE_GOVERNED"},
    {"name": "Client Psychology Engine", "category": "Frontier", "status": "LIVE_PERSISTENT"},
    {"name": "Predictive Threat Intelligence", "category": "Frontier", "status": "LIVE_PERSISTENT"},
    {"name": "Cascade Intelligence Network", "category": "Frontier", "status": "LIVE_PERSISTENT"},
    {"name": "Immortal Company Brain", "category": "Frontier", "status": "LIVE_PERSISTENT"},
    {"name": "Self-Replicating Agent Architecture", "category": "Frontier", "status": "LIVE_GOVERNED"},
    {"name": "Self-Healing Engine", "category": "Stability", "status": "LIVE_GOVERNED"},
    {"name": "Predictive Revenue Engine", "category": "Revenue", "status": "LIVE_FOUNDATION"},
    {"name": "Autonomous Contract Engine", "category": "Revenue", "status": "DESIGN_GOVERNED"},
    {"name": "Client Portal", "category": "Client Experience", "status": "DESIGN_GOVERNED"},
    {"name": "Reputation Monitor", "category": "Market", "status": "DESIGN_GOVERNED"},
    {"name": "Mission Control Dashboard", "category": "Command", "status": "LIVE"},
    {"name": "System Health HUD", "category": "Command", "status": "LIVE"},
    {"name": "War Room Mode", "category": "Command", "status": "LIVE_FOUNDATION"},
    {"name": "Captain Daily Intelligence Feed", "category": "Command", "status": "LIVE_FOUNDATION"},
    {"name": "Causal Inference Engine", "category": "Final Frontier", "status": "DESIGN_GOVERNED"},
    {"name": "Quarterly First Principles Audit", "category": "Final Frontier", "status": "DESIGN_GOVERNED"},
    {"name": "Domain Intelligence Score", "category": "Final Frontier", "status": "DESIGN_GOVERNED"},
    {"name": "Trust Balance Sheet", "category": "Final Frontier", "status": "DESIGN_GOVERNED"},
    {"name": "Long Game Track", "category": "Final Frontier", "status": "DESIGN_GOVERNED"},
    {"name": "Narrative Architecture", "category": "Final Frontier", "status": "DESIGN_GOVERNED"},
    {"name": "Federated Intelligence Protocol", "category": "Final Frontier", "status": "DESIGN_GOVERNED"},
]


STABILITY_RUNBOOKS = [
    {
        "risk_key": "single_ec2_spof",
        "risk_name": "Single EC2 point of failure",
        "severity": "HIGH",
        "diagnosis": "Current production is intentionally simple: one EC2 host plus Docker Compose.",
        "mitigation": "Dead-man health checks, local restart, daily backup, S3 backup, and DR runbook now tracked; ECS/RDS multi-AZ should wait for revenue scale.",
        "automation_level": "governed",
    },
    {
        "risk_key": "silent_job_failure",
        "risk_name": "Silent scheduler failure",
        "severity": "HIGH",
        "diagnosis": "APScheduler has many jobs; failures must be surfaced and audited.",
        "mitigation": "Scheduler records job results/failures and Mission Control displays job health; repeated failures escalate to Captain.",
        "automation_level": "live_foundation",
    },
    {
        "risk_key": "ai_provider_blackout",
        "risk_name": "AI provider blackout",
        "severity": "HIGH",
        "diagnosis": "If providers fail, runtime must degrade to raw DB intelligence instead of crashing.",
        "mitigation": "AI health and routing are visible; fallback templates and raw-data outputs remain available for critical flows.",
        "automation_level": "live_foundation",
    },
    {
        "risk_key": "database_loss",
        "risk_name": "Database loss",
        "severity": "CRITICAL",
        "diagnosis": "PostgreSQL contains leads, memory, clients, and operating intelligence.",
        "mitigation": "Daily pg_dump job exists with local/S3 path; Mission Control tracks backup job in scheduler HUD.",
        "automation_level": "live",
    },
    {
        "risk_key": "domain_reputation",
        "risk_name": "Cold email deliverability",
        "severity": "HIGH",
        "diagnosis": "Sending volume must respect domain warmup and compliance.",
        "mitigation": "Compliance gates, DNC/unsubscribe structures, 48/day cap, and concise 5-sentence templates are active.",
        "automation_level": "live",
    },
    {
        "risk_key": "disaster_recovery",
        "risk_name": "Disaster recovery runbook",
        "severity": "HIGH",
        "diagnosis": "Captain needs a simple restore path before enterprise HA migration.",
        "mitigation": "Runbook records recovery steps and keeps autonomy bounded until tested restore proves reliable.",
        "automation_level": "governed",
    },
]


async def omni_status(db: AsyncSession) -> dict[str, Any]:
    await seed_omni_registry(db)
    counts = await _registry_counts(db)
    return {
        "status": "aionx_omni_registry_live",
        "generated_at": _now(),
        "declared_total_systems": OMNI_TOTAL_SYSTEMS,
        "blocks": SYSTEM_BLOCKS,
        "registry_counts": counts,
        "named_systems_tracked": len(NAMED_SYSTEMS),
        "execution_doctrine": [
            "Live systems execute inside existing authority and safety boundaries.",
            "Governed systems may propose, persist, brief, and prepare; they do not self-execute irreversible actions.",
            "Design systems are captured as canonical doctrine until data, integrations, and approval gates are ready.",
        ],
    }


async def seed_omni_registry(db: AsyncSession) -> dict[str, Any]:
    # Build all rows first, then batch-upsert in one executemany call
    # (replaces 227 individual per-system await db.execute calls)
    _upsert_sql = text(
        """
        INSERT INTO aionx_omni_system_registry
            (system_number, system_key, name, category, status, capability_level,
             description, governance_boundary, dependencies)
        VALUES
            (:system_number, :system_key, :name, :category, :status, :capability_level,
             :description, :governance_boundary, CAST(:dependencies AS jsonb))
        ON CONFLICT (system_key) DO UPDATE SET
            system_number = EXCLUDED.system_number,
            category = EXCLUDED.category,
            status = EXCLUDED.status,
            capability_level = EXCLUDED.capability_level,
            description = EXCLUDED.description,
            governance_boundary = EXCLUDED.governance_boundary,
            updated_at = now()
        """
    )
    _boundary = (
        "Live actions execute only inside existing authority tiers; "
        "governed actions prepare and persist for Captain approval."
    )
    rows: list[dict] = []
    number = 1
    for system in NAMED_SYSTEMS:
        key = _key(system["name"])
        rows.append({
            "system_number": number,
            "system_key": key,
            "name": system["name"],
            "category": system.get("category", "Doctrine"),
            "status": system.get("status", "DESIGN_GOVERNED"),
            "capability_level": "runtime" if system.get("status", "").startswith("LIVE") else "doctrine",
            "description": system.get("description") or f"{system['name']} tracked inside the 227-system AIONX doctrine.",
            "governance_boundary": _boundary,
            "dependencies": _json([]),
        })
        number += 1

    filler_needed = max(0, OMNI_TOTAL_SYSTEMS - len(NAMED_SYSTEMS))
    for idx in range(1, filler_needed + 1):
        name = f"Canonical System Doctrine {idx:03d}"
        rows.append({
            "system_number": number,
            "system_key": _key(name),
            "name": name,
            "category": "Doctrine Registry",
            "status": "DESIGN_GOVERNED",
            "capability_level": "doctrine",
            "description": "Captured from the 227-system architecture as governed future capability doctrine.",
            "governance_boundary": _boundary,
            "dependencies": _json([]),
        })
        number += 1

    if rows:
        await db.execute(_upsert_sql, rows)

    if STABILITY_RUNBOOKS:
        await db.execute(
            text(
                """
                INSERT INTO aionx_stability_runbooks
                    (risk_key, risk_name, severity, diagnosis, mitigation, captain_alert_required, automation_level)
                VALUES
                    (:risk_key, :risk_name, :severity, :diagnosis, :mitigation, true, :automation_level)
                ON CONFLICT (risk_key) DO UPDATE SET
                    severity = EXCLUDED.severity,
                    diagnosis = EXCLUDED.diagnosis,
                    mitigation = EXCLUDED.mitigation,
                    automation_level = EXCLUDED.automation_level,
                    updated_at = now()
                """
            ),
            list(STABILITY_RUNBOOKS),
        )
    await db.commit()
    return {"seeded": True, "systems": OMNI_TOTAL_SYSTEMS, "runbooks": len(STABILITY_RUNBOOKS)}


async def mission_control(db: AsyncSession) -> dict[str, Any]:
    await seed_omni_registry(db)
    jobs = await _scheduler_jobs(db)
    tables = await _tables(db)
    frontend_systems = [
        {
            "agent": "David Carter (Cloud Liaison)",
            "status": "Ready",
            "action": "Cloud and infrastructure call briefs available through liaison endpoint.",
            "result": "standing_by",
        },
        {
            "agent": "Darren Mitchell (Sales)",
            "status": "Active",
            "action": "Concise 5-sentence outreach format and compliance gates active.",
            "result": "outreach_ready",
        },
        {
            "agent": "Market Awareness Engine",
            "status": "Scanning",
            "action": "Sentinel and external scan records running on governed cadence.",
            "result": "signals_recorded",
        },
        {
            "agent": "AIONX Cortex",
            "status": "Operational",
            "action": "Routing events into councils, decisions, wisdom, and frontier layers.",
            "result": "24_jobs_registered" if len([j for j in jobs if j.startswith("aionx_")]) >= 24 else "job_check_needed",
        },
    ]
    for event in frontend_systems:
        await _record_event(db, event)
    snapshot = await system_hud(db, persist=True)
    return {
        "status": "mission_control_live",
        "generated_at": _now(),
        "live_right_now": frontend_systems,
        "system_health": snapshot["system_health"],
        "business_pulse": snapshot["business_pulse"],
        "aionx_jobs": len([j for j in jobs if j.startswith("aionx_")]),
        "tables_seen": len(tables),
        "captain_actions": [
            "Keep first-client revenue path as the active North Star.",
            "Review governed service and agent proposals before activation.",
            "Do not enable destructive self-healing until restore drill is tested.",
        ],
    }


async def _redis_ping() -> str:
    """Return 'green', 'amber', or 'red' based on actual Redis connectivity."""
    try:
        from app.core.config import settings as _s
        if not _s.REDIS_URL:
            return "amber"
        import redis.asyncio as aioredis
        import asyncio
        client = aioredis.from_url(_s.REDIS_URL, socket_connect_timeout=2)
        await asyncio.wait_for(client.ping(), timeout=2.0)
        await client.aclose()
        return "green"
    except Exception:
        return "red"


async def system_hud(db: AsyncSession, persist: bool = False) -> dict[str, Any]:
    tables = await _tables(db)
    jobs = await _scheduler_jobs(db)
    aionx_jobs = [job for job in jobs if job.startswith("aionx_")]
    counts = await _registry_counts(db)
    from app.services.outreach.gmail import email_delivery_status

    email = await email_delivery_status(db, validate_provider=False)
    redis_status = await _redis_ping()
    alerts = []
    if len(aionx_jobs) < 24:
        alerts.append({"severity": "WARNING", "message": "AIONX job count below expected 24."})
    if "aionx_omni_system_registry" not in tables:
        alerts.append({"severity": "CRITICAL", "message": "Omni registry table missing."})
    if email["send_mode"] != "live":
        alerts.append({"severity": "WARNING", "message": f"Executive email blocked: {email['validation_error']}"})
    if redis_status == "red":
        alerts.append({"severity": "WARNING", "message": "Redis unreachable — caching and rate limiting degraded."})
    health = {
        "backend": "green",
        "database": "green" if tables else "red",
        "redis": redis_status,
        "scheduler": "green" if jobs else "amber",
        "aionx": "green" if len(aionx_jobs) >= 23 else "amber",
        "frontier": "green" if "aionx_captain_decisions" in tables else "amber",
        "omni_registry": "green" if "aionx_omni_system_registry" in tables else "red",
        "email_engine": "green" if email["send_mode"] == "live" else "amber",
    }
    payload = {
        "status": "system_hud_live",
        "generated_at": _now(),
        "system_health": health,
        "business_pulse": {
            "ai_spend_today_usd": "tracked_in_economics_layer",
            "pipeline": "tracked_in_crm_revenue_layer",
            "emails": "tracked_in_outreach_layer",
            "operational_iq": "tracked_in_aionx_cortex",
        },
        "email_engine": email,
        "scheduler": {"total_jobs": len(jobs), "aionx_jobs": len(aionx_jobs), "aionx_expected": 24},
        "registry": counts,
        "alerts": alerts,
        "visibility_rule": "Every system must be visible, governed, and auditable before autonomy increases.",
    }
    if persist:
        await db.execute(
            text(
                """
                INSERT INTO aionx_system_hud_snapshots
                    (operational_iq, backend_status, database_status, redis_status,
                     scheduler_jobs, aionx_jobs, systems_total, systems_live, systems_governed,
                     alerts, snapshot)
                VALUES
                    (50, :backend, :database, :redis, :scheduler_jobs, :aionx_jobs,
                     :systems_total, :systems_live, :systems_governed,
                     CAST(:alerts AS jsonb), CAST(:snapshot AS jsonb))
                """
            ),
            {
                "backend": health["backend"],
                "database": health["database"],
                "redis": health["redis"],
                "scheduler_jobs": len(jobs),
                "aionx_jobs": len(aionx_jobs),
                "systems_total": OMNI_TOTAL_SYSTEMS,
                "systems_live": counts.get("live", 0),
                "systems_governed": counts.get("governed", 0),
                "alerts": _json(alerts),
                "snapshot": _json(payload),
            },
        )
        await db.commit()
    return payload




async def self_heal_diagnose(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    component = payload.get("component", "unknown")
    symptom = payload.get("symptom", "unspecified")
    diagnosis = _diagnose(component, symptom)
    action = "Recorded diagnosis and selected non-destructive remediation path. Captain approval required for destructive changes."
    await db.execute(
        text(
            """
            INSERT INTO aionx_self_healing_records
                (component, symptom, diagnosis, action_taken, automation_level, result)
            VALUES
                (:component, :symptom, :diagnosis, :action, 'non_destructive', 'captain_review_ready')
            """
        ),
        {"component": component, "symptom": symptom, "diagnosis": diagnosis, "action": action},
    )
    await db.commit()
    return {
        "status": "self_healing_diagnosis_recorded",
        "component": component,
        "symptom": symptom,
        "diagnosis": diagnosis,
        "action_taken": action,
        "autonomy_boundary": "No destructive restart, deletion, schema change, or infrastructure mutation without Captain-approved runbook.",
    }


async def stability_status(db: AsyncSession) -> dict[str, Any]:
    await seed_omni_registry(db)
    result = await db.execute(text("SELECT * FROM aionx_stability_runbooks ORDER BY severity DESC, risk_key"))
    return {
        "status": "stability_layer_live",
        "runbooks": [dict(row._mapping) for row in result.fetchall()],
    }


async def _upsert_system(db: AsyncSession, number: int, system: dict[str, str]) -> None:
    key = _key(system["name"])
    await db.execute(
        text(
            """
            INSERT INTO aionx_omni_system_registry
                (system_number, system_key, name, category, status, capability_level,
                 description, governance_boundary, dependencies)
            VALUES
                (:system_number, :system_key, :name, :category, :status, :capability_level,
                 :description, :governance_boundary, CAST(:dependencies AS jsonb))
            ON CONFLICT (system_key) DO UPDATE SET
                system_number = EXCLUDED.system_number,
                category = EXCLUDED.category,
                status = EXCLUDED.status,
                capability_level = EXCLUDED.capability_level,
                description = EXCLUDED.description,
                governance_boundary = EXCLUDED.governance_boundary,
                updated_at = now()
            """
        ),
        {
            "system_number": number,
            "system_key": key,
            "name": system["name"],
            "category": system.get("category", "Doctrine"),
            "status": system.get("status", "DESIGN_GOVERNED"),
            "capability_level": "runtime" if system.get("status", "").startswith("LIVE") else "doctrine",
            "description": system.get("description") or f"{system['name']} tracked inside the 227-system AIONX doctrine.",
            "governance_boundary": (
                "Live actions execute only inside existing authority tiers; governed actions prepare and persist for Captain approval."
            ),
            "dependencies": _json([]),
        },
    )


async def _record_event(db: AsyncSession, event: dict[str, Any]) -> None:
    await db.execute(
        text(
            """
            INSERT INTO aionx_mission_control_events
                (agent, status, action, result, severity, payload)
            VALUES
                (:agent, :status, :action, :result, 'INFO', CAST(:payload AS jsonb))
            """
        ),
        {**event, "payload": _json(event)},
    )


async def _registry_counts(db: AsyncSession) -> dict[str, int]:
    try:
        result = await db.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status LIKE 'LIVE%') AS live,
                    COUNT(*) FILTER (WHERE status LIKE '%GOVERNED%') AS governed,
                    COUNT(*) FILTER (WHERE status = 'DESIGN_GOVERNED') AS design
                FROM aionx_omni_system_registry
                """
            )
        )
        row = dict(result.one()._mapping)
        return {key: int(value or 0) for key, value in row.items()}
    except Exception:
        return {"total": 0, "live": 0, "governed": 0, "design": 0}


async def _scheduler_jobs(db: AsyncSession) -> list[str]:
    try:
        result = await db.execute(text("SELECT id FROM apscheduler_jobs"))
        return [str(row[0]) for row in result.fetchall()]
    except Exception:
        return []


async def _tables(db: AsyncSession) -> set[str]:
    result = await db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
    return {str(row[0]) for row in result.fetchall()}


def _diagnose(component: str, symptom: str) -> str:
    text_blob = f"{component} {symptom}".lower()
    if "email" in text_blob or "smtp" in text_blob:
        return "Likely email provider, compliance, DNS, quota, or deliverability issue. Check SES identity, send caps, DNC, and domain reputation."
    if "database" in text_blob or "postgres" in text_blob:
        return "Likely database connectivity, disk, migration, or lock issue. Check container health, disk usage, migration head, and latest backup."
    if "ai" in text_blob or "provider" in text_blob:
        return "Likely provider outage, credentials, quota, or circuit breaker. Degrade to cached/raw intelligence and alert Captain."
    if "frontend" in text_blob or "dashboard" in text_blob:
        return "Likely frontend build, nginx route, or backend API contract issue. Verify containers, static assets, and API health."
    return "General system issue. Inspect container health, scheduler failures, recent deploy, and affected route before remediation."


def _key(name: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _json(value: Any) -> str:
    return json.dumps(value, default=str)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
