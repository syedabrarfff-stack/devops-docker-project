from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.lead import Lead
from app.models.outreach import OutreachLog, OutreachStatus, ReplyLog
from app.models.revenue_activation import OutreachLearning
from app.services.memory.memory_engine import memory_engine


class TeachingEngine:
    async def list_learnings(self, tenant_id=None, category: str | None = None, limit: int = 50) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                query = select(OutreachLearning).where(OutreachLearning.tenant_id == tenant_uuid)
                if category:
                    query = query.where(OutreachLearning.category == category)
                rows = (
                    await session.execute(
                        query.order_by(OutreachLearning.created_at.desc()).limit(max(1, min(limit, 200)))
                    )
                ).scalars().all()
        return {
            "tenant_id": str(tenant_uuid),
            "count": len(rows),
            "learnings": [_serialize_learning(row) for row in rows],
        }

    async def teach(
        self,
        *,
        tenant_id=None,
        title: str,
        learning: str,
        category: str = "outreach_intelligence",
        source_type: str = "captain_manual",
        source_id: str | None = None,
        score: float = 80.0,
        evidence: dict | None = None,
        applies_to: dict | None = None,
        created_by: str = "Captain",
    ) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                record = OutreachLearning(
                    tenant_id=tenant_uuid,
                    category=category,
                    title=title[:300],
                    learning=learning,
                    source_type=source_type,
                    source_id=source_id,
                    score=float(score or 0.0),
                    evidence_json=evidence or {},
                    applies_to_json=applies_to or {},
                    created_by=created_by,
                )
                session.add(record)
                await session.flush()
                session.add(
                    AuditLog(
                        tenant_id=tenant_uuid,
                        action="teaching_learning_stored",
                        entity_type="outreach_learning",
                        entity_id=record.id,
                        actor=created_by,
                        details={
                            "category": category,
                            "title": title,
                            "source_type": source_type,
                            "score": score,
                        },
                    )
                )
                await session.refresh(record)

        await memory_engine.store_strategic(
            category=category,
            content=json.dumps(
                {
                    "title": title,
                    "learning": learning,
                    "source_type": source_type,
                    "source_id": source_id,
                    "score": score,
                    "evidence": evidence or {},
                    "applies_to": applies_to or {},
                },
                default=str,
            ),
            tags=["m2", category, source_type, "revenue_activation"],
            tenant_id=tenant_uuid,
        )
        return {"stored": True, "id": str(record.id), "category": category, "title": record.title}

    async def analyze_recent_outreach(self, tenant_id=None, days: int = 30) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        cutoff = datetime.now(UTC) - timedelta(days=max(1, min(days, 90)))
        created = 0
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                rows = (
                    await session.execute(
                        select(
                            OutreachLog.subject,
                            OutreachLog.sent_from_persona,
                            OutreachLog.status,
                            func.count(OutreachLog.id),
                        )
                        .where(OutreachLog.tenant_id == tenant_uuid, OutreachLog.created_at >= cutoff)
                        .group_by(OutreachLog.subject, OutreachLog.sent_from_persona, OutreachLog.status)
                    )
                ).all()

                grouped: dict[str, dict[str, Any]] = {}
                for subject, persona, status, count in rows:
                    key = f"{subject or 'no subject'}::{persona or 'unknown'}"
                    entry = grouped.setdefault(
                        key,
                        {
                            "subject": subject or "no subject",
                            "persona": persona or "unknown",
                            "sent": 0,
                            "opened": 0,
                            "replied": 0,
                            "ignored": 0,
                        },
                    )
                    status_value = getattr(status, "value", str(status)).lower()
                    count_int = int(count or 0)
                    if status_value == OutreachStatus.OPENED.value.lower():
                        entry["opened"] += count_int
                    elif status_value == OutreachStatus.REPLIED.value.lower():
                        entry["replied"] += count_int
                    elif status_value == OutreachStatus.SENT.value.lower():
                        entry["sent"] += count_int
                    else:
                        entry["ignored"] += count_int

        for entry in grouped.values():
            total = max(1, entry["sent"] + entry["opened"] + entry["replied"] + entry["ignored"])
            open_rate = round((entry["opened"] + entry["replied"]) / total, 3)
            reply_rate = round(entry["replied"] / total, 3)
            if total < 1:
                continue
            await self.teach(
                tenant_id=tenant_uuid,
                title=f"Outreach pattern: {entry['subject'][:80]}",
                learning=(
                    f"Subject '{entry['subject']}' from {entry['persona']} produced "
                    f"open_rate={open_rate}, reply_rate={reply_rate}, total_events={total}. "
                    "Use this as evidence when choosing future outreach structure."
                ),
                category="outreach_intelligence",
                source_type="outreach_analysis",
                source_id=entry["subject"],
                score=round((open_rate * 70) + (reply_rate * 30), 2),
                evidence=entry,
                applies_to={"persona": entry["persona"], "subject": entry["subject"]},
                created_by="TeachingEngine",
            )
            created += 1
        return {"analyzed": len(grouped), "learnings_created": created}

    async def learn_from_call_debrief(
        self,
        *,
        tenant_id=None,
        lead: Lead,
        call_outcome: str,
        notes: str,
        next_action: str,
    ) -> dict[str, Any]:
        outcome = (call_outcome or "follow-up").lower()
        score = {"won": 95.0, "follow-up": 70.0, "lost": 40.0}.get(outcome, 60.0)
        return await self.teach(
            tenant_id=tenant_id,
            title=f"Call outcome pattern: {lead.company_name or lead.company or lead.id}",
            learning=(
                f"Call outcome was {outcome}. Notes: {notes[:800]}. "
                f"Next action: {next_action}. Use this pattern when briefing similar calls."
            ),
            category="call_intelligence",
            source_type="call_debrief",
            source_id=str(lead.id),
            score=score,
            evidence={
                "lead_id": str(lead.id),
                "company": lead.company_name or lead.company,
                "industry": lead.industry,
                "score": lead.score,
                "outcome": outcome,
            },
            applies_to={"industry": lead.industry, "country": lead.country, "outcome": outcome},
            created_by="CallRoomService",
        )


def _serialize_learning(row: OutreachLearning) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "category": row.category,
        "title": row.title,
        "learning": row.learning,
        "source_type": row.source_type,
        "source_id": row.source_id,
        "score": row.score,
        "evidence": row.evidence_json or {},
        "applies_to": row.applies_to_json or {},
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _tenant_uuid(value=None) -> uuid.UUID:
    raw = value or settings.JARVIS_DEFAULT_TENANT_ID
    if not raw:
        raise ValueError("tenant_id is required")
    return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))


teaching_engine = TeachingEngine()

