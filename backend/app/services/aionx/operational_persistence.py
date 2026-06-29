"""AIONX persisted operations and governed autonomy.

These helpers turn the architecture surface into durable production memory.
They deliberately record, propose, and audit; they do not execute destructive
or self-modifying actions without Captain approval.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.aionx.operational_integrity import (
    create_mission_plan,
    create_repair_instruction,
    issue_qa_certificate,
    run_fallback_drill,
    synthesize_milestone_learning,
)
from app.services.aionx.sovereign_organs import genesis_proposal, immune_scan, system_state_snapshot
from app.services.aionx.ultimate_client_journey import preventive_monitoring_status


async def persist_mission_plan(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    plan = create_mission_plan(payload)
    mission_row = await db.execute(
        text(
            """
            INSERT INTO aionx_mission_files (
                mission_id, client_name, objective, gateway, mission_status,
                captain_required, mission_payload, milestones, governance_workflow, created_by
            )
            VALUES (
                :mission_id, :client_name, :objective, :gateway, :mission_status,
                :captain_required, CAST(:mission_payload AS jsonb), CAST(:milestones AS jsonb),
                CAST(:governance_workflow AS jsonb), :created_by
            )
            ON CONFLICT (mission_id) DO UPDATE SET
                client_name = EXCLUDED.client_name,
                objective = EXCLUDED.objective,
                gateway = EXCLUDED.gateway,
                mission_status = EXCLUDED.mission_status,
                captain_required = EXCLUDED.captain_required,
                mission_payload = EXCLUDED.mission_payload,
                milestones = EXCLUDED.milestones,
                governance_workflow = EXCLUDED.governance_workflow,
                updated_at = now()
            RETURNING id
            """
        ),
        {
            "mission_id": plan["mission_id"],
            "client_name": plan["client"],
            "objective": plan["objective"],
            "gateway": plan["gateway"],
            "mission_status": "PLANNED",
            "captain_required": plan["captain_required"],
            "mission_payload": _json(plan),
            "milestones": _json(plan["milestones"]),
            "governance_workflow": _json(plan["workflow"]),
            "created_by": payload.get("created_by", "JARVIS"),
        },
    )
    mission_file_id = str(mission_row.scalar_one())

    if plan["milestones"]:
        await db.execute(
            text(
                """
                INSERT INTO aionx_milestone_plans (
                    mission_file_id, mission_id, milestone_number, title, owner,
                    status, success_criteria, evidence
                )
                VALUES (
                    CAST(:mission_file_id AS uuid), :mission_id, :milestone_number, :title, :owner,
                    'PENDING', CAST(:success_criteria AS jsonb), CAST(:evidence AS jsonb)
                )
                """
            ),
            [
                {
                    "mission_file_id": mission_file_id,
                    "mission_id": plan["mission_id"],
                    "milestone_number": milestone["number"],
                    "title": milestone["title"],
                    "owner": milestone["owner"],
                    "success_criteria": _json(milestone["success_criteria"]),
                    "evidence": _json({}),
                }
                for milestone in plan["milestones"]
            ],
        )

    await record_event(
        db,
        event_type="MISSION_FILE_CREATED",
        source="MISSION_CONTROL",
        payload=plan,
        severity="INFO",
        captain_approval_required=plan["captain_required"],
    )
    await db.commit()
    return {**plan, "persisted": True, "mission_file_id": mission_file_id}


async def persist_qa_certificate(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    certificate = issue_qa_certificate(payload)
    await db.execute(
        text(
            """
            INSERT INTO aionx_qa_certificates (
                certificate_id, mission_id, milestone_id, criteria, failures,
                verdict, client_delivery_allowed, next_route, certificate_payload, issued_by
            )
            VALUES (
                :certificate_id, :mission_id, :milestone_id, CAST(:criteria AS jsonb),
                CAST(:failures AS jsonb), :verdict, :client_delivery_allowed,
                :next_route, CAST(:certificate_payload AS jsonb), :issued_by
            )
            ON CONFLICT (certificate_id) DO UPDATE SET
                verdict = EXCLUDED.verdict,
                client_delivery_allowed = EXCLUDED.client_delivery_allowed,
                failures = EXCLUDED.failures,
                next_route = EXCLUDED.next_route,
                updated_at = now()
            """
        ),
        {
            "certificate_id": certificate["certificate_id"],
            "mission_id": payload.get("mission_id"),
            "milestone_id": str(certificate["milestone_id"]),
            "criteria": _json(certificate["criteria"]),
            "failures": _json(certificate["failures"]),
            "verdict": certificate["verdict"],
            "client_delivery_allowed": certificate["client_delivery_allowed"],
            "next_route": certificate["next_route"],
            "certificate_payload": _json(certificate),
            "issued_by": payload.get("issued_by", "QUALITY_ASSURANCE"),
        },
    )
    await record_event(
        db,
        event_type="QA_CERTIFICATE_ISSUED",
        source="QUALITY_ASSURANCE",
        payload=certificate,
        severity="INFO" if certificate["verdict"] == "pass" else "WARNING",
    )
    await db.commit()
    return {**certificate, "persisted": True}


async def persist_repair_instruction(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    repair = create_repair_instruction(payload)
    await db.execute(
        text(
            """
            INSERT INTO aionx_repair_records (
                repair_id, mission_id, milestone_id, defect, root_cause,
                fix_required, verification, priority, route, repair_payload, status
            )
            VALUES (
                :repair_id, :mission_id, :milestone_id, :defect, :root_cause,
                :fix_required, :verification, :priority, :route,
                CAST(:repair_payload AS jsonb), 'OPEN'
            )
            ON CONFLICT (repair_id) DO UPDATE SET
                root_cause = EXCLUDED.root_cause,
                fix_required = EXCLUDED.fix_required,
                verification = EXCLUDED.verification,
                priority = EXCLUDED.priority,
                route = EXCLUDED.route,
                repair_payload = EXCLUDED.repair_payload,
                updated_at = now()
            """
        ),
        {
            "repair_id": repair["repair_id"],
            "mission_id": payload.get("mission_id"),
            "milestone_id": payload.get("milestone_id"),
            "defect": repair["defect"],
            "root_cause": repair["root_cause"],
            "fix_required": repair["fix_required"],
            "verification": repair["verification"],
            "priority": repair["priority"],
            "route": repair["route"],
            "repair_payload": _json(repair),
        },
    )
    await record_event(
        db,
        event_type="REPAIR_INSTRUCTION_CREATED",
        source="REPAIR_RECOVERY",
        payload=repair,
        severity="WARNING" if repair["priority"] in {"HIGH", "CRITICAL"} else "INFO",
    )
    await db.commit()
    return {**repair, "persisted": True}


async def persist_fallback_drill(db: AsyncSession, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    drill = run_fallback_drill(payload)
    await db.execute(
        text(
            """
            INSERT INTO aionx_fallback_drill_records (
                component, failure_mode, fallback, target_activation_seconds,
                captain_notification_required, drill_payload, status
            )
            VALUES (
                :component, :failure_mode, :fallback, :target_activation_seconds,
                :captain_notification_required, CAST(:drill_payload AS jsonb), 'RECORDED'
            )
            """
        ),
        {
            "component": drill["component"],
            "failure_mode": drill["failure_mode"],
            "fallback": drill["fallback"],
            "target_activation_seconds": drill["target_activation_seconds"],
            "captain_notification_required": drill["captain_notification_required"],
            "drill_payload": _json(drill),
        },
    )
    await record_event(
        db,
        event_type="FALLBACK_DRILL_RECORDED",
        source="FALLBACK_CONTINUITY",
        payload=drill,
        severity="INFO",
        captain_approval_required=drill["captain_notification_required"],
    )
    await db.commit()
    return {**drill, "persisted": True}


async def persist_knowledge_synthesis(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    synthesis = synthesize_milestone_learning(payload)
    await db.execute(
        text(
            """
            INSERT INTO aionx_knowledge_synthesis_records (
                synthesis_id, mission_id, milestone_id, what_worked, what_was_harder,
                client_response, memory_targets, case_study_candidate, synthesis_payload
            )
            VALUES (
                :synthesis_id, :mission_id, :milestone_id, CAST(:what_worked AS jsonb),
                CAST(:what_was_harder AS jsonb), :client_response,
                CAST(:memory_targets AS jsonb), :case_study_candidate,
                CAST(:synthesis_payload AS jsonb)
            )
            ON CONFLICT (synthesis_id) DO UPDATE SET
                synthesis_payload = EXCLUDED.synthesis_payload,
                updated_at = now()
            """
        ),
        {
            "synthesis_id": synthesis["synthesis_id"],
            "mission_id": payload.get("mission_id"),
            "milestone_id": synthesis["milestone_id"],
            "what_worked": _json(synthesis["what_worked"]),
            "what_was_harder": _json(synthesis["what_was_harder"]),
            "client_response": synthesis["client_response"],
            "memory_targets": _json(synthesis["memory_targets"]),
            "case_study_candidate": synthesis["case_study_candidate"],
            "synthesis_payload": _json(synthesis),
        },
    )
    await record_event(db, event_type="KNOWLEDGE_SYNTHESIS_CREATED", source="KNOWLEDGE_SYNTHESIS", payload=synthesis)
    await db.commit()
    return {**synthesis, "persisted": True}


async def capture_system_state_snapshot(db: AsyncSession, captured_by: str = "AIONX_STATE_HEARTBEAT") -> dict[str, Any]:
    snapshot = system_state_snapshot()
    await db.execute(
        text(
            """
            INSERT INTO aionx_system_state_snapshots (
                overall_health_score, system_state, snapshot, captured_by
            )
            VALUES (
                :overall_health_score, :system_state, CAST(:snapshot AS jsonb), :captured_by
            )
            """
        ),
        {
            "overall_health_score": float(snapshot.get("overall_health_score", 0)),
            "system_state": snapshot.get("system_state", "UNKNOWN"),
            "snapshot": _json(snapshot),
            "captured_by": captured_by,
        },
    )
    await record_event(db, "SYSTEM_STATE_SNAPSHOT_CAPTURED", captured_by, snapshot)
    await db.commit()
    return {**snapshot, "persisted": True}


async def capture_preventive_monitoring_snapshot(db: AsyncSession) -> dict[str, Any]:
    monitoring = preventive_monitoring_status()
    await record_event(
        db,
        event_type="PREVENTIVE_MONITORING_SNAPSHOT",
        source="PREVENTIVE_MONITORING",
        payload=monitoring,
        severity="INFO",
    )
    await db.commit()
    return {**monitoring, "persisted": True}


async def create_autonomy_proposal(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    proposal = genesis_proposal(payload)
    proposal_id = proposal.get("proposal_id") or f"proposal-{int(datetime.now(timezone.utc).timestamp())}"
    title = payload.get("title") or payload.get("need") or "Governed self-improvement proposal"
    rationale = payload.get("rationale") or proposal.get("rationale") or "AIONX identified an improvement opportunity."
    blast_radius = payload.get("blast_radius", "LOW")
    expected_benefit = payload.get("expected_benefit") or proposal.get("expected_benefit") or "Improve operational resilience."
    rollback_plan = payload.get("rollback_plan") or "Disable proposed change and revert to previous approved configuration."
    await db.execute(
        text(
            """
            INSERT INTO aionx_autonomy_proposals (
                proposal_id, proposal_type, title, rationale, blast_radius,
                expected_benefit, rollback_plan, approval_status, proposal_payload, created_by
            )
            VALUES (
                :proposal_id, :proposal_type, :title, :rationale, :blast_radius,
                :expected_benefit, :rollback_plan, 'PENDING_CAPTAIN_REVIEW',
                CAST(:proposal_payload AS jsonb), :created_by
            )
            ON CONFLICT (proposal_id) DO UPDATE SET
                title = EXCLUDED.title,
                rationale = EXCLUDED.rationale,
                expected_benefit = EXCLUDED.expected_benefit,
                rollback_plan = EXCLUDED.rollback_plan,
                proposal_payload = EXCLUDED.proposal_payload,
                updated_at = now()
            """
        ),
        {
            "proposal_id": proposal_id,
            "proposal_type": payload.get("proposal_type", "SELF_IMPROVEMENT"),
            "title": str(title),
            "rationale": str(rationale),
            "blast_radius": str(blast_radius),
            "expected_benefit": str(expected_benefit),
            "rollback_plan": str(rollback_plan),
            "proposal_payload": _json(proposal),
            "created_by": payload.get("created_by", "GENESIS_ENGINE"),
        },
    )
    await record_event(
        db,
        "AUTONOMY_PROPOSAL_CREATED",
        "GENESIS_ENGINE",
        proposal,
        severity="WARNING" if str(blast_radius).upper() in {"HIGH", "CRITICAL"} else "INFO",
        captain_approval_required=True,
    )
    await db.commit()
    return {**proposal, "proposal_id": proposal_id, "persisted": True, "approval_status": "PENDING_CAPTAIN_REVIEW"}


async def record_external_scan(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    findings = payload.get("findings") or [
        "External scan connector recorded; authenticated crawling sources can be attached by provider."
    ]
    recommended_actions = payload.get("recommended_actions") or [
        "Review scan findings before any production adaptation.",
        "Escalate strong signals to Provider Sovereign Council.",
    ]
    scan = {
        "scan_type": payload.get("scan_type", "TECH_RADAR"),
        "source": payload.get("source", "AIONX_SENTINEL"),
        "summary": payload.get("summary", "Governed external scan record created."),
        "findings": findings,
        "recommended_actions": recommended_actions,
        "guardrail": "Scan records may inform proposals; they cannot self-execute production changes.",
    }
    await db.execute(
        text(
            """
            INSERT INTO aionx_external_scan_records (
                scan_type, source, summary, findings, recommended_actions, scan_payload
            )
            VALUES (
                :scan_type, :source, :summary, CAST(:findings AS jsonb),
                CAST(:recommended_actions AS jsonb), CAST(:scan_payload AS jsonb)
            )
            """
        ),
        {
            "scan_type": scan["scan_type"],
            "source": scan["source"],
            "summary": scan["summary"],
            "findings": _json(findings),
            "recommended_actions": _json(recommended_actions),
            "scan_payload": _json(scan),
        },
    )
    await record_event(db, "EXTERNAL_SCAN_RECORDED", scan["source"], scan)
    await db.commit()
    return {**scan, "persisted": True}


async def run_governed_integrity_cycle(db: AsyncSession) -> dict[str, Any]:
    state = await capture_system_state_snapshot(db, captured_by="AIONX_GOVERNED_INTEGRITY_CYCLE")
    monitoring = await capture_preventive_monitoring_snapshot(db)
    immune = immune_scan({"content": f"system_state={state.get('system_state')}", "source": "integrity_cycle"})
    proposal = None
    if float(state.get("overall_health_score", 0)) < 75:
        proposal = await create_autonomy_proposal(
            db,
            {
                "need": "Operational health is below target; propose governed remediation plan.",
                "title": "Operational health remediation proposal",
                "blast_radius": "LOW",
                "expected_benefit": "Increase system resilience without autonomous production mutation.",
            },
        )
    return {
        "status": "governed_integrity_cycle_recorded",
        "state_health": state.get("overall_health_score"),
        "monitoring_dimensions": monitoring.get("dimension_count"),
        "immune_verdict": immune.get("verdict"),
        "proposal_created": bool(proposal),
        "proposal": proposal,
    }


async def operational_persistence_status(db: AsyncSession) -> dict[str, Any]:
    tables = [
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
    ]
    counts: dict[str, int] = {}
    for table in tables:
        try:
            result = await db.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
            counts[table] = int(result.scalar_one())
        except Exception:
            counts[table] = -1
    return {
        "status": "operational_persistence_live",
        "table_count": len(tables),
        "tables": tables,
        "counts": counts,
        "governance_boundary": (
            "Persistence, scans, proposals, and snapshots are autonomous. "
            "External production changes and self-modification remain Captain-approval gated."
        ),
    }


async def latest_persisted_records(db: AsyncSession, limit: int = 10) -> dict[str, Any]:
    queries = {
        "events": "SELECT event_type, source, severity, governance_status, created_at FROM aionx_event_spine ORDER BY created_at DESC LIMIT :limit",
        "missions": "SELECT mission_id, client_name, mission_status, created_at FROM aionx_mission_files ORDER BY created_at DESC LIMIT :limit",
        "qa": "SELECT certificate_id, verdict, client_delivery_allowed, created_at FROM aionx_qa_certificates ORDER BY created_at DESC LIMIT :limit",
        "repairs": "SELECT repair_id, priority, status, created_at FROM aionx_repair_records ORDER BY created_at DESC LIMIT :limit",
        "proposals": "SELECT proposal_id, title, approval_status, created_at FROM aionx_autonomy_proposals ORDER BY created_at DESC LIMIT :limit",
        "snapshots": "SELECT overall_health_score, system_state, captured_by, created_at FROM aionx_system_state_snapshots ORDER BY created_at DESC LIMIT :limit",
    }
    data: dict[str, list[dict[str, Any]]] = {}
    for key, query in queries.items():
        result = await db.execute(text(query), {"limit": limit})
        data[key] = [dict(row._mapping) for row in result.fetchall()]
    return {"status": "latest_records", "limit": limit, "records": data}


async def record_event(
    db: AsyncSession,
    event_type: str,
    source: str,
    payload: dict[str, Any],
    severity: str = "INFO",
    captain_approval_required: bool = False,
    correlation_id: str | None = None,
) -> None:
    await db.execute(
        text(
            """
            INSERT INTO aionx_event_spine (
                event_type, source, severity, correlation_id, payload,
                governance_status, captain_approval_required
            )
            VALUES (
                :event_type, :source, :severity, :correlation_id,
                CAST(:payload AS jsonb), :governance_status, :captain_approval_required
            )
            """
        ),
        {
            "event_type": event_type,
            "source": source,
            "severity": severity,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "payload": _json(payload),
            "governance_status": "PENDING_CAPTAIN_REVIEW" if captain_approval_required else "RECORDED",
            "captain_approval_required": captain_approval_required,
        },
    )


def _json(value: Any) -> str:
    import json

    return json.dumps(value, default=str)
