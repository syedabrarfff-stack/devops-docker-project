from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.innovation import InnovationQueueItem, InnovationStatus
from app.services.civilization import civilization_ledger
from app.services.memory.graph import _upsert_node


SEED_PROPOSALS = [
    (
        "Competitor monitoring frequency tuner",
        "Adjust competitor checks based on how often each competitor changes pricing, service pages, or positioning.",
        86,
        82,
        "Market Intelligence",
    ),
    (
        "Outreach subject-line A/B testing",
        "Automatically test two subject lines per service category and promote the winner by reply rate.",
        92,
        78,
        "Revenue Command",
    ),
    (
        "Client health scoring model",
        "Score every client by delivery progress, reply speed, invoice status, satisfaction signals, and renewal risk.",
        90,
        74,
        "Client Success",
    ),
    (
        "Lead source ROI attribution",
        "Track every lead source through outreach, replies, demos, proposals, and closed revenue.",
        88,
        80,
        "Finance Center",
    ),
    (
        "Demo-to-proposal conversion tracker",
        "Record which demo packages produce calls, proposals, and payment, then tune demo copy by industry.",
        84,
        83,
        "Demo Builder",
    ),
    (
        "Pricing objection memory bank",
        "Store pricing objections and winning responses so future proposals can handle them earlier.",
        81,
        87,
        "Proposal Architect",
    ),
    (
        "LinkedIn URL enrichment task",
        "Detect leads missing LinkedIn URLs and queue enrichment tasks before LinkedIn sequence generation.",
        78,
        88,
        "Outreach",
    ),
    (
        "Telegram activation watchdog",
        "Check Telegram token validity daily and surface a clear activation warning until mobile alerts work.",
        72,
        92,
        "Notifications",
    ),
    (
        "Cost-aware model routing",
        "Route low-risk tasks to lower-cost models and reserve premium reasoning models for proposals, strategy, and risk.",
        89,
        76,
        "AI Operations",
    ),
    (
        "First-client war-room dashboard",
        "Create a focused dashboard view only for first-client acquisition: lead, email, reply, demo, proposal, close.",
        95,
        70,
        "Command Center",
    ),
]


class InnovationQueueService:
    async def seed(self, tenant_id) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        created = 0
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                for title, description, impact, feasibility, proposed_by in SEED_PROPOSALS:
                    existing = await session.scalar(
                        select(InnovationQueueItem)
                        .where(InnovationQueueItem.tenant_id == tenant_uuid, InnovationQueueItem.title == title)
                        .limit(1)
                    )
                    if existing:
                        continue
                    session.add(
                        InnovationQueueItem(
                            tenant_id=tenant_uuid,
                            title=title,
                            description=description,
                            impact_score=float(impact),
                            feasibility_score=float(feasibility),
                            priority_score=_priority(impact, feasibility),
                            status=InnovationStatus.PROPOSED.value,
                            proposed_by=proposed_by,
                            council_approved=False,
                        )
                    )
                    created += 1
                session.add(
                    AuditLog(
                        tenant_id=tenant_uuid,
                        action="innovation_queue_seeded",
                        entity_type="innovation_queue",
                        actor="InnovationQueueService",
                        details={"created": created},
                    )
                )
        return {"seeded": created, "queue_ready": True}

    async def list_queue(self, tenant_id) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                rows = (
                    await session.execute(
                        select(InnovationQueueItem)
                        .where(InnovationQueueItem.tenant_id == tenant_uuid)
                        .order_by(InnovationQueueItem.priority_score.desc(), InnovationQueueItem.created_at.asc())
                        .limit(200)
                    )
                ).scalars().all()
        return {"count": len(rows), "items": [_serialize(row) for row in rows]}

    async def propose(
        self,
        tenant_id,
        *,
        title: str,
        description: str,
        impact_score: float,
        feasibility_score: float,
        proposed_by: str,
    ) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        impact = _bounded(impact_score)
        feasibility = _bounded(feasibility_score)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                item = InnovationQueueItem(
                    tenant_id=tenant_uuid,
                    title=title.strip(),
                    description=description.strip(),
                    impact_score=impact,
                    feasibility_score=feasibility,
                    priority_score=_priority(impact, feasibility),
                    status=InnovationStatus.PROPOSED.value,
                    proposed_by=proposed_by.strip() or "JARVIS",
                    council_approved=False,
                )
                session.add(item)
                await session.flush()
                session.add(
                    AuditLog(
                        tenant_id=tenant_uuid,
                        action="innovation_item_proposed",
                        entity_type="innovation_queue",
                        entity_id=item.id,
                        actor=item.proposed_by,
                        details={"title": item.title, "priority_score": item.priority_score},
                    )
                )
                payload = _serialize(item)
        return payload

    async def weekly_council_review(self, tenant_id) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        await self.seed(tenant_uuid)
        reviewed = []
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                rows = (
                    await session.execute(
                        select(InnovationQueueItem)
                        .where(
                            InnovationQueueItem.tenant_id == tenant_uuid,
                            InnovationQueueItem.status == InnovationStatus.PROPOSED.value,
                        )
                        .order_by(InnovationQueueItem.priority_score.desc(), InnovationQueueItem.created_at.asc())
                        .limit(3)
                    )
                ).scalars().all()
                for item in rows:
                    approved = float(item.priority_score or 0.0) >= 60.0
                    item.council_approved = approved
                    item.status = InnovationStatus.IMPLEMENTING.value if approved else InnovationStatus.PROPOSED.value
                    item.review_notes = (
                        "Council approved for implementation because priority score is above the execution threshold."
                        if approved
                        else "Council held this proposal for more evidence before implementation."
                    )
                    reviewed.append(_serialize(item))
                session.add(
                    AuditLog(
                        tenant_id=tenant_uuid,
                        action="innovation_council_review_completed",
                        entity_type="innovation_queue",
                        actor="InnovationCouncil",
                        details={"reviewed": reviewed},
                    )
                )
        return {"reviewed": len(reviewed), "items": reviewed}

    async def mark_deployed(self, tenant_id, item_id) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        item_uuid = _tenant_uuid(item_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                item = await session.scalar(
                    select(InnovationQueueItem).where(
                        InnovationQueueItem.tenant_id == tenant_uuid,
                        InnovationQueueItem.id == item_uuid,
                    )
                )
                if not item:
                    raise ValueError("Innovation item not found")
                item.status = InnovationStatus.DEPLOYED.value
                item.council_approved = True
                await civilization_ledger.append_event(
                    session,
                    tenant_uuid,
                    event_type="system_upgrade",
                    title=f"Innovation deployed: {item.title}",
                    description=item.description,
                    impact="system_upgrade",
                    actors=[item.proposed_by, "JARVIS"],
                    data_snapshot={"innovation_item_id": str(item.id), "priority_score": item.priority_score},
                    milestone=True,
                    dedupe=True,
                )
                await _upsert_node(
                    session,
                    tenant_uuid,
                    node_type="civilization_milestone",
                    title=f"Innovation deployed: {item.title}",
                    content=(
                        f"JARVIS deployed an improvement from the innovation queue. "
                        f"Description: {item.description}. Priority score: {item.priority_score}."
                    ),
                    source_table="innovation_queue",
                    source_id=f"{item.id}:deployed",
                    metadata={
                        "innovation_item_id": str(item.id),
                        "impact_score": item.impact_score,
                        "feasibility_score": item.feasibility_score,
                        "priority_score": item.priority_score,
                        "proposed_by": item.proposed_by,
                    },
                )
                session.add(
                    AuditLog(
                        tenant_id=tenant_uuid,
                        action="innovation_item_deployed",
                        entity_type="innovation_queue",
                        entity_id=item.id,
                        actor="InnovationQueueService",
                        details={"title": item.title},
                    )
                )
                payload = _serialize(item)
        return payload


innovation_queue_service = InnovationQueueService()


def _priority(impact: float, feasibility: float) -> float:
    return round((_bounded(impact) * _bounded(feasibility)) / 100.0, 2)


def _bounded(value: float) -> float:
    return max(0.0, min(100.0, float(value or 0.0)))


def _serialize(row: InnovationQueueItem) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "title": row.title,
        "description": row.description,
        "impact_score": float(row.impact_score or 0.0),
        "feasibility_score": float(row.feasibility_score or 0.0),
        "priority_score": float(row.priority_score or 0.0),
        "status": row.status,
        "proposed_by": row.proposed_by,
        "council_approved": row.council_approved,
        "review_notes": row.review_notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _tenant_uuid(value) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
