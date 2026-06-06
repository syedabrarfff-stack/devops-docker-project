from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.communication import (
    CommunicationChannel,
    CommunicationChannelStatus,
    CommunicationDirection,
    CommunicationEvent,
)


async def record_communication_event(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    channel: CommunicationChannel | str,
    direction: CommunicationDirection | str,
    transport: str,
    external_message_id: str | None = None,
    thread_id: str | None = None,
    from_address: str | None = None,
    to_address: str | None = None,
    contact_name: str | None = None,
    lead_id: uuid.UUID | None = None,
    client_id: uuid.UUID | None = None,
    contact_id: int | None = None,
    subject: str | None = None,
    body_text: str | None = None,
    status: str = "received",
    hia_persona: str = "Joseph David",
    processing_summary: dict[str, Any] | None = None,
    raw_payload: dict[str, Any] | None = None,
    processed_at: datetime | None = None,
) -> CommunicationEvent:
    event = CommunicationEvent(
        tenant_id=tenant_id,
        channel=CommunicationChannel(channel),
        direction=CommunicationDirection(direction),
        transport=transport,
        external_message_id=external_message_id,
        thread_id=thread_id,
        from_address=from_address,
        to_address=to_address,
        contact_name=contact_name,
        lead_id=lead_id,
        client_id=client_id,
        contact_id=contact_id,
        subject=subject,
        body_text=body_text,
        status=status,
        hia_persona=hia_persona,
        processing_summary=processing_summary or {},
        raw_payload=raw_payload or {},
        processed_at=processed_at,
    )
    db.add(event)
    await db.flush()
    return event


async def update_channel_status(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    channel: CommunicationChannel | str,
    provider: str,
    identity: str | None,
    configured: bool,
    connected: bool,
    status: str,
    blocker_code: str | None = None,
    required_action: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    values = {
        "tenant_id": tenant_id,
        "channel": CommunicationChannel(channel).value,
        "provider": provider,
        "identity": identity,
        "configured": configured,
        "connected": connected,
        "status": status,
        "blocker_code": blocker_code,
        "required_action": required_action,
        "details": details or {},
        "last_checked_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    stmt = pg_insert(CommunicationChannelStatus).values(**values)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_communication_channel_provider",
        set_=values,
    )
    await db.execute(stmt)


async def communication_counts(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    rows = await db.execute(
        select(
            CommunicationEvent.channel,
            CommunicationEvent.direction,
            func.count(CommunicationEvent.id),
        )
        .where(CommunicationEvent.tenant_id == tenant_id)
        .group_by(CommunicationEvent.channel, CommunicationEvent.direction)
    )
    counts: dict[str, dict[str, int]] = {
        "EMAIL": {"INBOUND": 0, "OUTBOUND": 0},
        "WHATSAPP": {"INBOUND": 0, "OUTBOUND": 0},
    }
    for channel, direction, count in rows.all():
        counts[str(channel.value if hasattr(channel, "value") else channel)][str(direction.value if hasattr(direction, "value") else direction)] = int(count or 0)
    return counts


async def recent_events(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    channel: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    query = (
        select(CommunicationEvent)
        .where(CommunicationEvent.tenant_id == tenant_id)
        .order_by(CommunicationEvent.created_at.desc())
        .limit(max(1, min(int(limit or 50), 200)))
    )
    if channel:
        query = query.where(CommunicationEvent.channel == CommunicationChannel(channel.upper()))
    events = (await db.execute(query)).scalars().all()
    return [
        {
            "id": str(event.id),
            "channel": event.channel.value,
            "direction": event.direction.value,
            "transport": event.transport,
            "status": event.status,
            "from": event.from_address,
            "to": event.to_address,
            "contact_name": event.contact_name,
            "lead_id": str(event.lead_id) if event.lead_id else None,
            "subject": event.subject,
            "preview": (event.body_text or "")[:240],
            "hia_persona": event.hia_persona,
            "processing_summary": event.processing_summary,
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "processed_at": event.processed_at.isoformat() if event.processed_at else None,
        }
        for event in events
    ]
