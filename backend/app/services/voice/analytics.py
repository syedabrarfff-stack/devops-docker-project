"""V6-5: Voice Analytics + Scheduler Job.

Tracks all voice interactions (inbound WhatsApp voice, outbound voice notes,
call recordings, TTS briefings) and computes daily metrics.

Scheduler job: voice_analytics_daily at 04:30 UTC.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, date, timedelta
from typing import Any

logger = logging.getLogger(__name__)

SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


async def compute_voice_metrics(target_date: date | None = None) -> dict[str, Any]:
    """
    Compute voice analytics for the given date (defaults to yesterday).
    Reads from memory table entries with 'voice_interaction' and 'call_summary' prefixes.
    """
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import text as sqla_text

    report_date = target_date or (datetime.now(UTC).date() - timedelta(days=1))
    date_str = report_date.isoformat()

    try:
        async with AsyncSessionLocal() as session:
            # Count inbound voice transcriptions
            res = await session.execute(sqla_text(
                "SELECT COUNT(*) FROM memory WHERE tenant_id=:tid "
                "AND key LIKE 'voice_interaction.%' AND key LIKE :date_pat"
            ), {"tid": SYSTEM_TENANT_ID, "date_pat": f"%.{date_str}"})
            inbound_count = res.scalar_one()

            # Count call summaries
            res = await session.execute(sqla_text(
                "SELECT COUNT(*) FROM memory WHERE tenant_id=:tid "
                "AND key LIKE 'call_summary.%' AND key LIKE :date_pat"
            ), {"tid": SYSTEM_TENANT_ID, "date_pat": f"%.{date_str}"})
            call_count = res.scalar_one()

            # Count positive call outcomes
            res = await session.execute(sqla_text(
                "SELECT COUNT(*) FROM memory WHERE tenant_id=:tid "
                "AND key LIKE 'call_summary.%' AND key LIKE :date_pat "
                "AND value ILIKE '%interested%'"
            ), {"tid": SYSTEM_TENANT_ID, "date_pat": f"%.{date_str}"})
            positive_calls = res.scalar_one()

    except Exception as exc:
        logger.warning("[VoiceAnalytics] DB query failed: %s", exc)
        inbound_count = call_count = positive_calls = 0

    conversion_rate = (positive_calls / max(call_count, 1)) * 100

    return {
        "date": date_str,
        "inbound_voice_messages": inbound_count,
        "call_recordings_processed": call_count,
        "positive_call_outcomes": positive_calls,
        "call_conversion_rate_pct": round(conversion_rate, 1),
        "computed_at": datetime.now(UTC).isoformat(),
    }


async def run_voice_analytics_job() -> dict[str, Any]:
    """
    Daily job entry point. Computes metrics and stores to memory.
    Also logs summary to Captain via Slack if there were any interactions.
    """
    metrics = await compute_voice_metrics()

    # Persist metrics to memory
    try:
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import text as sqla_text

        async with AsyncSessionLocal() as session:
            await session.execute(sqla_text(
                "INSERT INTO memory (tenant_id, layer, key, value, confidence, version) "
                "VALUES (:tid, 'operational', :key, :val, 0.95, 1) "
                "ON CONFLICT (tenant_id, key) DO UPDATE SET "
                "value=EXCLUDED.value, updated_at=NOW()"
            ), {
                "tid": SYSTEM_TENANT_ID,
                "key": f"voice_analytics.daily.{metrics['date']}",
                "val": str(metrics),
            })
            await session.commit()
    except Exception as exc:
        logger.warning("[VoiceAnalytics] Persist failed: %s", exc)

    # Alert Captain if there was voice activity
    total = metrics["inbound_voice_messages"] + metrics["call_recordings_processed"]
    if total > 0:
        try:
            from app.services.notifications.slack import notify_slack
            await notify_slack(
                f"🎙️ *Voice Analytics ({metrics['date']})*\n"
                f"• Inbound voice messages: {metrics['inbound_voice_messages']}\n"
                f"• Call recordings processed: {metrics['call_recordings_processed']}\n"
                f"• Positive outcomes: {metrics['positive_call_outcomes']} "
                f"({metrics['call_conversion_rate_pct']}%)"
            )
        except Exception as exc:
            logger.debug("[VoiceAnalytics] Slack notify failed: %s", exc)

    logger.info("[VoiceAnalytics] Daily metrics: %s", metrics)
    return metrics


# Scheduler registration: see app/services/scheduler/scheduler.py's
# `voice_analytics_daily()` (registered in _production_job_specs(), runs
# 04:30 UTC daily). That is the only registration path — do not re-add a
# registrar here (Task #23: one scheduler, one job registry). This module's
# previous `register_voice_analytics_job()` was dead on arrival — it
# imported a `scheduler` attribute that has never existed on engine.py, so
# this job never ran in production regardless of the engine.py/scheduler.py
# split.
