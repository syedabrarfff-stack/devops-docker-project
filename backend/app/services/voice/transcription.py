"""V6-1: WhatsApp voice transcription pipeline.

Receives audio files (ogg/m4a/mp3/wav) from Evolution API webhooks,
sends to OpenAI Whisper API for transcription, returns structured result.

Flow:
1. Evolution API receives voice message → calls JARVIS webhook
2. JARVIS downloads the audio file from Evolution
3. Sends to Whisper → gets transcript
4. Routes to AI for intent classification + auto-reply generation
5. Stores interaction in memory
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"
_SUPPORTED_FORMATS = {".ogg", ".mp3", ".mp4", ".m4a", ".wav", ".webm"}


# ── Whisper transcription ─────────────────────────────────────────────────────

async def transcribe_audio_url(audio_url: str, language: str | None = None) -> dict[str, Any]:
    """
    Download audio from URL and transcribe via OpenAI Whisper.
    Returns {"transcript": str, "language": str, "duration_s": float | None}.
    """
    if not settings.OPENAI_API_KEY:
        return {
            "transcript": "",
            "language": language or "unknown",
            "error": "OPENAI_API_KEY not configured",
        }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            audio_resp = await client.get(audio_url)
        audio_resp.raise_for_status()
    except Exception as exc:
        logger.warning("[Transcription] Download failed: %s", exc)
        return {"transcript": "", "error": f"download_failed: {exc}"}

    # Detect extension from URL or default to .ogg (WhatsApp standard)
    suffix = Path(audio_url.split("?")[0]).suffix.lower() or ".ogg"
    if suffix not in _SUPPORTED_FORMATS:
        suffix = ".ogg"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_resp.content)
        tmp_path = Path(tmp.name)

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            with open(tmp_path, "rb") as f:
                form_data = {
                    "model": "whisper-1",
                    "response_format": "verbose_json",
                }
                if language:
                    form_data["language"] = language
                r = await client.post(
                    _WHISPER_URL,
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    files={"file": (f"audio{suffix}", f, "audio/ogg")},
                    data=form_data,
                )
        r.raise_for_status()
        data = r.json()
        return {
            "transcript": data.get("text", ""),
            "language": data.get("language", language or "unknown"),
            "duration_s": data.get("duration"),
        }
    except Exception as exc:
        logger.warning("[Transcription] Whisper error: %s", exc)
        return {"transcript": "", "error": str(exc)}
    finally:
        tmp_path.unlink(missing_ok=True)


async def transcribe_audio_bytes(
    audio_bytes: bytes, filename: str = "audio.ogg", language: str | None = None
) -> dict[str, Any]:
    """Transcribe raw audio bytes (for direct upload scenarios)."""
    if not settings.OPENAI_API_KEY:
        return {"transcript": "", "error": "OPENAI_API_KEY not configured"}

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            form_data: dict[str, Any] = {"model": "whisper-1", "response_format": "verbose_json"}
            if language:
                form_data["language"] = language
            r = await client.post(
                _WHISPER_URL,
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                files={"file": (filename, audio_bytes, "audio/ogg")},
                data=form_data,
            )
        r.raise_for_status()
        data = r.json()
        return {
            "transcript": data.get("text", ""),
            "language": data.get("language", "unknown"),
            "duration_s": data.get("duration"),
        }
    except Exception as exc:
        logger.warning("[Transcription] Bytes transcription error: %s", exc)
        return {"transcript": "", "error": str(exc)}


# ── Intent classification ─────────────────────────────────────────────────────

async def classify_voice_intent(transcript: str, sender_phone: str) -> dict[str, Any]:
    """
    Classify a transcribed voice message into an intent category.
    Intents: pricing_inquiry | meeting_request | support | lead_qualification
             | approval_response | general | spam
    """
    if not transcript.strip():
        return {"intent": "unknown", "confidence": 0.0, "reply": None}

    try:
        from app.services.ai.router import ai_router

        prompt = (
            "Classify this WhatsApp voice message from a prospect into exactly one intent:\n"
            "pricing_inquiry | meeting_request | support | lead_qualification | "
            "approval_response | general | spam\n\n"
            f"Message: \"{transcript[:500]}\"\n\n"
            "Respond in JSON: {\"intent\": \"<intent>\", \"confidence\": 0.0-1.0, "
            "\"suggested_reply\": \"<brief reply in <100 words>\"}"
        )
        response = await ai_router.chat(
            messages=[{"role": "user", "content": prompt}],
            task_type="FAST",
        )
        if response and not response.error:
            import json, re
            m = re.search(r"\{.*\}", response.content or "", re.DOTALL)
            if m:
                data = json.loads(m.group())
                return {
                    "intent": data.get("intent", "general"),
                    "confidence": float(data.get("confidence", 0.7)),
                    "reply": data.get("suggested_reply"),
                }
    except Exception as exc:
        logger.debug("[Transcription] Intent classification error: %s", exc)

    return {"intent": "general", "confidence": 0.5, "reply": None}


# ── Store interaction in memory ───────────────────────────────────────────────

async def store_voice_interaction(
    phone: str, transcript: str, intent: str, language: str
) -> None:
    """Persist voice interaction to episodic memory for future AI context."""
    try:
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import text as sqla_text
        import uuid
        from datetime import date

        system_tenant = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
        key = f"voice_interaction.{phone}.{date.today().isoformat()}"
        value = f"[{language.upper()}] Intent={intent} | Transcript: {transcript[:500]}"

        async with AsyncSessionLocal() as session:
            await session.execute(sqla_text(
                "INSERT INTO memory (tenant_id, layer, key, value, confidence, version) "
                "VALUES (:tid, 'episodic', :key, :val, 0.8, 1) "
                "ON CONFLICT (tenant_id, key) DO UPDATE SET "
                "value = memory.value || ' | ' || EXCLUDED.value, updated_at=NOW()"
            ), {"tid": system_tenant, "key": key, "val": value})
            await session.commit()
    except Exception as exc:
        logger.debug("[Transcription] Memory store failed: %s", exc)
