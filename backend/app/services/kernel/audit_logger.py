"""K1-8: JARVIS Audit Logger — append-only, queryable.

Every autonomous action MUST produce an audit record before execution.
This is JARVIS's accountability layer — every decision is explainable.

The AuditLog table is append-only by convention (no UPDATE or DELETE
operations are ever issued by this service). The database row itself can
be deleted by a human DBA with explicit written Captain approval only.

Usage:
    logger = AuditLogger(db_session)
    record_id = await logger.write(
        action_type="policy.approved",
        actor="health_aggregator",
        resource_id=some_uuid,
        details={"operation": "db.add_column", "table": "leads"},
        outcome="APPROVED",
    )
    records = await logger.query(actor="health_aggregator", limit=50)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kernel import AuditLog

log = logging.getLogger(__name__)


class AuditLogger:
    """Write and query the immutable audit log.

    Every autonomous action record includes:
      action_type — what was attempted / happened
      actor       — which engine or service took the action
      resource_id — which entity was affected (nullable)
      details     — JSONB bag of structured context
      outcome     — APPROVED / BLOCKED / PENDING_CAPTAIN_APPROVAL /
                    COMPLETED / FAILED / VERIFIED / REPORTED_TO_CAPTAIN
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def write(
        self,
        action_type: str,
        actor: str,
        outcome: str,
        resource_id: Optional[uuid.UUID] = None,
        details: Optional[dict] = None,
    ) -> uuid.UUID:
        """Append one audit record. Returns the new record's UUID."""
        record = AuditLog(
            action_type=action_type,
            actor=actor,
            resource_id=resource_id,
            details=details or {},
            outcome=outcome,
        )
        self._session.add(record)
        await self._session.flush()

        log.debug(
            "AuditLogger: %s | actor=%s | outcome=%s | id=%s",
            action_type,
            actor,
            outcome,
            record.id,
        )
        return record.id

    async def query(
        self,
        actor: Optional[str] = None,
        action_type: Optional[str] = None,
        outcome: Optional[str] = None,
        resource_id: Optional[uuid.UUID] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Query the audit log with optional filters.

        All filters are AND-combined.
        """
        q = select(AuditLog).order_by(AuditLog.created_at.desc())

        if actor is not None:
            q = q.where(AuditLog.actor == actor)
        if action_type is not None:
            q = q.where(AuditLog.action_type == action_type)
        if outcome is not None:
            q = q.where(AuditLog.outcome == outcome)
        if resource_id is not None:
            q = q.where(AuditLog.resource_id == resource_id)
        if since is not None:
            q = q.where(AuditLog.created_at >= since)

        q = q.limit(limit).offset(offset)
        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def count(
        self,
        actor: Optional[str] = None,
        action_type: Optional[str] = None,
        outcome: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """Return total count matching the given filters."""
        from sqlalchemy import func
        q = select(func.count(AuditLog.id))
        if actor:
            q = q.where(AuditLog.actor == actor)
        if action_type:
            q = q.where(AuditLog.action_type == action_type)
        if outcome:
            q = q.where(AuditLog.outcome == outcome)
        if since:
            q = q.where(AuditLog.created_at >= since)
        result = await self._session.execute(q)
        return result.scalar_one() or 0

    async def get_by_id(self, record_id: uuid.UUID) -> Optional[AuditLog]:
        """Fetch a single audit record by ID."""
        result = await self._session.execute(
            select(AuditLog).where(AuditLog.id == record_id)
        )
        return result.scalar_one_or_none()

    async def recent(self, limit: int = 20) -> list[AuditLog]:
        """Return the N most recent audit records (for Captain dashboard)."""
        result = await self._session.execute(
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
