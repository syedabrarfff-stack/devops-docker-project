"""
Persists call transcripts to the database and (in production) recordings to S3.
"""

import logging
from datetime import datetime, timezone

from arq import create_pool
from arq.connections import RedisSettings

from app.config.settings import get_settings
from app.core.database import get_db_context
from app.models.call_log import CallLog
from app.services.appointment_service import book_appointment_from_action
from app.services.notification_service import send_appointment_confirmation

logger = logging.getLogger(__name__)
settings = get_settings()


async def save_call_transcript(call_sid: str, clinic_config: dict | None, result: dict) -> None:
    clinic_id = (clinic_config or {}).get("_clinic_id")
    if not clinic_id:
        logger.warning(f"No clinic_id for call {call_sid}, skipping persistence")
        return

    started_at = datetime.now(timezone.utc)
    outcome = result.get("outcome")
    action_params = result.get("action_params", {})

    async with get_db_context() as db:
        call_log = CallLog(
            clinic_id=clinic_id,
            call_sid=call_sid,
            started_at=started_at,
            duration_seconds=result.get("duration_seconds"),
            exchange_count=len(result.get("transcript", [])),
            outcome=outcome,
            transferred=outcome == "TRANSFER",
            appointment_booked=outcome == "BOOK",
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

        if outcome == "BOOK":
            appointment = await book_appointment_from_action(db, clinic_id, action_params, call_log_id=call_log_id)
            call_log.patient_id = appointment.patient_id
            await db.flush()

    await _enqueue_summary(call_log_id)

    if outcome == "BOOK" and action_params.get("phone"):
        clinic_name = (clinic_config or {}).get("name", "our clinic")
        await send_appointment_confirmation(
            action_params.get("phone"),
            clinic_name,
            action_params.get("service", "your appointment"),
            action_params.get("datetime", "the scheduled time"),
        )

    logger.info(f"Saved call log for {call_sid} (clinic {clinic_id}, outcome={outcome})")


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
