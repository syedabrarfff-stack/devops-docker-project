from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.lead import Lead
from app.models.memory import MemoryGraphNode
from app.models.outreach import FollowUpQueue, FollowUpStatus
from app.services.intelligence.morning_briefing import MorningBriefingEngine
from app.services.memory.graph import graph_status, seed_memory_graph
from app.services.outreach.engine import outreach_engine


class PilotActivationService:
    async def status(self, tenant_id: uuid.UUID | str) -> dict[str, Any]:
        tenant_uuid = _coerce_tenant_id(tenant_id)
        memory = await graph_status(tenant_uuid)
        confidence = self._confidence(memory["nodes"])
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                pending_outreach = await session.scalar(
                    select(func.count()).select_from(FollowUpQueue).where(
                        FollowUpQueue.tenant_id == tenant_uuid,
                        FollowUpQueue.status == FollowUpStatus.PENDING,
                    )
                )
                qualified_leads = await session.scalar(
                    select(func.count()).select_from(Lead).where(
                        Lead.tenant_id == tenant_uuid,
                        Lead.score >= 60,
                    )
                )
        return {
            "pilot_ready": bool(settings.PILOT_READY and confidence >= settings.AUTONOMOUS_CONFIDENCE_THRESHOLD),
            "confidence": round(confidence, 3),
            "confidence_threshold": settings.AUTONOMOUS_CONFIDENCE_THRESHOLD,
            "external_api_blockers_bypassed_for_pilot": settings.EXTERNAL_API_BLOCKERS_BYPASSED_FOR_PILOT,
            "memory": memory,
            "qualified_leads": int(qualified_leads or 0),
            "outreach_queue_count": int(pending_outreach or 0),
        }

    async def activate(self, tenant_id: uuid.UUID | str) -> dict[str, Any]:
        tenant_uuid = _coerce_tenant_id(tenant_id)
        memory = await seed_memory_graph(tenant_uuid)
        lead_id = await self._queue_best_lead(tenant_uuid)
        briefing = await MorningBriefingEngine().generate_and_send(tenant_uuid)
        status = await self.status(tenant_uuid)
        return {
            **status,
            "memory_seed": memory,
            "activated_lead_id": str(lead_id) if lead_id else None,
            "morning_briefing_generated": True,
            "morning_briefing_preview": briefing[:800],
        }

    async def _queue_best_lead(self, tenant_id: uuid.UUID) -> uuid.UUID | None:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_id))
                lead = (
                    await session.execute(
                        select(Lead)
                        .where(Lead.tenant_id == tenant_id, Lead.score >= 60)
                        .order_by(Lead.score.desc(), Lead.created_at.asc())
                        .limit(1)
                    )
                ).scalar_one_or_none()
                if not lead:
                    session.add(
                        AuditLog(
                            tenant_id=tenant_id,
                            action="pilot_activation_no_qualified_lead",
                            entity_type="pilot",
                            actor="PilotActivationService",
                            details={"minimum_score": 60},
                        )
                    )
                    return None
                lead_id = lead.id

        await outreach_engine.queue_sequence(lead_id, tenant_id)
        await self._set_pilot_schedule(tenant_id, lead_id)
        return lead_id

    async def _set_pilot_schedule(self, tenant_id: uuid.UUID, lead_id: uuid.UUID) -> None:
        now = datetime.now(timezone.utc)
        schedule = {
            1: now + timedelta(days=1),
            2: now + timedelta(days=4),
            3: now + timedelta(days=8),
        }
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_id))
                items = (
                    await session.execute(
                        select(FollowUpQueue).where(
                            FollowUpQueue.tenant_id == tenant_id,
                            FollowUpQueue.lead_id == lead_id,
                            FollowUpQueue.status == FollowUpStatus.PENDING,
                        )
                    )
                ).scalars().all()
                for item in items:
                    item.scheduled_at = schedule.get(item.sequence_step, item.scheduled_at)
                session.add(
                    AuditLog(
                        tenant_id=tenant_id,
                        action="pilot_outreach_activated",
                        entity_type="lead",
                        entity_id=lead_id,
                        actor="PilotActivationService",
                        details={
                            "email_1": schedule[1].isoformat(),
                            "email_2": schedule[2].isoformat(),
                            "email_3": schedule[3].isoformat(),
                            "queued_items": len(items),
                        },
                    )
                )

    def _confidence(self, memory_nodes: int) -> float:
        memory_boost = 0.05 if memory_nodes > 0 else 0.0
        return settings.SYSTEM_CONFIDENCE_BASE + memory_boost


def _coerce_tenant_id(tenant_id: uuid.UUID | str) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


pilot_activation_service = PilotActivationService()
