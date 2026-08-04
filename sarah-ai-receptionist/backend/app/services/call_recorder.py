"""
Persists call transcripts to the database and (in production) recordings to S3.
"""

import logging
from datetime import datetime, timezone

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import update

from app.config.settings import get_settings
from app.core.clinic_time import format_for_caller
from app.core.database import get_db_context
from app.models.appointment import Appointment
from app.models.call_log import CallLog
from app.services.appointment_service import (
    book_appointment_from_action,
    cancel_appointment_from_action,
    reschedule_appointment_from_action,
)
from app.services.notification_service import (
    send_appointment_change,
    send_appointment_confirmation,
    send_urgent_escalation,
)

logger = logging.getLogger(__name__)
settings = get_settings()


async def save_call_transcript(call_sid: str, clinic_config: dict | None, result: dict) -> None:
    clinic_id = (clinic_config or {}).get("_clinic_id")
    if not clinic_id:
        logger.warning(f"No clinic_id for call {call_sid}, skipping persistence")
        return

    started_at = result.get("started_at") or datetime.now(timezone.utc)
    transfer_result = result.get("transfer_result")
    fulfillment = result.get("fulfillment_actions", [])

    # The outcome label is what the caller actually accomplished. A concrete
    # booking/change outranks the [END] the call happened to finish on — the
    # bug this replaces let that [END] overwrite a [BOOK] and lose it.
    booked = any(fa["action"] == "BOOK" for fa in fulfillment)
    if fulfillment:
        outcome = fulfillment[-1]["action"]
    elif transfer_result:
        outcome = "TRANSFER"
    else:
        outcome = result.get("outcome")

    clinic_timezone = (clinic_config or {}).get("_timezone")
    # Primitives captured inside the session so SMS can be sent after it closes.
    changes: list[dict] = []

    async with get_db_context() as db:
        call_log = CallLog(
            clinic_id=clinic_id,
            call_sid=call_sid,
            caller_phone=result.get("caller_phone"),
            started_at=started_at,
            duration_seconds=result.get("duration_seconds"),
            exchange_count=len(result.get("transcript", [])),
            outcome=outcome,
            transferred=transfer_result is not None,
            transfer_result=transfer_result,
            appointment_booked=booked,
            transcript=result.get("transcript", []),
            avg_response_ms=result.get("avg_response_ms"),
            recording_s3_key=result.get("recording_s3_key"),
            # The consent disclosure is unconditionally spoken before the media
            # stream connects (call_handler.CONSENT_DISCLOSURE) — every call
            # that reaches persistence has had it played.
            consent_disclosed=True,
        )
        db.add(call_log)
        await db.flush()
        call_log_id = call_log.id

        # Apply each booking/change in the order it happened. A cancel-then-book
        # (the caller moved to a different clinic day) is two actions and both
        # run. Confirm what was actually written, not the caller's raw phrase.
        for fa in fulfillment:
            act, params = fa["action"], fa.get("params", {})
            appt = None
            if act == "BOOK":
                appt = await book_appointment_from_action(db, clinic_id, params, call_log_id=call_log_id)
                call_log.patient_id = appt.patient_id
            elif act == "RESCHEDULE":
                appt = await reschedule_appointment_from_action(db, clinic_id, params)
            elif act == "CANCEL":
                appt = await cancel_appointment_from_action(db, clinic_id, params)
            if appt is not None:
                changes.append({
                    "kind": {"BOOK": "booked", "RESCHEDULE": "rescheduled", "CANCEL": "cancelled"}[act],
                    "id": appt.id,
                    "phone": appt.patient_phone,
                    "service": appt.service_type,
                    "when": appt.appointment_datetime,
                })
        await db.flush()

    await _enqueue_summary(call_log_id)

    await _send_change_confirmations(clinic_config, clinic_timezone, changes)

    # Sarah told the caller their details were passed on — that has to be true.
    # Sent here rather than mid-call so an abrupt hangup can't skip it.
    escalate_to = result.get("escalate_sms_to")
    if escalate_to:
        transcript = result.get("transcript") or []
        last_caller_turn = next(
            (t.get("content") for t in reversed(transcript) if t.get("role") == "caller"), None
        )
        sent = await send_urgent_escalation(
            escalate_to,
            (clinic_config or {}).get("name", "Your clinic"),
            result.get("caller_phone"),
            last_caller_turn,
        )
        if not sent:
            # The caller was promised a callback nobody was told about — this
            # needs to be visible in the dashboard, not just the logs.
            async with get_db_context() as db:
                await db.execute(
                    update(CallLog)
                    .where(CallLog.id == call_log_id)
                    .values(transfer_result="escalation_failed")
                )
            logger.error(f"Escalation SMS failed for call {call_sid} — caller expects a callback")

    logger.info(f"Saved call log for {call_sid} (clinic {clinic_id}, outcome={outcome})")


async def _send_change_confirmations(
    clinic_config: dict | None, clinic_timezone: str | None, changes: list[dict]
) -> None:
    """Text the caller a confirmation for each booking/change actually written.

    Runs after the DB session closes so a slow carrier can't hold the call's
    persistence transaction open. A booking marks confirmation_sms_sent so the
    dashboard can tell a delivered confirmation from a silent failure."""
    clinic_name = (clinic_config or {}).get("name", "our clinic")
    for change in changes:
        phone = change.get("phone")
        if not phone:
            continue
        when = format_for_caller(change["when"], clinic_timezone)
        if change["kind"] == "booked":
            sent = await send_appointment_confirmation(
                phone, clinic_name, change["service"] or "your appointment", when
            )
            if sent:
                async with get_db_context() as db:
                    await db.execute(
                        update(Appointment)
                        .where(Appointment.id == change["id"])
                        .values(confirmation_sms_sent=True)
                    )
        else:
            await send_appointment_change(
                phone, clinic_name, change["kind"], change["service"] or "your appointment", when
            )


async def _enqueue_summary(call_log_id: str) -> None:
    try:
        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        await redis.enqueue_job("summarize_call", call_log_id)
        await redis.close()
    except Exception as e:
        logger.warning(f"Failed to enqueue call summary job for {call_log_id}: {e}")


def _wrap_mulaw_in_wav(mulaw_bytes: bytes, sample_rate: int = 8000) -> bytes:
    """Wraps raw G.711 mulaw samples in a minimal WAV container (format tag 7)
    so the result is a real, browser-playable file — Python's `wave` module
    only supports PCM, so this builds the 44-byte RIFF/WAVE header by hand."""
    import struct

    data_size = len(mulaw_bytes)
    byte_rate = sample_rate  # 1 byte/sample, mono, mulaw
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 7, 1, sample_rate, byte_rate, 1, 8,
        b"data", data_size,
    )
    return header + mulaw_bytes


async def upload_recording_to_s3(call_sid: str, audio_bytes: bytes, clinic_id: str) -> str | None:
    """Uploads a call recording to S3, KMS-encrypted. Returns the S3 key.

    On ECS, credentials come from the task's IAM role, not static keys — the
    previous version only ever ran when AWS_ACCESS_KEY_ID was explicitly set,
    which is never true in production, so this silently never uploaded
    anything there. boto3's default credential chain (env vars if present,
    otherwise the task/instance role) is used instead.
    """
    import asyncio

    import boto3

    client_kwargs = {"region_name": settings.aws_region}
    if settings.aws_access_key_id:
        client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
        client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key

    s3 = boto3.client("s3", **client_kwargs)
    key = f"recordings/{clinic_id}/{call_sid}.wav"
    wav_bytes = _wrap_mulaw_in_wav(audio_bytes)

    await asyncio.to_thread(
        s3.put_object,
        Bucket=settings.s3_bucket_recordings,
        Key=key,
        Body=wav_bytes,
        ServerSideEncryption="aws:kms",
        ContentType="audio/wav",
    )
    return key
