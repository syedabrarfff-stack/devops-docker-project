from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from app.core.config import settings
from app.models.approval import AuditLog
from app.models.civilization import CivilizationLedger
from app.services.notifications.telegram import notify_telegram

FOUNDING_EVENTS = [
    {
        "event_type": "company_foundation",
        "title": "Aliyar Solutions operating system established",
        "description": "JARVIS became the operating intelligence spine for Aliyar Solutions, with revenue generation as the first mission.",
        "impact": "strategic",
        "actors": ["Captain Syed Abrar", "JARVIS"],
        "milestone": True,
    },
    {
        "event_type": "architecture_layer_deployed",
        "title": "Stable vNEXT spine deployed",
        "description": "FastAPI, PostgreSQL, Redis, Docker, monitoring, memory graph, pilot readiness, demos, and outreach scheduling were made live.",
        "impact": "infrastructure",
        "actors": ["JARVIS", "Codex"],
        "milestone": True,
    },
    {
        "event_type": "architecture_layer_deployed",
        "title": "Competitor intelligence and Captain cognition deployed",
        "description": "Competitor profiles, Aliyar win reasons, LinkedIn outreach preparation, Captain awareness, and decision load management became live.",
        "impact": "intelligence",
        "actors": ["JARVIS", "Codex"],
        "milestone": True,
    },
]


class CivilizationLedgerService:
    async def append_event(
        self,
        session,
        tenant_id: uuid.UUID,
        *,
        event_type: str,
        title: str,
        description: str,
        impact: str = "operational",
        actors: list[str] | None = None,
        data_snapshot: dict[str, Any] | None = None,
        milestone: bool = False,
        dedupe: bool = False,
    ) -> CivilizationLedger:
        if dedupe:
            existing = await session.scalar(
                select(CivilizationLedger)
                .where(
                    CivilizationLedger.tenant_id == tenant_id,
                    CivilizationLedger.event_type == event_type,
                    CivilizationLedger.title == title,
                )
                .limit(1)
            )
            if existing:
                return existing

        previous = await session.scalar(
            select(CivilizationLedger)
            .where(CivilizationLedger.tenant_id == tenant_id)
            .order_by(CivilizationLedger.created_at.desc())
            .limit(1)
        )
        previous_hash = previous.record_hash if previous else None
        event_timestamp = datetime.now(UTC)
        payload = {
            "tenant_id": str(tenant_id),
            "event_type": event_type,
            "title": title,
            "description": description,
            "impact": impact,
            "actors": actors or ["JARVIS"],
            "data_snapshot": data_snapshot or {},
            "event_timestamp": event_timestamp.isoformat(),
            "previous_hash": previous_hash,
        }
        record_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
        event = CivilizationLedger(
            tenant_id=tenant_id,
            event_type=event_type,
            title=title,
            description=description,
            impact=impact,
            actors=actors or ["JARVIS"],
            data_snapshot=data_snapshot or {},
            event_timestamp=event_timestamp,
            previous_hash=previous_hash,
            record_hash=record_hash,
            milestone=milestone,
        )
        session.add(event)
        await session.flush()
        session.add(
            AuditLog(
                tenant_id=tenant_id,
                action="civilization_ledger_event_appended",
                entity_type="civilization_ledger",
                entity_id=event.id,
                actor="CivilizationLedger",
                details={"event_type": event_type, "title": title, "record_hash": record_hash},
            )
        )
        return event

    async def initialize(self, tenant_id) -> dict[str, Any]:
        from app.core.database import AsyncSessionLocal, set_tenant_context

        tenant_uuid = _tenant_uuid(tenant_id)
        created = 0
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                for item in FOUNDING_EVENTS:
                    before = await session.scalar(
                        select(func.count())
                        .select_from(CivilizationLedger)
                        .where(
                            CivilizationLedger.tenant_id == tenant_uuid,
                            CivilizationLedger.event_type == item["event_type"],
                            CivilizationLedger.title == item["title"],
                        )
                    )
                    await self.append_event(
                        session,
                        tenant_uuid,
                        data_snapshot={"source": "layer_43_initialization"},
                        dedupe=True,
                        **item,
                    )
                    created += 0 if before else 1
                total = await session.scalar(
                    select(func.count()).select_from(CivilizationLedger).where(CivilizationLedger.tenant_id == tenant_uuid)
                )
        return {"founding_events_created": created, "total_events": int(total or 0), "ledger_ready": True}

    async def list_events(self, tenant_id, milestones_only: bool = False, limit: int = 200) -> dict[str, Any]:
        from app.core.database import AsyncSessionLocal, set_tenant_context

        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                query = select(CivilizationLedger).where(CivilizationLedger.tenant_id == tenant_uuid)
                if milestones_only:
                    query = query.where(CivilizationLedger.milestone.is_(True))
                rows = (
                    await session.execute(
                        query.order_by(CivilizationLedger.created_at.asc()).limit(max(1, min(limit, 1000)))
                    )
                ).scalars().all()
                full_rows = (
                    await session.execute(
                        select(CivilizationLedger)
                        .where(CivilizationLedger.tenant_id == tenant_uuid)
                        .order_by(CivilizationLedger.created_at.asc())
                    )
                ).scalars().all()
        return {
            "count": len(rows),
            "chain_valid": _chain_valid(full_rows),
            "events": [_serialize(row) for row in rows],
        }

    async def maybe_generate_chronicle(self, session, tenant_id: uuid.UUID) -> str | None:
        count = await session.scalar(
            select(func.count()).select_from(CivilizationLedger).where(CivilizationLedger.tenant_id == tenant_id)
        )
        if int(count or 0) < 100:
            return None
        existing = await session.scalar(
            select(CivilizationLedger)
            .where(
                CivilizationLedger.tenant_id == tenant_id,
                CivilizationLedger.event_type == "company_chronicle_generated",
            )
            .limit(1)
        )
        if existing:
            return (existing.data_snapshot or {}).get("pdf_path")

        rows = (
            await session.execute(
                select(CivilizationLedger)
                .where(CivilizationLedger.tenant_id == tenant_id)
                .order_by(CivilizationLedger.created_at.asc())
            )
        ).scalars().all()
        pdf_path = await _build_chronicle_pdf(rows)
        await self.append_event(
            session,
            tenant_id,
            event_type="company_chronicle_generated",
            title="Company Chronicle generated",
            description="The civilization ledger crossed 100 events and generated the first Aliyar Solutions Company Chronicle PDF.",
            impact="strategic",
            actors=["JARVIS"],
            data_snapshot={"pdf_path": pdf_path, "event_count": len(rows)},
            milestone=True,
        )
        await notify_telegram(f"Company Chronicle ready - {pdf_path}")
        return pdf_path


civilization_ledger = CivilizationLedgerService()


async def _build_chronicle_pdf(events: list[CivilizationLedger]) -> str:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    output_dir = Path(os.getenv("JARVIS_CHRONICLE_DIR", "/data/chronicles"))
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"aliyar_company_chronicle_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.pdf"
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Aliyar Solutions Company Chronicle", styles["Title"]),
        Paragraph("Immutable operating history generated by JARVIS.", styles["BodyText"]),
        Spacer(1, 18),
    ]
    for event in events:
        timestamp = event.event_timestamp.isoformat() if event.event_timestamp else ""
        story.append(Paragraph(f"{timestamp} - {event.title}", styles["Heading3"]))
        story.append(Paragraph(event.description, styles["BodyText"]))
        story.append(Paragraph(f"Impact: {event.impact} | Hash: {event.record_hash[:12]}", styles["BodyText"]))
        story.append(Spacer(1, 10))
    SimpleDocTemplate(str(pdf_path), pagesize=letter).build(story)
    return str(pdf_path)


def _chain_valid(rows: list[CivilizationLedger]) -> bool:
    previous_hash = None
    for row in rows:
        if row.previous_hash != previous_hash:
            return False
        previous_hash = row.record_hash
    return True


def _serialize(row: CivilizationLedger) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "event_type": row.event_type,
        "title": row.title,
        "description": row.description,
        "impact": row.impact,
        "milestone": row.milestone,
        "actors": row.actors or [],
        "data_snapshot": row.data_snapshot or {},
        "timestamp": row.event_timestamp.isoformat() if row.event_timestamp else None,
        "hash": row.record_hash,
        "previous_hash": row.previous_hash,
    }


def _tenant_uuid(value) -> uuid.UUID:
    raw = value or settings.JARVIS_DEFAULT_TENANT_ID or "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))
