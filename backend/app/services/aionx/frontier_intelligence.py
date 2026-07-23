"""AIONX frontier intelligence systems.

This module implements the advanced architecture from the recovered design:
Founder Mirror, Parallel Universe experiments, autonomous service concepts,
client psychology, early warning, cascade intelligence, immortal company
brain, and governed agent scaling.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


FRONTIER_SYSTEMS: list[dict[str, Any]] = [
    {
        "id": "founder_mirror",
        "name": "Founder Mirror",
        "status": "LIVE_PERSISTENT",
        "purpose": "Predict Captain approval patterns and pause low-confidence actions.",
        "boundary": "Prediction assists governance; Captain remains final authority.",
    },
    {
        "id": "parallel_universe",
        "name": "Parallel Universe Engine",
        "status": "LIVE_PERSISTENT",
        "purpose": "Run controlled variants for outreach, proposals, pricing, and positioning.",
        "boundary": "Winners are recommended or promoted inside approved non-risk workflows only.",
    },
    {
        "id": "service_innovation",
        "name": "Autonomous Service Creation",
        "status": "LIVE_GOVERNED",
        "purpose": "Generate new service concepts from market/client signals.",
        "boundary": "New services stay in Captain review until explicitly approved.",
    },
    {
        "id": "client_psychology",
        "name": "Client Psychology Engine",
        "status": "LIVE_PERSISTENT",
        "purpose": "Profile decision style and rewrite messages around buyer psychology.",
        "boundary": "Personalization cannot manipulate, misrepresent, or pressure clients.",
    },
    {
        "id": "early_warning",
        "name": "Predictive Threat Intelligence",
        "status": "LIVE_PERSISTENT",
        "purpose": "Detect lead, client, provider, revenue, and council risks before crisis.",
        "boundary": "Critical alerts notify and propose action; destructive action is blocked.",
    },
    {
        "id": "cascade_network",
        "name": "Cascade Intelligence Network",
        "status": "LIVE_PERSISTENT",
        "purpose": "Propagate intelligence across relevant departments with audit trail.",
        "boundary": "Cascades update briefs and recommendations, not irreversible production state.",
    },
    {
        "id": "immortal_brain",
        "name": "Immortal Company Brain",
        "status": "LIVE_PERSISTENT",
        "purpose": "Store permanent company knowledge artifacts and recall what worked.",
        "boundary": "Artifacts are immutable by default; corrections create new records.",
    },
    {
        "id": "agent_scaling",
        "name": "Self-Replicating Agent Architecture",
        "status": "LIVE_GOVERNED",
        "purpose": "Detect capacity pressure and propose new agents for Captain approval.",
        "boundary": "Agents are proposed, not autonomously deployed.",
    },
]


async def frontier_status(db: AsyncSession) -> dict[str, Any]:
    counts = {}
    for table in FRONTIER_TABLES:
        try:
            result = await db.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
            counts[table] = int(result.scalar_one())
        except Exception:
            counts[table] = -1
    return {
        "status": "aionx_frontier_intelligence_live",
        "generated_at": _now(),
        "systems_total": len(FRONTIER_SYSTEMS),
        "systems": FRONTIER_SYSTEMS,
        "table_count": len(FRONTIER_TABLES),
        "counts": counts,
        "governance": [
            "Captain-first loyalty check runs before significant autonomous action.",
            "Low-confidence Founder Mirror predictions pause for Captain review.",
            "New services and new agents require Captain approval before activation.",
            "Threat intelligence may alert immediately but cannot self-mutate production.",
        ],
    }


async def record_captain_decision(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    decision = str(payload.get("decision") or "unknown").lower()
    action = str(payload.get("action") or "unspecified_action")
    context = payload.get("context") or {}
    reasoning = payload.get("reasoning") or "Recorded for Founder Mirror learning."
    outcome = payload.get("outcome")
    confidence = float(payload.get("confidence", 0.75))
    row = await db.execute(
        text(
            """
            INSERT INTO aionx_captain_decisions
                (tenant_id, action, context, reasoning, outcome, decision, confidence)
            VALUES
                (:tenant_id, :action, CAST(:context AS jsonb), :reasoning, :outcome, :decision, :confidence)
            RETURNING id
            """
        ),
        {
            "tenant_id": payload.get("tenant_id"),
            "action": action,
            "context": _json(context),
            "reasoning": reasoning,
            "outcome": outcome,
            "decision": decision,
            "confidence": confidence,
        },
    )
    await db.commit()
    return {"id": str(row.scalar_one()), "recorded": True, "decision": decision, "confidence": confidence}


async def captain_mirror_profile(db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(
        text(
            """
            SELECT decision, COUNT(*) AS count, AVG(confidence) AS confidence
            FROM aionx_captain_decisions
            GROUP BY decision
            ORDER BY count DESC
            """
        )
    )
    rows = [dict(row._mapping) for row in result.fetchall()]
    total = sum(int(row["count"]) for row in rows)
    return {
        "status": "founder_mirror_live",
        "captain_model": "pattern_based_v1",
        "decisions_recorded": total,
        "decision_distribution": rows,
        "approval_threshold": 0.7,
        "default_boundary": "If confidence < 0.70, pause and ask Captain.",
    }


async def predict_captain_decision(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    action = str(payload.get("action_description") or payload.get("context") or "")
    options = payload.get("options") or ["approve", "reject"]
    lowered = action.lower()
    risk_terms = ["delete", "force push", "pricing", "client", "send", "deploy", "secret", "cost", "contract"]
    protection_terms = ["backup", "audit", "verify", "read only", "approval", "rollback", "safety"]
    risk_hits = sum(1 for term in risk_terms if term in lowered)
    protection_hits = sum(1 for term in protection_terms if term in lowered)
    predicted = "approve" if protection_hits >= risk_hits else "captain_review"
    confidence = min(0.92, max(0.55, 0.68 + (protection_hits * 0.06) - (risk_hits * 0.04)))
    if confidence < 0.7:
        predicted = "captain_review"
    return {
        "predicted_decision": predicted,
        "confidence": round(confidence, 2),
        "options": options,
        "reasoning": (
            "Prediction is based on Captain-first safety, operational reversibility, "
            "client exposure, and approval boundaries."
        ),
        "captain_would_approve": predicted == "approve" and confidence >= 0.7,
        "requires_captain_review": confidence < 0.7 or predicted != "approve",
    }


async def create_experiment(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    variants = payload.get("variants") or ["A", "B", "C"]
    row = await db.execute(
        text(
            """
            INSERT INTO aionx_experiments
                (tenant_id, name, target_metric, variants, default_variant)
            VALUES
                (:tenant_id, :name, :target_metric, CAST(:variants AS jsonb), :default_variant)
            RETURNING id
            """
        ),
        {
            "tenant_id": payload.get("tenant_id"),
            "name": payload.get("name", "Untitled experiment"),
            "target_metric": payload.get("target_metric", "conversion_rate"),
            "variants": _json(variants),
            "default_variant": str(variants[0]) if variants else "A",
        },
    )
    await db.commit()
    return {"experiment_id": str(row.scalar_one()), "created": True, "variants": variants}


async def list_experiments(db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(
        text(
            """
            SELECT e.id, e.name, e.target_metric, e.variants, e.status, e.winner,
                   COUNT(o.id) AS outcomes,
                   COALESCE(AVG(o.metric_value), 0) AS avg_metric
            FROM aionx_experiments e
            LEFT JOIN aionx_experiment_outcomes o ON o.experiment_id = e.id
            GROUP BY e.id
            ORDER BY e.created_at DESC
            LIMIT 100
            """
        )
    )
    return {"experiments": [dict(row._mapping) for row in result.fetchall()]}


async def assign_variant(db: AsyncSession, experiment_id: str, prospect_id: str) -> dict[str, Any]:
    result = await db.execute(text("SELECT variants FROM aionx_experiments WHERE id = CAST(:id AS uuid)"), {"id": experiment_id})
    variants = result.scalar_one_or_none() or ["A"]
    if isinstance(variants, str):
        variants = json.loads(variants)
    digest = hashlib.sha256(f"{experiment_id}:{prospect_id}".encode()).hexdigest()
    variant = variants[int(digest[:8], 16) % len(variants)]
    return {"experiment_id": experiment_id, "prospect_id": prospect_id, "variant": variant}


async def record_experiment_outcome(db: AsyncSession, experiment_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    await db.execute(
        text(
            """
            INSERT INTO aionx_experiment_outcomes
                (tenant_id, experiment_id, prospect_id, variant, outcome, metric_value, metadata_json)
            VALUES
                (:tenant_id, CAST(:experiment_id AS uuid), :prospect_id, :variant, :outcome, :metric_value, CAST(:metadata AS jsonb))
            """
        ),
        {
            "tenant_id": payload.get("tenant_id"),
            "experiment_id": experiment_id,
            "prospect_id": payload.get("prospect_id"),
            "variant": payload.get("variant", "A"),
            "outcome": payload.get("outcome", "unknown"),
            "metric_value": float(payload.get("metric_value", 0)),
            "metadata": _json(payload.get("metadata") or {}),
        },
    )
    await db.commit()
    return {"recorded": True, "experiment_id": experiment_id}


async def get_experiment_winner(db: AsyncSession, experiment_id: str, promote: bool = False) -> dict[str, Any]:
    result = await db.execute(
        text(
            """
            SELECT variant, COUNT(*) AS samples, COALESCE(AVG(metric_value), 0) AS score
            FROM aionx_experiment_outcomes
            WHERE experiment_id = CAST(:experiment_id AS uuid)
            GROUP BY variant
            ORDER BY score DESC, samples DESC
            """
        ),
        {"experiment_id": experiment_id},
    )
    rows = [dict(row._mapping) for row in result.fetchall()]
    winner = rows[0]["variant"] if rows else None
    if promote and winner:
        await db.execute(
            text("UPDATE aionx_experiments SET winner=:winner, status='winner_promoted', updated_at=now() WHERE id=CAST(:id AS uuid)"),
            {"winner": winner, "id": experiment_id},
        )
        await db.commit()
    return {"experiment_id": experiment_id, "winner": winner, "results": rows, "promoted": bool(promote and winner)}


async def generate_service_concept(db: AsyncSession, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    signals = payload.get("signals") or ["buyers need trusted AI operations without hiring internal teams"]
    industry = payload.get("industry") or "SMB operations"
    name = payload.get("name") or f"{industry.title()} Operating Intelligence Pilot"
    concept = {
        "name": name,
        "description": f"A 90-day pilot that maps, fixes, and measures one high-friction {industry} operating workflow.",
        "target_client": payload.get("target_client") or f"Founder-led {industry} teams with visible follow-up or reporting gaps.",
        "pricing": payload.get("pricing") or "Captain review required; propose pilot-first pricing after discovery.",
        "delivery_method": "Discovery brief, workflow map, implementation sprint, QA gate, monthly outcome review.",
        "sales_script": "Lead with the pain, show one quantified result, ask one relevance question, then offer a demo path.",
        "proposal_template": "Problem -> measurable target -> 90-day pilot -> risk reversal -> next step.",
        "source_signals": signals,
    }
    row = await db.execute(
        text(
            """
            INSERT INTO aionx_service_concepts
                (tenant_id, name, description, target_client, pricing, delivery_method, sales_script, proposal_template, source_signals)
            VALUES
                (:tenant_id, :name, :description, :target_client, :pricing, :delivery_method, :sales_script, :proposal_template, CAST(:signals AS jsonb))
            RETURNING id
            """
        ),
        {**concept, "tenant_id": payload.get("tenant_id"), "signals": _json(signals)},
    )
    await db.commit()
    return {"concept_id": str(row.scalar_one()), "status": "captain_review", **concept}


async def list_service_concepts(db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(text("SELECT * FROM aionx_service_concepts ORDER BY created_at DESC LIMIT 100"))
    return {"concepts": [dict(row._mapping) for row in result.fetchall()]}


async def approve_service_concept(db: AsyncSession, concept_id: str) -> dict[str, Any]:
    await db.execute(
        text("UPDATE aionx_service_concepts SET status='active', updated_at=now() WHERE id=CAST(:id AS uuid)"),
        {"id": concept_id},
    )
    await db.commit()
    return {"concept_id": concept_id, "status": "active", "approved": True}


async def build_psychology_profile(db: AsyncSession, lead_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    text_blob = " ".join(str(v) for v in payload.values()).lower()
    profile = {
        "communication_style": "technical" if any(w in text_blob for w in ["api", "stack", "integration"]) else "executive",
        "decision_pattern": "data_driven" if any(w in text_blob for w in ["roi", "metric", "report"]) else "committee",
        "price_sensitivity": "high" if any(w in text_blob for w in ["budget", "cost", "cheap"]) else "medium",
        "risk_tolerance": "conservative" if any(w in text_blob for w in ["compliance", "risk", "security"]) else "moderate",
        "motivator": "cost_reduction" if "cost" in text_blob else "revenue_growth",
        "response_pattern": "slow_deliberate" if len(text_blob) > 900 else "quick_responder",
    }
    await db.execute(
        text(
            """
            INSERT INTO aionx_psychology_profiles
                (tenant_id, lead_id, communication_style, decision_pattern, price_sensitivity, risk_tolerance, motivator, response_pattern, profile)
            VALUES
                (:tenant_id, :lead_id, :communication_style, :decision_pattern, :price_sensitivity, :risk_tolerance, :motivator, :response_pattern, CAST(:profile AS jsonb))
            """
        ),
        {**profile, "tenant_id": payload.get("tenant_id"), "lead_id": lead_id, "profile": _json({**profile, "evidence": payload})},
    )
    await db.commit()
    return {"lead_id": lead_id, "profile": profile, "persisted": True}


async def personalize_message(db: AsyncSession, lead_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    result = await db.execute(
        text("SELECT profile FROM aionx_psychology_profiles WHERE lead_id=:lead_id ORDER BY created_at DESC LIMIT 1"),
        {"lead_id": lead_id},
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = (await build_psychology_profile(db, lead_id, payload)).get("profile")
    template = payload.get("template") or "Your team may be losing time in manual handoffs. Would this be relevant?"
    motivator = profile.get("motivator", "revenue_growth") if isinstance(profile, dict) else "revenue_growth"
    suffix = "with a clear revenue outcome" if motivator == "revenue_growth" else "with less operational waste"
    return {"lead_id": lead_id, "profile": profile, "personalized_message": f"{template} Framed {suffix}."}


async def real_threat_signals(db: AsyncSession) -> dict[str, Any]:
    """Pull live signals for scan_threats instead of the empty-dict default that made every threshold unreachable."""
    reply_rates = (await db.execute(
        text(
            "SELECT "
            "(SELECT COUNT(*) FROM outreach_log WHERE created_at >= now() - interval '1 day') AS sent_today, "
            "(SELECT COUNT(*) FROM reply_log WHERE created_at >= now() - interval '1 day') AS replies_today, "
            "(SELECT COUNT(*) FROM outreach_log WHERE created_at >= now() - interval '7 days') AS sent_week, "
            "(SELECT COUNT(*) FROM reply_log WHERE created_at >= now() - interval '7 days') AS replies_week"
        )
    )).mappings().one()

    today_rate = (reply_rates["replies_today"] / reply_rates["sent_today"] * 100) if reply_rates["sent_today"] else 0.0
    week_rate = (reply_rates["replies_week"] / reply_rates["sent_week"] * 100) if reply_rates["sent_week"] else 0.0
    reply_rate_drop_pct = max(0.0, week_rate - today_rate)

    silence_row = (await db.execute(
        text("SELECT EXTRACT(day FROM now() - MAX(created_at)) AS days FROM reply_log")
    )).mappings().one()
    client_silence_days = float(silence_row["days"]) if silence_row["days"] is not None else 0.0

    pipeline_leads = (await db.execute(text("SELECT COUNT(*) FROM leads"))).scalar_one()

    from app.services.ai.router import ai_router as jarvis_router
    configured = len(jarvis_router.available_providers())
    operational = len(jarvis_router.operational_providers())
    provider_error_rate_pct = (100.0 * (1 - operational / configured)) if configured else 0.0

    return {
        "reply_rate_drop_pct": round(reply_rate_drop_pct, 1),
        "client_silence_days": client_silence_days,
        "provider_error_rate_pct": round(provider_error_rate_pct, 1),
        "pipeline_leads": pipeline_leads,
    }


async def scan_threats(db: AsyncSession, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    signals = payload.get("signals") or {}
    generated = []
    checks = [
        ("reply_rate_drop", signals.get("reply_rate_drop_pct", 0), 20, "HIGH", "Reply rate dropped more than 20%. Refresh offer angle and subject line."),
        ("client_silence", signals.get("client_silence_days", 0), 5, "HIGH", "Client silence exceeds five days. Prepare retention touchpoint."),
        ("provider_degradation", signals.get("provider_error_rate_pct", 0), 10, "CRITICAL", "Provider errors rising. Prepare failover path."),
        ("pipeline_dryness", signals.get("pipeline_leads", 99), 10, "MEDIUM", "Pipeline has fewer than 10 leads. Trigger discovery sprint."),
    ]
    for threat_type, value, threshold, severity, action in checks:
        active = value > threshold if threat_type != "pipeline_dryness" else value < threshold
        if not active:
            continue
        row = await db.execute(
            text(
                """
                INSERT INTO aionx_threat_alerts
                    (tenant_id, threat_type, severity, confidence, summary, recommended_action)
                VALUES
                    (:tenant_id, :threat_type, :severity, :confidence, :summary, :recommended_action)
                RETURNING id
                """
            ),
            {
                "tenant_id": payload.get("tenant_id"),
                "threat_type": threat_type,
                "severity": severity,
                "confidence": 0.82,
                "summary": f"{threat_type} threshold crossed: {value}",
                "recommended_action": action,
            },
        )
        generated.append({"id": str(row.scalar_one()), "threat_type": threat_type, "severity": severity})
    await db.commit()
    return {"scan_complete": True, "alerts_created": len(generated), "alerts": generated}


async def list_threats(db: AsyncSession, active_only: bool = True) -> dict[str, Any]:
    if active_only:
        result = await db.execute(
            text("SELECT * FROM aionx_threat_alerts WHERE status='active' ORDER BY created_at DESC LIMIT 100")
        )
    else:
        result = await db.execute(
            text("SELECT * FROM aionx_threat_alerts ORDER BY created_at DESC LIMIT 100")
        )
    return {"threats": [dict(row._mapping) for row in result.fetchall()]}


async def resolve_threat(db: AsyncSession, threat_id: str) -> dict[str, Any]:
    await db.execute(
        text("UPDATE aionx_threat_alerts SET status='resolved', resolved_at=now(), updated_at=now() WHERE id=CAST(:id AS uuid)"),
        {"id": threat_id},
    )
    await db.commit()
    return {"threat_id": threat_id, "resolved": True}


async def cascade_intelligence(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    event_type = payload.get("event_type", "GENERAL_SIGNAL")
    source = payload.get("source_department", "JARVIS")
    targets = _cascade_targets(event_type)
    audit = [{"department": dept, "action": _cascade_action(event_type, dept), "status": "brief_updated"} for dept in targets]
    row = await db.execute(
        text(
            """
            INSERT INTO aionx_intelligence_events
                (tenant_id, source_department, event_type, payload, propagated_to, audit_trail)
            VALUES
                (:tenant_id, :source, :event_type, CAST(:payload AS jsonb), CAST(:targets AS jsonb), CAST(:audit AS jsonb))
            RETURNING id
            """
        ),
        {
            "tenant_id": payload.get("tenant_id"),
            "source": source,
            "event_type": event_type,
            "payload": _json(payload.get("payload") or {}),
            "targets": _json(targets),
            "audit": _json(audit),
        },
    )
    await db.commit()
    return {"event_id": str(row.scalar_one()), "source_department": source, "propagated_to": targets, "audit_trail": audit}


async def list_cascade_events(db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(text("SELECT * FROM aionx_intelligence_events ORDER BY created_at DESC LIMIT 100"))
    return {"events": [dict(row._mapping) for row in result.fetchall()]}


async def create_knowledge_artifact(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    row = await db.execute(
        text(
            """
            INSERT INTO aionx_knowledge_artifacts
                (tenant_id, artifact_type, content, tags, importance_score, metadata_json)
            VALUES
                (:tenant_id, :artifact_type, :content, CAST(:tags AS jsonb), :importance_score, CAST(:metadata AS jsonb))
            RETURNING id
            """
        ),
        {
            "tenant_id": payload.get("tenant_id"),
            "artifact_type": payload.get("artifact_type", "lesson"),
            "content": payload.get("content", ""),
            "tags": _json(payload.get("tags") or []),
            "importance_score": float(payload.get("importance_score", 0.7)),
            "metadata": _json(payload.get("metadata") or {}),
        },
    )
    await db.commit()
    return {"artifact_id": str(row.scalar_one()), "created": True}


async def recall_knowledge(db: AsyncSession, query: str, limit: int = 10) -> dict[str, Any]:
    terms = [term for term in query.lower().split() if len(term) > 2]
    pattern = "%" + "%".join(terms[:4] or [query.lower()]) + "%"
    result = await db.execute(
        text(
            """
            SELECT id, artifact_type, content, tags, importance_score, created_at
            FROM aionx_knowledge_artifacts
            WHERE LOWER(content) LIKE :pattern OR CAST(tags AS text) ILIKE :pattern
            ORDER BY importance_score DESC, created_at DESC
            LIMIT :limit
            """
        ),
        {"pattern": pattern, "limit": limit},
    )
    return {"query": query, "results": [dict(row._mapping) for row in result.fetchall()]}


async def what_worked(db: AsyncSession, industry: str | None = None, service_type: str | None = None) -> dict[str, Any]:
    query = " ".join(filter(None, [industry, service_type, "worked success conversion"])).strip() or "worked"
    return await recall_knowledge(db, query, limit=20)


async def _real_department_capacity(db: AsyncSession) -> list[dict[str, Any]]:
    """Pull live queue/backlog counts per department instead of hardcoded sample numbers."""
    outreach = (await db.execute(
        text(
            "SELECT "
            "(SELECT COUNT(*) FROM follow_up_queue WHERE status = 'PENDING' AND scheduled_at <= now()) AS queued, "
            "(SELECT COUNT(*) FROM reply_log WHERE classification IN ('INTERESTED', 'QUESTION') "
            "AND created_at <= now() - interval '3 days') AS backlog"
        )
    )).mappings().one()

    client_success = (await db.execute(
        text(
            "SELECT "
            "(SELECT COUNT(*) FROM invoices WHERE status = 'SENT') AS queued, "
            "(SELECT COUNT(*) FROM invoices WHERE status = 'OVERDUE') AS backlog"
        )
    )).mappings().one()

    cloud = (await db.execute(
        text(
            "SELECT "
            "(SELECT COUNT(*) FROM incident_reports WHERE status IN ('open', 'investigating')) AS queued, "
            "(SELECT COUNT(*) FROM incident_reports WHERE category = 'infrastructure' AND status = 'open') AS backlog"
        )
    )).mappings().one()

    return [
        {"department": "Outreach", "tasks_queued": outreach["queued"], "response_time_minutes": 0, "backlog_size": outreach["backlog"]},
        {"department": "Client Success", "tasks_queued": client_success["queued"], "response_time_minutes": 0, "backlog_size": client_success["backlog"]},
        {"department": "Cloud", "tasks_queued": cloud["queued"], "response_time_minutes": 0, "backlog_size": cloud["backlog"]},
    ]


async def agent_capacity(db: AsyncSession, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    departments = payload.get("departments") or await _real_department_capacity(db)
    snapshots = []
    insert_params = []
    over_capacity_depts: list[str] = []
    for dept in departments:
        capacity = min(100, int(dept.get("tasks_queued", 0)) * 4 + int(dept.get("backlog_size", 0)) * 6)
        status = "over_capacity" if capacity >= 80 else "normal"
        row_params = {**dept, "tenant_id": payload.get("tenant_id"), "capacity_percent": capacity, "status": status}
        insert_params.append(row_params)
        snapshots.append({**dept, "capacity_percent": capacity, "status": status})
        if status == "over_capacity":
            over_capacity_depts.append(dept["department"])

    if insert_params:
        await db.execute(
            text(
                """
                INSERT INTO aionx_agent_capacity
                    (tenant_id, department, tasks_queued, response_time_minutes, backlog_size, capacity_percent, status)
                VALUES
                    (:tenant_id, :department, :tasks_queued, :response_time_minutes, :backlog_size, :capacity_percent, :status)
                """
            ),
            insert_params,
        )

    proposals = []
    for dept_name in over_capacity_depts:
        existing = await db.execute(
            text("SELECT id FROM aionx_agent_proposals WHERE department = :department AND status = 'captain_review' LIMIT 1"),
            {"department": dept_name},
        )
        if existing.first() is not None:
            continue
        proposals.append(await propose_agent(db, dept_name, payload.get("tenant_id")))
    await db.commit()
    return {"capacity_checked": True, "departments": snapshots, "agent_proposals": proposals}


async def propose_agent(db: AsyncSession, department: str, tenant_id=None) -> dict[str, Any]:
    agent_name = f"{department.upper().replace(' ', '_')}-2"
    proposal = {
        "department": department,
        "agent_name": agent_name,
        "role": f"{department} Specialist",
        "responsibilities": ["reduce backlog", "maintain quality", "report milestones to Council"],
        "kpis": ["task_completion_rate", "quality_score", "response_time"],
        "captain_message": f"{department} capacity is high. JARVIS designed {agent_name} for Captain approval.",
    }
    row = await db.execute(
        text(
            """
            INSERT INTO aionx_agent_proposals
                (tenant_id, department, agent_name, role, responsibilities, kpis, proposal)
            VALUES
                (:tenant_id, :department, :agent_name, :role, CAST(:responsibilities AS jsonb), CAST(:kpis AS jsonb), CAST(:proposal AS jsonb))
            RETURNING id
            """
        ),
        {
            "tenant_id": tenant_id,
            "department": department,
            "agent_name": agent_name,
            "role": proposal["role"],
            "responsibilities": _json(proposal["responsibilities"]),
            "kpis": _json(proposal["kpis"]),
            "proposal": _json(proposal),
        },
    )
    return {"proposal_id": str(row.scalar_one()), **proposal, "status": "captain_review"}


async def list_agent_proposals(db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(text("SELECT * FROM aionx_agent_proposals ORDER BY created_at DESC LIMIT 100"))
    return {"proposals": [dict(row._mapping) for row in result.fetchall()]}


async def approve_agent_proposal(db: AsyncSession, proposal_id: str) -> dict[str, Any]:
    await db.execute(
        text("UPDATE aionx_agent_proposals SET status='approved', updated_at=now() WHERE id=CAST(:id AS uuid)"),
        {"id": proposal_id},
    )
    await db.commit()
    return {"proposal_id": proposal_id, "status": "approved", "note": "Approved for activation by Captain authority."}


def _cascade_targets(event_type: str) -> list[str]:
    event = event_type.upper()
    if "COMPETITOR" in event:
        return ["Sales", "Marketing", "Strategy", "Council"]
    if "TECH" in event:
        return ["Engineering", "DevOps", "AI Runtime", "Council"]
    if "CLIENT" in event:
        return ["Delivery", "Client Success", "Support", "Council"]
    if "MARKET" in event:
        return ["Sales", "Pricing", "Outreach", "Strategy"]
    return ["Council", "Operations", "Captain Bridge"]


def _cascade_action(event_type: str, department: str) -> str:
    return f"{department} brief updated from {event_type}; next action stays governance-gated."


def _json(value: Any) -> str:
    return json.dumps(value, default=str)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


FRONTIER_TABLES = [
    "aionx_captain_decisions",
    "aionx_experiments",
    "aionx_experiment_outcomes",
    "aionx_service_concepts",
    "aionx_psychology_profiles",
    "aionx_threat_alerts",
    "aionx_intelligence_events",
    "aionx_knowledge_artifacts",
    "aionx_agent_capacity",
    "aionx_agent_proposals",
]
