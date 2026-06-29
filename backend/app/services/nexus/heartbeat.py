"""
NEXUS HEARTBEAT — Continuous Operational Pulse.

Every hour, NEXUS pulse runs:
  1. Reads pipeline state (leads, signals, pending drafts)
  2. Checks all subsystem health
  3. Stores pulse snapshot in Redis
  4. Triggers BRAIN think cycle if actionable signals detected
  5. Queues decisions for AUTOPILOT execution if within Constitution
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_PULSE_KEY = "nexus:pulse:latest"
_PULSE_HISTORY_KEY = "nexus:pulse:history"
_DECISION_LOG_KEY = "nexus:decisions"
_HEAL_LOG_KEY = "nexus:heal:log"

_FALLBACK_PULSES: list[dict] = []
_FALLBACK_DECISIONS: list[dict] = []
_FALLBACK_HEAL_LOG: list[dict] = []


async def _redis():
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings
        url = settings.REDIS_URL or os.environ.get("REDIS_URL", "redis://localhost:6379")
        return aioredis.from_url(url, decode_responses=True)
    except Exception:
        return None


async def store_pulse(pulse: dict) -> None:
    r = await _redis()
    payload = json.dumps(pulse, default=str)
    if r:
        try:
            await r.set(_PULSE_KEY, payload, ex=7200)
            await r.lpush(_PULSE_HISTORY_KEY, payload)
            await r.ltrim(_PULSE_HISTORY_KEY, 0, 167)  # keep 7 days of hourly pulses
        except Exception as exc:
            logger.warning("Redis pulse store failed: %s", exc)
            _FALLBACK_PULSES.append(pulse)
        finally:
            await r.aclose()
    else:
        _FALLBACK_PULSES.append(pulse)
        if len(_FALLBACK_PULSES) > 168:
            _FALLBACK_PULSES.pop(0)


async def get_latest_pulse() -> dict | None:
    r = await _redis()
    if r:
        try:
            raw = await r.get(_PULSE_KEY)
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.warning("Redis get_latest_pulse failed: %s", exc)
        finally:
            await r.aclose()
    return _FALLBACK_PULSES[-1] if _FALLBACK_PULSES else None


async def get_pulse_history(limit: int = 24) -> list[dict]:
    r = await _redis()
    if r:
        try:
            items = await r.lrange(_PULSE_HISTORY_KEY, 0, limit - 1)
            return [json.loads(i) for i in items]
        except Exception as exc:
            logger.warning("Redis get_pulse_history failed: %s", exc)
        finally:
            await r.aclose()
    return _FALLBACK_PULSES[-limit:]


async def log_decision(decision: dict) -> None:
    r = await _redis()
    record = {**decision, "logged_at": datetime.now(timezone.utc).isoformat()}
    payload = json.dumps(record, default=str)
    if r:
        try:
            await r.lpush(_DECISION_LOG_KEY, payload)
            await r.ltrim(_DECISION_LOG_KEY, 0, 499)
        except Exception as exc:
            logger.warning("Redis log_decision failed: %s", exc)
            _FALLBACK_DECISIONS.insert(0, record)
        finally:
            await r.aclose()
    else:
        _FALLBACK_DECISIONS.insert(0, record)
        if len(_FALLBACK_DECISIONS) > 500:
            _FALLBACK_DECISIONS.pop()


async def get_decisions(limit: int = 20) -> list[dict]:
    r = await _redis()
    if r:
        try:
            items = await r.lrange(_DECISION_LOG_KEY, 0, limit - 1)
            return [json.loads(i) for i in items]
        except Exception as exc:
            logger.warning("Redis get_decisions failed: %s", exc)
        finally:
            await r.aclose()
    return _FALLBACK_DECISIONS[:limit]


async def log_heal_event(event: dict) -> None:
    r = await _redis()
    record = {**event, "logged_at": datetime.now(timezone.utc).isoformat()}
    payload = json.dumps(record, default=str)
    if r:
        try:
            await r.lpush(_HEAL_LOG_KEY, payload)
            await r.ltrim(_HEAL_LOG_KEY, 0, 99)
        except Exception as exc:
            logger.warning("Redis log_heal_event failed: %s", exc)
            _FALLBACK_HEAL_LOG.insert(0, record)
        finally:
            await r.aclose()
    else:
        _FALLBACK_HEAL_LOG.insert(0, record)
        if len(_FALLBACK_HEAL_LOG) > 100:
            _FALLBACK_HEAL_LOG.pop()


async def get_heal_log(limit: int = 20) -> list[dict]:
    r = await _redis()
    if r:
        try:
            items = await r.lrange(_HEAL_LOG_KEY, 0, limit - 1)
            return [json.loads(i) for i in items]
        except Exception as exc:
            logger.warning("Redis get_heal_log failed: %s", exc)
        finally:
            await r.aclose()
    return _FALLBACK_HEAL_LOG[:limit]


async def run_pulse(db: Any) -> dict:
    """
    Execute one heartbeat pulse. Returns the pulse snapshot dict.
    This is called by the scheduler every hour and on demand.
    """
    from sqlalchemy import func, select
    from app.models.lead import Lead, LeadStatus

    ts = datetime.now(timezone.utc).isoformat()
    pulse: dict[str, Any] = {"timestamp": ts, "subsystems": {}}

    # ── Pipeline metrics ──────────────────────────────────────────────────────
    try:
        import uuid as _uuid
        from app.core.config import settings as _cfg
        _tid = None
        if getattr(_cfg, "JARVIS_DEFAULT_TENANT_ID", None):
            try:
                _tid = _uuid.UUID(str(_cfg.JARVIS_DEFAULT_TENANT_ID))
            except (ValueError, AttributeError):
                pass
        _tf = [Lead.tenant_id == _tid] if _tid else []
        total = await db.scalar(select(func.count()).select_from(Lead).where(*_tf)) or 0
        hot = await db.scalar(select(func.count()).select_from(Lead).where(*_tf, Lead.score >= 75)) or 0
        warm = await db.scalar(select(func.count()).select_from(Lead).where(*_tf, Lead.score.between(45, 74))) or 0
        eligible = await db.scalar(select(func.count()).select_from(Lead).where(*_tf, Lead.outreach_eligible == True)) or 0
        pulse["pipeline"] = {
            "total_leads": total, "hot_leads": hot, "warm_leads": warm,
            "eligible_for_outreach": eligible, "cool_cold": max(0, total - hot - warm),
        }
        pulse["subsystems"]["pipeline"] = "healthy"
    except Exception as exc:
        pulse["pipeline"] = {}
        pulse["subsystems"]["pipeline"] = f"error: {exc}"

    # ── AUTOPILOT pending drafts ──────────────────────────────────────────────
    try:
        from app.services.autopilot.pipeline import get_pending_drafts
        pending = await get_pending_drafts(None)
        pulse["autopilot_pending"] = len(pending)
        pulse["subsystems"]["autopilot"] = "healthy"
    except Exception as exc:
        pulse["autopilot_pending"] = 0
        pulse["subsystems"]["autopilot"] = f"error: {exc}"

    # ── AI provider health ────────────────────────────────────────────────────
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    pulse["subsystems"]["ai_provider"] = "configured" if anthropic_key else "missing_key"

    # ── Redis health ──────────────────────────────────────────────────────────
    r = await _redis()
    if r:
        try:
            await r.ping()
            pulse["subsystems"]["redis"] = "healthy"
        except Exception as exc:
            pulse["subsystems"]["redis"] = f"error: {exc}"
    else:
        pulse["subsystems"]["redis"] = "unavailable"

    # ── Actionable signals ────────────────────────────────────────────────────
    pipeline = pulse.get("pipeline", {})
    hot_count = pipeline.get("hot_leads", 0)
    eligible_count = pipeline.get("eligible_for_outreach", 0)
    pending_count = pulse.get("autopilot_pending", 0)

    pulse["actionable"] = hot_count > 0 and eligible_count > 0
    pulse["action_signal"] = (
        "OUTREACH_READY" if (hot_count > 0 and eligible_count > 0 and pending_count == 0)
        else "DRAFTS_PENDING" if pending_count > 0
        else "MONITOR"
    )

    # Convenience booleans for quick checks in notification handlers
    pulse["ai_available"] = pulse["subsystems"].get("ai_provider") == "configured"
    pulse["redis_ok"] = pulse["subsystems"].get("redis") == "healthy"

    await store_pulse(pulse)
    return pulse
