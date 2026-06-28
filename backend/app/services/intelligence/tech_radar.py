from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.core.tenant_context import get_current_tenant_id
from app.models.approval import AuditLog
from app.models.intelligence import TechRadarEntry
from app.models.tenant import Tenant
from app.services.ai.base_provider import Message, TaskType
from app.services.ai.router import ai_router

logger = logging.getLogger(__name__)

CATEGORIES = ("AI/ML", "Cloud", "Security", "DevOps", "Data", "Frontend", "Backend")
RINGS = ("ADOPT", "TRIAL", "ASSESS", "HOLD")

TECH_RADAR_PROMPT = """You are the Aliyar Solutions Intelligence Division.

Scan the current technology landscape for emerging technologies that matter to a small-to-mid-market AI, cloud,
DevOps, data, frontend, backend, and security services company.

Return ONLY a valid JSON array. No markdown. No code fences.

Each item must contain:
- name: technology, platform, framework, or practice
- category: one of AI/ML, Cloud, Security, DevOps, Data, Frontend, Backend
- ring: one of ADOPT, TRIAL, ASSESS, HOLD
- summary: one sentence explaining what it is
- recommendation: one or two concrete actions Aliyar Solutions should take
- why_it_matters: revenue, delivery, security, or operational reason
- evidence_refs: array of short evidence labels or public reference names
- confidence_score: number from 0 to 1
- risk_score: number from 0 to 1

Focus on technologies that can help Aliyar Solutions win clients, deliver faster, reduce operational risk,
or improve margins in the next 90 days. Generate 7 to 14 entries."""


class TechRadarEngine:
    async def scan_week(self, tenant_id) -> list[TechRadarEntry]:
        tenant_uuid = _coerce_tenant_id(tenant_id)
        response, _ = await asyncio.wait_for(
            ai_router.chat(
                [Message(role="user", content=TECH_RADAR_PROMPT)],
                task_type=TaskType.RESEARCH,
                force_provider="google",
                force_model="gemini-pro",
                system_prompt="You are a senior technology radar analyst. Return only valid JSON arrays.",
                max_tokens=4500,
            ),
            timeout=120.0,
        )
        if response.error:
            logger.warning("Tech radar AI call failed: %s", response.error)
            return []

        entries_data = _parse_json_array(response.content or "")
        if not entries_data:
            logger.warning("Tech radar scan returned no parseable entries")
            return []

        entries: list[TechRadarEntry] = []
        async with AsyncSessionLocal() as db:
            await _apply_tenant_context(db, tenant_uuid)
            for item in entries_data:
                normalized = _normalize_radar_item(item)
                if not normalized["name"]:
                    continue
                entry = TechRadarEntry(
                    tenant_id=tenant_uuid,
                    name=normalized["name"],
                    category=normalized["category"],
                    status=normalized["ring"],
                    summary=normalized["summary"],
                    recommendation=normalized["recommendation"],
                    why_it_matters=normalized["why_it_matters"],
                )
                db.add(entry)
                entries.append(entry)

            db.add(
                AuditLog(
                    tenant_id=tenant_uuid,
                    action="tech_radar_scan",
                    entity_type="tech_radar",
                    actor="tech_radar_engine",
                    details={
                        "entries_created": len(entries),
                        "categories": CATEGORIES,
                        "rings": RINGS,
                    },
                )
            )
            await db.commit()

        return entries


async def scan_technologies(db=None) -> int:
    tenant_id = await _default_tenant_id(db)
    if not tenant_id:
        logger.info("Tech radar scan skipped: no tenant configured")
        return 0
    entries = await TechRadarEngine().scan_week(tenant_id)
    return len(entries)


async def get_radar(db) -> dict:
    tenant_id = get_current_tenant_id() or settings.JARVIS_DEFAULT_TENANT_ID
    if not tenant_id:
        logger.warning("Tech radar get_radar: no tenant resolved, returning empty radar")
        return {"categories": [], "entries": {}, "total": 0}
    query = (
        select(TechRadarEntry)
        .where(TechRadarEntry.tenant_id == _coerce_tenant_id(tenant_id))
        .order_by(TechRadarEntry.category, TechRadarEntry.status, TechRadarEntry.created_at.desc())
    )

    result = await db.execute(query)
    entries = result.scalars().all()

    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        ring = (entry.status or "ASSESS").upper()
        grouped.setdefault(entry.category, []).append(
            {
                "id": entry.id,
                "name": entry.name,
                "ring": ring,
                "status": ring.lower(),
                "summary": entry.summary,
                "recommendation": entry.recommendation,
                "why_it_matters": entry.why_it_matters,
                "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
            }
        )

    return {
        "tenant_id": str(tenant_id) if tenant_id else None,
        "categories": grouped,
        "total": len(entries),
        "by_status": {
            ring.lower(): sum(1 for entry in entries if (entry.status or "").upper() == ring)
            for ring in RINGS
        },
    }


async def _default_tenant_id(db=None) -> str | None:
    if get_current_tenant_id():
        return get_current_tenant_id()
    if settings.JARVIS_DEFAULT_TENANT_ID:
        return settings.JARVIS_DEFAULT_TENANT_ID
    if db is not None:
        tenant = await db.scalar(select(Tenant).where(Tenant.is_active.is_(True)).order_by(Tenant.created_at).limit(1))
        return str(tenant.id) if tenant else None
    async with AsyncSessionLocal() as session:
        tenant = await session.scalar(select(Tenant).where(Tenant.is_active.is_(True)).order_by(Tenant.created_at).limit(1))
        return str(tenant.id) if tenant else None


async def _apply_tenant_context(db, tenant_id: uuid.UUID) -> None:
    if settings.DATABASE_URL.startswith("sqlite"):
        return
    await set_tenant_context(db, str(tenant_id))


def _coerce_tenant_id(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _parse_json_array(raw: str) -> list[dict[str, Any]]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return []
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return []
    return data if isinstance(data, list) else []


def _normalize_radar_item(item: dict[str, Any]) -> dict[str, Any]:
    category = str(item.get("category") or "AI/ML").strip()
    if category not in CATEGORIES:
        category = "AI/ML"

    ring = str(item.get("ring") or item.get("status") or "ASSESS").strip().upper()
    if ring not in RINGS:
        ring = "ASSESS"

    return {
        "name": str(item.get("name") or "").strip()[:200],
        "category": category,
        "ring": ring,
        "summary": str(item.get("summary") or "").strip(),
        "recommendation": str(item.get("recommendation") or "").strip(),
        "why_it_matters": str(item.get("why_it_matters") or "").strip(),
    }
