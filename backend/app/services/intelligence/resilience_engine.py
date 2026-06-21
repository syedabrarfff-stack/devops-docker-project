"""
JARVIS Operational Resilience Engine — Automatic playbook execution for system failures.
Ensures company survival during any infrastructure or business disruption.
10 incident types. Auto-escalation. Captain notification on critical/high severity.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.core.database import AsyncSessionLocal, set_tenant_context
from app.services.intelligence.incident_playbooks import (
    INCIDENT_PLAYBOOK_REGISTRY,
    format_captain_alert,
)

logger = logging.getLogger(__name__)

SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


def _coerce_tenant_id(tenant_id: Any) -> UUID:
    if tenant_id is None:
        return SYSTEM_TENANT_ID
    if isinstance(tenant_id, UUID):
        return tenant_id
    return UUID(str(tenant_id))


class ResilienceEngine:
    """Detects incidents, executes playbooks, tracks recovery, notifies Captain."""

    async def detect_and_respond(
        self,
        tenant_id: Any,
        incident_type: str,
        details: dict | None = None,
    ) -> dict:
        from app.models.truth_resilience import ResilienceEvent
        tid = _coerce_tenant_id(tenant_id)
        playbook = INCIDENT_PLAYBOOK_REGISTRY.get(incident_type, {})
        severity = playbook.get("severity", "medium")
        should_notify = severity in ("critical", "high")

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            event = ResilienceEvent(
                tenant_id=tid,
                incident_type=incident_type,
                severity=severity,
                status="detected",
                playbook_used=incident_type,
                escalation_path=playbook.get("immediate_actions", []),
                fallback_systems_activated=playbook.get("fallback_systems", []),
                recovery_steps_taken=playbook.get("immediate_actions", []),
                estimated_recovery_minutes=playbook.get("estimated_rto_minutes"),
                captain_notified=should_notify,
                impact_summary=details.get("impact_summary") if details else None,
                detected_at=datetime.now(timezone.utc),
            )
            db.add(event)
            await db.flush()
            event_id = event.id
            await db.commit()

        if should_notify:
            alert_msg = format_captain_alert(incident_type, details)
            try:
                from app.services.notifications import notify_telegram, notify_slack
                await notify_telegram(alert_msg)
                await notify_slack(alert_msg)
            except Exception as exc:
                logger.warning("Failed to send resilience alert: %s", exc)

        logger.warning(
            "Resilience incident detected: type=%s severity=%s event_id=%s",
            incident_type,
            severity,
            event_id,
        )

        return {
            "event_id": event_id,
            "incident_type": incident_type,
            "severity": severity,
            "status": "detected",
            "playbook": playbook.get("name", incident_type),
            "immediate_actions": playbook.get("immediate_actions", []),
            "estimated_recovery_minutes": playbook.get("estimated_rto_minutes"),
            "captain_notified": should_notify,
            "captain_alert": format_captain_alert(incident_type, details) if should_notify else None,
        }

    async def resolve_incident(
        self,
        tenant_id: Any,
        event_id: int,
        resolution_notes: str,
    ) -> dict:
        from app.models.truth_resilience import ResilienceEvent
        from sqlalchemy import select
        tid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            result = await db.execute(
                select(ResilienceEvent).where(
                    ResilienceEvent.id == event_id,
                    ResilienceEvent.tenant_id == tid,
                )
            )
            event = result.scalar_one_or_none()
            if not event:
                return {"error": "incident not found"}

            resolved_at = datetime.now(timezone.utc)
            event.status = "resolved"
            event.resolution_notes = resolution_notes
            event.resolved_at = resolved_at

            if event.detected_at:
                delta = resolved_at - event.detected_at
                event.actual_recovery_minutes = int(delta.total_seconds() / 60)

            await db.commit()
            return {
                "event_id": event_id,
                "status": "resolved",
                "actual_recovery_minutes": event.actual_recovery_minutes,
                "resolution_notes": resolution_notes,
            }

    async def get_active_incidents(self, tenant_id: Any) -> list:
        from app.models.truth_resilience import ResilienceEvent
        from sqlalchemy import select
        tid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            result = await db.execute(
                select(ResilienceEvent).where(
                    ResilienceEvent.tenant_id == tid,
                    ResilienceEvent.status != "resolved",
                ).order_by(ResilienceEvent.detected_at.desc())
            )
            events = result.scalars().all()
            return [
                {
                    "event_id": e.id,
                    "incident_type": e.incident_type,
                    "severity": e.severity,
                    "status": e.status,
                    "playbook_used": e.playbook_used,
                    "estimated_recovery_minutes": e.estimated_recovery_minutes,
                    "captain_notified": e.captain_notified,
                    "detected_at": e.detected_at.isoformat() if e.detected_at else None,
                }
                for e in events
            ]

    async def get_resilience_status(self, tenant_id: Any) -> dict:
        from app.models.truth_resilience import ResilienceEvent
        from sqlalchemy import select
        tid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            active_result = await db.execute(
                select(ResilienceEvent).where(
                    ResilienceEvent.tenant_id == tid,
                    ResilienceEvent.status != "resolved",
                )
            )
            active = active_result.scalars().all()

            last_result = await db.execute(
                select(ResilienceEvent).where(ResilienceEvent.tenant_id == tid).order_by(ResilienceEvent.detected_at.desc()).limit(1)
            )
            last_incident = last_result.scalar_one_or_none()

        return {
            "active_incident_count": len(active),
            "system_health": "degraded" if active else "nominal",
            "last_incident": {
                "type": last_incident.incident_type,
                "severity": last_incident.severity,
                "status": last_incident.status,
                "detected_at": last_incident.detected_at.isoformat() if last_incident and last_incident.detected_at else None,
            } if last_incident else None,
            "playbooks_available": list(INCIDENT_PLAYBOOK_REGISTRY.keys()),
            "playbook_count": len(INCIDENT_PLAYBOOK_REGISTRY),
            "active_incidents": [
                {"type": e.incident_type, "severity": e.severity}
                for e in active
            ],
        }


resilience_engine = ResilienceEngine()
