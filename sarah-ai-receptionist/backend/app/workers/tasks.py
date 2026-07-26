"""
Background jobs run by the Arq worker: post-call AI summaries and
appointment reminders. Queued from the API/voice services via Redis.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import get_db_context
from app.models.appointment import Appointment
from app.models.call_log import CallLog
from app.models.clinic import Clinic
from app.services.ai_brain import AIBrain
from app.services.notification_service import send_appointment_reminder

logger = logging.getLogger(__name__)


async def summarize_call(ctx, call_log_id: str):
    """Generates a short AI summary of a call transcript using the fast/cheap model."""
    async with get_db_context() as db:
        result = await db.execute(select(CallLog).where(CallLog.id == call_log_id))
        call_log = result.scalar_one_or_none()
        if not call_log or not call_log.transcript:
            return

        transcript_text = "\n".join(f"{t['role']}: {t['content']}" for t in call_log.transcript)

        from app.config.settings import get_settings
        settings = get_settings()
        brain = AIBrain(model=settings.ai_model_summary)
        summary_parts = []
        async for kind, payload in brain.stream_response(
            f"Summarize this call in one sentence for a clinic front-desk dashboard:\n\n{transcript_text}"
        ):
            if kind == "sentence":
                summary_parts.append(payload)
        await brain.close()

        call_log.ai_summary = " ".join(summary_parts).strip()
        await db.flush()

    logger.info(f"Summarized call {call_log_id}")


async def enforce_call_retention(ctx):
    """Redacts transcript/summary/recording data on calls past the configured
    retention window. The CallLog row itself (outcome, timing, latency stats)
    is kept for aggregate reporting — only the PHI-bearing fields are cleared."""
    from app.config.settings import get_settings

    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.call_transcript_retention_days)

    async with get_db_context() as db:
        result = await db.execute(
            select(CallLog).where(
                CallLog.started_at < cutoff,
                CallLog.transcript != [],
            )
        )
        expired = result.scalars().all()
        for call_log in expired:
            call_log.transcript = []
            call_log.ai_summary = None
            call_log.recording_s3_key = None
        await db.flush()

    logger.info(f"Redacted {len(expired)} call transcripts past the {settings.call_transcript_retention_days}-day retention window")


async def send_reminders(ctx):
    """Runs periodically: sends SMS reminders for appointments happening in ~24h."""
    window_start = datetime.now(timezone.utc) + timedelta(hours=23)
    window_end = datetime.now(timezone.utc) + timedelta(hours=25)

    async with get_db_context() as db:
        result = await db.execute(
            select(Appointment, Clinic)
            .join(Clinic, Clinic.id == Appointment.clinic_id)
            .where(
                Appointment.appointment_datetime >= window_start,
                Appointment.appointment_datetime <= window_end,
                Appointment.reminder_sent == False,
                Appointment.status == "scheduled",
            )
        )
        rows = result.all()

        for appointment, clinic in rows:
            sent = await send_appointment_reminder(
                appointment.patient_phone,
                clinic.name,
                appointment.service_type,
                appointment.appointment_datetime.strftime("%B %d at %I:%M %p"),
            )
            if sent:
                appointment.reminder_sent = True

        await db.flush()

    logger.info(f"Sent {len(rows)} appointment reminders")
