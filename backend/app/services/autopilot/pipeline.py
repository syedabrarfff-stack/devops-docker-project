"""
JARVIS AUTOPILOT — Autonomous Outreach Pipeline.

Each cycle:
  1. Selects top-scoring, un-contacted leads from the DB
  2. For each lead: auto-selects persona, composes email via GHOST (Claude Opus)
  3. Stores composed drafts in Redis (48h TTL) keyed by tenant
  4. Notifies Captain via Telegram

Captain then reviews, edits if needed, approves or rejects in the dashboard.
Approval triggers immediate send via the Aliyar Gmail/SES stack and updates
the lead's status and outreach_count.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.lead import Lead, LeadStatus
from app.services.ghost.writer import (
    auto_select_persona,
    get_persona,
    ghost_compose_once,
)

logger = logging.getLogger(__name__)

_REDIS_KEY = "autopilot:{tenant_id}:drafts"
_STATS_KEY = "autopilot:{tenant_id}:stats"
_FALLBACK: dict[str, list[dict]] = {}   # in-memory fallback when Redis is absent
_SYSTEM_TENANT = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def _resolve_tenant(tenant_id: str | None) -> str:
    """Resolve None or empty tenant_id to the configured default or system tenant."""
    if tenant_id:
        return str(tenant_id)
    tid = settings.JARVIS_DEFAULT_TENANT_ID
    return str(tid) if tid else _SYSTEM_TENANT


# ── Redis helpers ──────────────────────────────────────────────────────────────

async def _redis():
    if not settings.REDIS_URL:
        return None
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
        return r
    except Exception as exc:
        logger.warning("Autopilot: Redis connection failed — falling back to in-memory: %s", exc)
        return None


async def _load_drafts(tenant_id: str | None) -> list[dict]:
    key = _REDIS_KEY.format(tenant_id=_resolve_tenant(tenant_id))
    r = await _redis()
    if r:
        try:
            raw = await r.get(key)
            await r.aclose()
            return json.loads(raw) if raw else []
        except Exception as exc:
            logger.warning("Autopilot: failed to load drafts from Redis key %s: %s", key, exc)
    return _FALLBACK.get(key, [])


async def _save_drafts(tenant_id: str | None, drafts: list[dict]) -> None:
    key = _REDIS_KEY.format(tenant_id=_resolve_tenant(tenant_id))
    r = await _redis()
    if r:
        try:
            await r.set(key, json.dumps(drafts), ex=172_800)  # 48h TTL
            await r.aclose()
            return
        except Exception as exc:
            logger.warning("Autopilot: failed to save drafts to Redis key %s: %s", key, exc)
    _FALLBACK[key] = drafts


async def _load_stats(tenant_id: str) -> dict:
    key = _STATS_KEY.format(tenant_id=tenant_id)
    r = await _redis()
    if r:
        try:
            raw = await r.get(key)
            await r.aclose()
            return json.loads(raw) if raw else {}
        except Exception as exc:
            logger.warning("Autopilot: failed to load stats from Redis key %s: %s", key, exc)
    return _FALLBACK.get(key + ":stats", {})


async def _update_stats(tenant_id: str, patch: dict) -> None:
    stats = await _load_stats(tenant_id)
    stats.update(patch)
    key = _STATS_KEY.format(tenant_id=tenant_id)
    r = await _redis()
    if r:
        try:
            await r.set(key, json.dumps(stats), ex=172_800)
            await r.aclose()
            return
        except Exception as exc:
            logger.warning("Autopilot: failed to update stats in Redis key %s: %s", key, exc)
    _FALLBACK[key + ":stats"] = stats


# ── Lead selection ─────────────────────────────────────────────────────────────

async def _eligible_leads(
    db: AsyncSession,
    tenant_id: UUID | None,
    max_leads: int,
    min_score: float,
) -> list[dict]:
    from datetime import timedelta

    from app.models.outreach import OutreachLog

    # ART-08 (NEXUS Constitution): no lead may receive more than 3 autonomous
    # outreach emails in 7 days. Enforced here at lead selection, since the
    # NEXUS brain's evaluate_action() only ever sees one cycle-level decision
    # with no per-lead context to check this against.
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    over_cap_leads = (
        select(OutreachLog.lead_id)
        .where(OutreachLog.sent_at >= seven_days_ago, OutreachLog.lead_id.isnot(None))
        .group_by(OutreachLog.lead_id)
        .having(func.count() >= 3)
    )

    q = (
        select(Lead)
        .where(
            and_(
                Lead.outreach_eligible == True,
                Lead.status.in_([LeadStatus.NEW, LeadStatus.NURTURE]),
                Lead.score >= min_score,
                Lead.email.isnot(None),
                Lead.id.notin_(over_cap_leads),
            )
        )
        .order_by(Lead.score.desc())
        .limit(max_leads)
    )
    if tenant_id:
        q = q.where(Lead.tenant_id == tenant_id)

    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(r.id),
            "company_name": r.company_name,
            "contact_name": r.contact_name,
            "email": r.email,
            "industry": r.industry,
            "country": r.country,
            "pain_points": r.pain_points or [],
            "score": float(r.score or 0),
            "status": r.status.value if r.status else "NEW",
            "notes": r.notes or "",
            "assigned_persona": r.assigned_persona,
        }
        for r in rows
    ]


# ── Parse email text ───────────────────────────────────────────────────────────

def _parse_email(text: str) -> tuple[str, str]:
    lines = (text or "").strip().splitlines()
    subject, body_lines, in_body = "", [], False
    for line in lines:
        if not in_body and line.lower().startswith("subject:"):
            subject = line[8:].strip()
            in_body = True
        elif in_body:
            body_lines.append(line)
    body = "\n".join(body_lines).strip()
    if not subject and lines:
        subject = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
    return subject, body


# ── Core cycle ─────────────────────────────────────────────────────────────────

async def run_autopilot_cycle(
    tenant_id: UUID | None = None,
    max_leads: int = 10,
    min_score: float = 55.0,
    tone: str = "professional",
) -> dict:
    """
    Compose emails for top eligible leads and queue them for Captain approval.
    Returns a summary dict.
    """
    tid = str(tenant_id) if tenant_id else "system"

    async with AsyncSessionLocal() as db:
        leads = await _eligible_leads(db, tenant_id, max_leads, min_score)

    if not leads:
        logger.info("Autopilot: no eligible leads for tenant %s", tid)
        return {
            "status": "no_eligible_leads",
            "composed": 0,
            "skipped": 0,
            "tenant_id": tid,
            "timestamp": _now(),
        }

    composed, skipped = 0, 0
    new_drafts: list[dict] = []

    for lead in leads:
        try:
            persona_name = (
                lead.get("assigned_persona")
                or auto_select_persona(lead.get("industry"), lead.get("pain_points"))
            )
            persona = get_persona(persona_name) or get_persona("Darren Mitchell")

            full_text = await ghost_compose_once(
                lead=lead, persona=persona, tone=tone, email_num=1, total=1
            )
            subject, body = _parse_email(full_text)
            if not subject:
                subject = f"Quick thought for {lead.get('company_name') or 'your team'}"

            new_drafts.append({
                "id": str(uuid4()),
                "tenant_id": tid,
                "lead_id": lead["id"],
                "lead_company": lead.get("company_name") or "—",
                "lead_contact": lead.get("contact_name") or "",
                "lead_email": lead.get("email") or "",
                "lead_score": lead.get("score", 0),
                "lead_industry": lead.get("industry") or "",
                "lead_country": lead.get("country") or "",
                "lead_pain_points": lead.get("pain_points") or [],
                "persona_name": persona_name,
                "persona_role": persona.get("role", ""),
                "persona_email": persona.get("email", ""),
                "subject": subject,
                "body": body,
                "full_text": full_text,
                "tone": tone,
                "status": "pending",
                "created_at": _now(),
                "approved_at": None,
                "sent_at": None,
            })
            composed += 1

        except Exception as exc:
            logger.warning("Autopilot: failed composing for lead %s — %s", lead.get("id"), exc)
            skipped += 1

    # Merge with any existing pending drafts (don't overwrite un-actioned ones)
    existing = await _load_drafts(tid)
    existing_lead_ids = {d["lead_id"] for d in existing if d["status"] == "pending"}
    merged = existing + [d for d in new_drafts if d["lead_id"] not in existing_lead_ids]
    await _save_drafts(tid, merged)

    # Stats
    await _update_stats(tid, {
        "last_run": _now(),
        "last_composed": composed,
        "last_skipped": skipped,
    })

    # Notify Captain with inline approve/reject buttons
    truly_new = [d for d in new_drafts if d["lead_id"] not in existing_lead_ids]
    if truly_new:
        try:
            from app.services.notifications.telegram_bot import (
                notify_autopilot_draft_ready,
                notify_autopilot_drafts_pending,
            )
            if len(truly_new) <= 3:
                for draft in truly_new:
                    await notify_autopilot_draft_ready(draft)
            else:
                await notify_autopilot_drafts_pending(truly_new)
        except Exception:
            pass

    return {
        "status": "ok",
        "composed": composed,
        "skipped": skipped,
        "pending_total": len([d for d in merged if d["status"] == "pending"]),
        "tenant_id": tid,
        "timestamp": _now(),
    }


# ── Draft CRUD ─────────────────────────────────────────────────────────────────

async def get_pending_drafts(tenant_id: str | None) -> list[dict]:
    drafts = await _load_drafts(tenant_id)
    return [d for d in drafts if d["status"] == "pending"]


async def get_all_drafts(tenant_id: str) -> list[dict]:
    return await _load_drafts(tenant_id)


async def approve_draft(tenant_id: str, draft_id: str) -> dict:
    """Send the email and mark draft approved."""
    drafts = await _load_drafts(tenant_id)
    draft = next((d for d in drafts if d["id"] == draft_id), None)
    if not draft:
        raise ValueError(f"Draft {draft_id} not found")
    if draft["status"] != "pending":
        raise ValueError(f"Draft {draft_id} is already {draft['status']}")

    to_email = draft["lead_email"]
    if not to_email:
        raise ValueError("Lead has no email address")

    async with AsyncSessionLocal() as db:
        from app.services.outreach.gmail import send_client_email
        from app.services.outreach.compliance import outreach_compliance

        # AUTOPILOT is a fully autonomous/bulk-approval sender — it must clear the
        # same do-not-contact/daily-cap/pause gate as every other send path
        # (GHOST's manual send, the automated sequence engine). Load the lead row
        # up front so the gate can be checked before anything is sent.
        lead_uuid = _to_uuid(draft["lead_id"])
        row = None
        if lead_uuid:
            row = (await db.execute(select(Lead).where(Lead.id == lead_uuid))).scalar_one_or_none()

        if row is not None:
            tenant_uuid = row.tenant_id or _to_uuid(tenant_id)
            safety = await outreach_compliance.safety_gate(db, tenant_uuid, row, to_email)
            if not safety["allowed"]:
                raise RuntimeError(f"Blocked by outreach compliance: {safety.get('reason', 'not_allowed')}")

        body_text = outreach_compliance.append_footer(draft["body"], to_email)
        success, error, method = await send_client_email(
            db=db,
            to=to_email,
            subject=draft["subject"],
            body=body_text,
            to_name=draft.get("lead_contact") or "",
        )
        if not success:
            raise RuntimeError(f"Email send failed: {error}")

        # Update lead record
        if row is not None:
            row.outreach_count = (row.outreach_count or 0) + 1
            if row.status == LeadStatus.NEW:
                row.status = LeadStatus.CONTACTED
            row.last_contact = datetime.now(timezone.utc)
        await db.commit()

    draft["status"] = "sent"
    draft["approved_at"] = _now()
    draft["sent_at"] = _now()
    draft["send_method"] = method

    await _save_drafts(tenant_id, drafts)

    # Update stats
    stats = await _load_stats(tenant_id)
    stats["total_sent"] = stats.get("total_sent", 0) + 1
    await _update_stats(tenant_id, stats)

    # Real-time WebSocket push
    try:
        from app.api.v1.routes.ws import broadcast
        await broadcast("autopilot_draft_sent", {
            "draft_id": draft_id,
            "to": to_email,
            "method": method,
            "lead_company": draft.get("lead_company", ""),
        })
    except Exception:
        pass

    return {"sent": True, "to": to_email, "method": method}


async def reject_draft(tenant_id: str, draft_id: str, reason: str = "") -> None:
    drafts = await _load_drafts(tenant_id)
    draft = next((d for d in drafts if d["id"] == draft_id), None)
    if not draft:
        raise ValueError(f"Draft {draft_id} not found")
    draft["status"] = "rejected"
    draft["reject_reason"] = reason
    await _save_drafts(tenant_id, drafts)

    # Real-time WebSocket push
    try:
        from app.api.v1.routes.ws import broadcast
        await broadcast("autopilot_draft_rejected", {
            "draft_id": draft_id,
            "reason": reason,
            "lead_company": draft.get("lead_company", ""),
        })
    except Exception:
        pass


async def edit_draft(
    tenant_id: str,
    draft_id: str,
    subject: str | None = None,
    body: str | None = None,
) -> dict:
    drafts = await _load_drafts(tenant_id)
    draft = next((d for d in drafts if d["id"] == draft_id), None)
    if not draft:
        raise ValueError(f"Draft {draft_id} not found")
    if subject is not None:
        draft["subject"] = subject
    if body is not None:
        draft["body"] = body
    draft["edited"] = True
    await _save_drafts(tenant_id, drafts)
    return draft


async def approve_all_pending(tenant_id: str) -> dict:
    """Bulk-approve all pending drafts — send all emails."""
    drafts = await _load_drafts(tenant_id)
    pending = [d for d in drafts if d["status"] == "pending"]

    sent, failed = 0, 0
    for draft in pending:
        try:
            await approve_draft(tenant_id, draft["id"])
            sent += 1
        except Exception as exc:
            logger.error("Autopilot bulk approve failed for %s: %s", draft["id"], exc)
            draft["status"] = "error"
            draft["error"] = str(exc)
            failed += 1

    return {"sent": sent, "failed": failed, "total": len(pending)}


async def get_autopilot_status(tenant_id: str) -> dict:
    drafts = await _load_drafts(tenant_id)
    stats = await _load_stats(tenant_id)
    return {
        "pending": sum(1 for d in drafts if d["status"] == "pending"),
        "sent": sum(1 for d in drafts if d["status"] == "sent"),
        "rejected": sum(1 for d in drafts if d["status"] == "rejected"),
        "error": sum(1 for d in drafts if d["status"] == "error"),
        "total_drafts": len(drafts),
        "last_run": stats.get("last_run"),
        "last_composed": stats.get("last_composed", 0),
        "total_sent_all_time": stats.get("total_sent", 0),
    }


# ── Utilities ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_uuid(val: Any) -> UUID | None:
    try:
        return UUID(str(val))
    except (ValueError, TypeError):
        return None
