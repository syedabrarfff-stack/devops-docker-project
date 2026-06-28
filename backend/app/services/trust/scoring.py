import logging
from uuid import UUID
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.trust_engine import LeadEngagementEvent

logger = logging.getLogger(__name__)

EVENT_WEIGHTS = {
    "email_opened": 5,
    "reply_received": 20,
    "meeting_attended": 25,
    "demo_watched": 30,
    "brief_viewed": 15,
    "proposal_viewed": 20,
    "technical_question": 15,
    "decision_maker_contacted": 25,
    "contract_viewed": 35,
}
MAX_TRUST_SCORE = 100


async def compute_scores(lead_id: UUID) -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(LeadEngagementEvent).where(LeadEngagementEvent.lead_id == lead_id)
        )
        events = result.scalars().all()

    raw_score = 0.0
    events_summary: dict[str, int] = {}
    for event in events:
        raw_score += EVENT_WEIGHTS.get(event.event_type, event.weight)
        events_summary[event.event_type] = events_summary.get(event.event_type, 0) + 1

    trust_score = min(raw_score, MAX_TRUST_SCORE)
    conversion_probability = int(min(trust_score / 60.0, 1.0) * 100)

    return {
        "trust_score": trust_score,
        "conversion_probability": conversion_probability,
        "event_count": len(events),
        "events_summary": events_summary,
        "ready_for_proposal": trust_score >= 40,
    }


async def log_event(
    lead_id: UUID,
    event_type: str,
    source: str = "",
    metadata: dict | None = None,
) -> dict:
    weight = float(EVENT_WEIGHTS.get(event_type, 1.0))

    async with AsyncSessionLocal() as db:
        event = LeadEngagementEvent(
            lead_id=lead_id,
            event_type=event_type,
            weight=weight,
            source=source or None,
            metadata_json=metadata or {},
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        event_dict = {
            "id": event.id,
            "lead_id": str(event.lead_id) if event.lead_id else None,
            "event_type": event.event_type,
            "weight": event.weight,
            "source": event.source,
            "metadata": event.metadata_json or {},
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }

    scores = await compute_scores(lead_id)
    return {**event_dict, "scores": scores}
