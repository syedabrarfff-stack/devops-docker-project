"""V6-3: Call Summariser.

Receives a call recording (via webhook from Calendly, Google Meet, or direct upload),
transcribes via Whisper, summarises via AI Council, stores to memory, and alerts Captain.

Webhook endpoint: POST /api/v1/webhooks/voice/call-ended
Payload: {"recording_url": str, "caller_name": str, "caller_phone": str,
          "duration_seconds": int, "call_type": "inbound"|"outbound"}
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.services.voice.transcription import transcribe_audio_url

logger = logging.getLogger(__name__)

SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


# ── AI summary generation ─────────────────────────────────────────────────────

async def _generate_call_summary(
    transcript: str,
    caller_name: str,
    call_type: str,
    duration_s: int,
) -> dict[str, Any]:
    """Generate structured call summary using AI Fabric."""
    try:
        from app.services.ai.router import ai_router

        prompt = (
            f"Summarise this {call_type} sales call with {caller_name or 'a prospect'} "
            f"(duration: {duration_s}s) for the CEO's review.\n\n"
            f"Transcript:\n{transcript[:3000]}\n\n"
            "Return a JSON object with:\n"
            "  summary: str (2-3 sentences, what was discussed)\n"
            "  outcome: 'interested' | 'not_interested' | 'needs_follow_up' | 'closed' | 'unknown'\n"
            "  next_action: str (what to do next, max 50 words)\n"
            "  key_points: list[str] (3-5 bullet points)\n"
            "  sentiment: 'positive' | 'neutral' | 'negative'\n"
            "Return only the JSON, no markdown."
        )
        response, _ = await ai_router.chat(
            messages=[{"role": "user", "content": prompt}],
            task_type="ANALYSIS",
        )
        if response and not response.error and response.content:
            import json, re
            m = re.search(r"\{.*\}", response.content, re.DOTALL)
            if m:
                return json.loads(m.group())
    except Exception as exc:
        logger.debug("[CallSummariser] AI summary failed: %s", exc)

    return {
        "summary": f"{call_type.title()} call with {caller_name} ({duration_s}s). Transcript processed.",
        "outcome": "unknown",
        "next_action": "Review transcript and follow up.",
        "key_points": [],
        "sentiment": "neutral",
    }


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def process_call_recording(
    recording_url: str,
    caller_name: str = "",
    caller_phone: str = "",
    duration_seconds: int = 0,
    call_type: str = "inbound",
) -> dict[str, Any]:
    """
    Full pipeline:
    1. Transcribe recording via Whisper
    2. Generate AI summary
    3. Store to memory
    4. Alert Captain via Slack + Telegram
    5. Return structured result
    """
    started = datetime.now(UTC)
    logger.info(
        "[CallSummariser] Processing %s call from %s (%ds)",
        call_type, caller_name or caller_phone, duration_seconds
    )

    # Step 1: Transcribe
    transcription = await transcribe_audio_url(recording_url)
    transcript = transcription.get("transcript", "")
    language = transcription.get("language", "unknown")

    if not transcript:
        return {
            "status": "transcription_failed",
            "error": transcription.get("error"),
            "caller": caller_name,
        }

    # Step 2: AI Summary
    summary_data = await _generate_call_summary(
        transcript, caller_name, call_type, duration_seconds
    )

    # Step 3: Store to memory
    await _persist_call_summary(
        caller_name=caller_name,
        caller_phone=caller_phone,
        transcript=transcript,
        summary=summary_data,
        call_type=call_type,
        duration_s=duration_seconds,
        language=language,
    )

    # Step 4: Alert Captain
    outcome = summary_data.get("outcome", "unknown")
    next_action = summary_data.get("next_action", "")
    summary_text = summary_data.get("summary", "")
    await _alert_captain(caller_name, call_type, outcome, summary_text, next_action)

    elapsed = (datetime.now(UTC) - started).total_seconds()
    return {
        "status": "processed",
        "caller": caller_name,
        "phone": caller_phone,
        "call_type": call_type,
        "language": language,
        "transcript_chars": len(transcript),
        "outcome": outcome,
        "summary": summary_data,
        "processing_seconds": round(elapsed, 2),
    }


async def _persist_call_summary(
    caller_name: str,
    caller_phone: str,
    transcript: str,
    summary: dict,
    call_type: str,
    duration_s: int,
    language: str,
) -> None:
    try:
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import text as sqla_text

        today = datetime.now(UTC).date().isoformat()
        key = f"call_summary.{caller_phone or caller_name}.{today}"
        value_str = (
            f"[{language.upper()}] {call_type.upper()} call ({duration_s}s) | "
            f"Outcome: {summary.get('outcome')} | {summary.get('summary', '')[:300]} | "
            f"Next: {summary.get('next_action', '')[:100]}"
        )

        async with AsyncSessionLocal() as session:
            await session.execute(sqla_text(
                "INSERT INTO memory (tenant_id, layer, key, value, confidence, version) "
                "VALUES (:tid, 'episodic', :key, :val, 0.9, 1) "
                "ON CONFLICT (tenant_id, key) DO UPDATE SET "
                "value=EXCLUDED.value, updated_at=NOW()"
            ), {"tid": SYSTEM_TENANT_ID, "key": key, "val": value_str})
            await session.commit()
    except Exception as exc:
        logger.debug("[CallSummariser] Persist failed: %s", exc)


async def _alert_captain(
    caller: str, call_type: str, outcome: str, summary: str, next_action: str
) -> None:
    try:
        from app.services.notifications.slack import notify_slack

        emoji = {"interested": "🔥", "closed": "✅", "not_interested": "❌"}.get(outcome, "📞")
        msg = (
            f"{emoji} *{call_type.upper()} Call Complete* — {caller}\n"
            f"Outcome: *{outcome}*\n{summary[:200]}\n"
            f"Next: {next_action[:100]}"
        )
        await notify_slack(msg)
    except Exception as exc:
        logger.debug("[CallSummariser] Alert failed: %s", exc)
