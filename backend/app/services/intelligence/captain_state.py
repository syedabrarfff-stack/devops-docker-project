from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta
from statistics import mean
from typing import Any

from sqlalchemy import func, or_, select

from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import ApprovalRequest, ApprovalStatus, AuditLog
from app.models.conversation import Conversation
from app.services.memory.graph import _upsert_node
from app.services.notifications.telegram import notify_telegram


class CaptainAwarenessEngine:
    async def current_state(self, tenant_id) -> dict[str, Any]:
        tenant_uuid = _coerce_uuid(tenant_id)
        now = datetime.now(UTC)
        since = now - timedelta(hours=24)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                messages = (
                    await session.execute(
                        select(Conversation)
                        .where(
                            Conversation.tenant_id == tenant_uuid,
                            Conversation.role == "user",
                            Conversation.created_at >= since,
                        )
                        .order_by(Conversation.created_at.asc())
                    )
                ).scalars().all()
                pending_count = await session.scalar(
                    select(func.count())
                    .select_from(ApprovalRequest)
                    .where(
                        ApprovalRequest.tenant_id == tenant_uuid,
                        ApprovalRequest.status == ApprovalStatus.PENDING,
                    )
                )

                metrics = _message_metrics(messages)
                state = _state_from_metrics(metrics, int(pending_count or 0))
                briefing_depth = _briefing_depth(state)

                memory_content = (
                    f"Captain state reading at {now.isoformat()}. "
                    f"Energy={state['energy']}; focus={state['focus']}; stress={state['stress']}. "
                    f"Messages last 24h={metrics['message_count']}; average length={metrics['average_message_length']}; "
                    f"pending approvals={int(pending_count or 0)}; recommended briefing depth={briefing_depth}."
                )
                node, _ = await _upsert_node(
                    session,
                    tenant_uuid,
                    node_type="captain_state",
                    title=f"Captain state reading - {now.strftime('%Y-%m-%d %H:00 UTC')}",
                    content=memory_content,
                    source_table="captain_awareness",
                    source_id=f"captain_state:{now.strftime('%Y%m%d%H')}",
                    metadata={
                        "state": state,
                        "metrics": metrics,
                        "briefing_depth": briefing_depth,
                        "pending_approvals": int(pending_count or 0),
                    },
                )
                audit_payload = {
                    "state": state,
                    "metrics": metrics,
                    "briefing_depth": briefing_depth,
                    "memory_node_id": str(node.id),
                }
                session.add(
                    AuditLog(
                        tenant_id=tenant_uuid,
                        action="captain_state_reading_recorded",
                        entity_type="captain_awareness",
                        actor="CaptainAwarenessEngine",
                        details=audit_payload,
                    )
                )

        return {
            "captain": "Syed Abrar",
            "state": state,
            "briefing_depth": briefing_depth,
            "metrics": metrics,
            "pending_approvals": int(pending_count or 0),
            "memory_recorded": True,
            "read_at": now.isoformat(),
        }


class DecisionLoadManager:
    async def current_load(self, tenant_id) -> dict[str, Any]:
        tenant_uuid = _coerce_uuid(tenant_id)
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                decisions_today = await session.scalar(
                    select(func.count())
                    .select_from(ApprovalRequest)
                    .where(
                        ApprovalRequest.tenant_id == tenant_uuid,
                        ApprovalRequest.status != ApprovalStatus.PENDING,
                        or_(
                            ApprovalRequest.decided_at >= today_start,
                            ApprovalRequest.approved_at >= today_start,
                        ),
                    )
                )
                pending = (
                    await session.execute(
                        select(ApprovalRequest)
                        .where(
                            ApprovalRequest.tenant_id == tenant_uuid,
                            ApprovalRequest.status == ApprovalStatus.PENDING,
                        )
                        .order_by(ApprovalRequest.priority.desc(), ApprovalRequest.created_at.asc())
                    )
                ).scalars().all()

                prioritized = [_prioritize_item(item, now) for item in pending]
                prioritized.sort(key=lambda item: item["score"], reverse=True)
                for item in pending:
                    score = next(
                        (row["score"] for row in prioritized if row["approval_id"] == str(item.id)),
                        float(item.priority or 0),
                    )
                    item.priority = max(int(item.priority or 0), min(100, int(score)))

                queue_depth = len(pending)
                overloaded = queue_depth > 5 or int(decisions_today or 0) > 10
                telegram_notified = False
                if overloaded:
                    telegram_notified = await notify_telegram(
                        f"Captain - {queue_depth} items queued. Recommend batch review session."
                    )

                audit_payload = {
                    "queue_depth": queue_depth,
                    "decisions_today": int(decisions_today or 0),
                    "overloaded": overloaded,
                    "telegram_notified": telegram_notified,
                }
                session.add(
                    AuditLog(
                        tenant_id=tenant_uuid,
                        action="decision_load_reviewed",
                        entity_type="approval_requests",
                        actor="DecisionLoadManager",
                        details=audit_payload,
                    )
                )

        return {
            "queue_depth": queue_depth,
            "decisions_today": int(decisions_today or 0),
            "overloaded": overloaded,
            "telegram_notified": telegram_notified,
            "prioritized_queue": prioritized,
            "rule": "overloaded when queue_depth > 5 or decisions_today > 10",
            "checked_at": now.isoformat(),
        }


captain_awareness_engine = CaptainAwarenessEngine()
decision_load_manager = DecisionLoadManager()


def _message_metrics(messages: list[Conversation]) -> dict[str, Any]:
    lengths = [len((row.content or "").strip()) for row in messages]
    intervals = []
    previous = None
    for row in messages:
        created_at = _as_aware(row.created_at)
        if previous:
            intervals.append(max(0.0, (created_at - previous).total_seconds() / 60.0))
        previous = created_at
    active_hours = sorted({_as_aware(row.created_at).hour for row in messages})
    session_count = len({row.session_id for row in messages if row.session_id})
    urgent_terms = _urgent_term_count(" ".join(row.content or "" for row in messages))

    return {
        "message_count": len(messages),
        "average_message_length": round(mean(lengths), 1) if lengths else 0.0,
        "longest_message_length": max(lengths) if lengths else 0,
        "average_response_gap_minutes": round(mean(intervals), 1) if intervals else None,
        "active_hours_utc": active_hours,
        "session_count": session_count,
        "urgent_term_count": urgent_terms,
    }


def _state_from_metrics(metrics: dict[str, Any], pending_count: int) -> dict[str, str]:
    message_count = int(metrics["message_count"])
    avg_len = float(metrics["average_message_length"])
    sessions = int(metrics["session_count"])
    urgent_terms = int(metrics["urgent_term_count"])

    if message_count >= 8 or avg_len >= 260:
        energy = "high"
    elif message_count >= 2 or avg_len >= 80:
        energy = "medium"
    else:
        energy = "low"

    focus = "scattered" if sessions >= 4 or (message_count >= 5 and avg_len < 90) else "deep"
    stress = "elevated" if pending_count > 5 or urgent_terms >= 3 or avg_len >= 520 else "calm"
    return {"energy": energy, "focus": focus, "stress": stress}


def _briefing_depth(state: dict[str, str]) -> str:
    if state["stress"] == "elevated" or state["energy"] == "low":
        return "top_3_bullets"
    if state["energy"] == "high":
        return "full"
    return "standard"


def _prioritize_item(item: ApprovalRequest, now: datetime) -> dict[str, Any]:
    revenue_impact = _revenue_impact(item)
    risk_level = (item.risk_level or "MEDIUM").upper()
    urgency = {"CRITICAL": 5.0, "HIGH": 4.0, "MEDIUM": 2.5, "LOW": 1.5}.get(risk_level, 2.5)
    age_hours = max(0.0, (now - _as_aware(item.created_at)).total_seconds() / 3600.0)
    urgency += min(3.0, age_hours / 24.0)
    score = round((revenue_impact / 1000.0) * urgency + float(item.priority or 0), 2)
    return {
        "approval_id": str(item.id),
        "title": item.title or item.action_type or "Approval item",
        "risk_level": risk_level.lower(),
        "revenue_impact": revenue_impact,
        "urgency": round(urgency, 2),
        "score": score,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _revenue_impact(item: ApprovalRequest) -> float:
    candidates: list[str] = []
    if item.estimated_cost:
        candidates.append(item.estimated_cost)
    if item.title:
        candidates.append(item.title)
    if item.summary:
        candidates.append(item.summary)
    payload = item.payload or {}
    for key in ("revenue_impact", "estimated_cost", "pipeline_value", "impact"):
        value = payload.get(key)
        if value is not None:
            candidates.append(str(value))
    return max((_parse_money(text) for text in candidates), default=0.0)


def _parse_money(text: str) -> float:
    best = 0.0
    for match in re.finditer(r"[$£€]\s*([0-9]+(?:\.[0-9]+)?)([kKmM]?)|([0-9]+(?:\.[0-9]+)?)\s*([kKmM])", text or ""):
        number = match.group(1) or match.group(3)
        suffix = match.group(2) or match.group(4) or ""
        value = float(number)
        if suffix.lower() == "k":
            value *= 1000
        elif suffix.lower() == "m":
            value *= 1_000_000
        best = max(best, value)
    return best


def _urgent_term_count(text: str) -> int:
    lower = text.lower()
    terms = ("urgent", "blocked", "fix", "not working", "failed", "revenue", "client", "live")
    return sum(lower.count(term) for term in terms)


def _as_aware(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _coerce_uuid(value) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
