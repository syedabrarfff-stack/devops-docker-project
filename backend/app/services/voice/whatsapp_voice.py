"""V6-4: WhatsApp Voice Automation.

Sends voice notes to prospects and clients via Evolution API.
Chain: text → ElevenLabs TTS → MP3 bytes → Evolution API sendAudio

Use cases:
- Proposal voice summary (after sending a proposal deck)
- Meeting reminder voice note (day before a scheduled call)
- Follow-up voice note (instead of a text message)
- Captain alert via WhatsApp voice (fallback when Telegram is unavailable)
"""
from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_EVOLUTION_BASE = "{base_url}/message/sendMedia/{instance}"


def _evolution_headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "apikey": getattr(settings, "EVOLUTION_API_KEY", "") or "",
    }


def _evolution_url(path: str) -> str:
    base = getattr(settings, "EVOLUTION_API_URL", "http://evolution:8080") or "http://evolution:8080"
    instance = getattr(settings, "EVOLUTION_INSTANCE", "jarvis") or "jarvis"
    return f"{base.rstrip('/')}/{path.lstrip('/')}/{instance}"


# ── ElevenLabs TTS ────────────────────────────────────────────────────────────

async def _generate_audio(text: str) -> bytes | None:
    """Generate MP3 audio from text via ElevenLabs."""
    if not settings.ELEVENLABS_API_KEY:
        return None

    vid = settings.ELEVENLABS_VOICE_ID or "onwK4e9ZLuTAKqWW03F9"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
                headers={
                    "xi-api-key": settings.ELEVENLABS_API_KEY,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": text[:2000],
                    "model_id": "eleven_turbo_v2",
                    "voice_settings": {"stability": 0.65, "similarity_boost": 0.80},
                },
            )
        return r.content if r.status_code == 200 else None
    except Exception as exc:
        logger.warning("[WAVoice] ElevenLabs error: %s", exc)
        return None


# ── Evolution API send ────────────────────────────────────────────────────────

async def send_voice_note(phone: str, text: str) -> dict[str, Any]:
    """
    Generate TTS audio and send as a WhatsApp voice note.
    phone: E.164 format without '+' (e.g. '447911123456')
    """
    audio = await _generate_audio(text)
    if not audio:
        return {"status": "tts_failed", "phone": phone}

    audio_b64 = base64.b64encode(audio).decode()
    payload = {
        "number": phone,
        "mediatype": "audio",
        "mimetype": "audio/mpeg",
        "media": audio_b64,
        "fileName": "jarvis_message.mp3",
        "caption": "",
    }

    try:
        url = _evolution_url("message/sendMedia")
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload, headers=_evolution_headers())
        ok = r.status_code < 300
        if not ok:
            logger.warning("[WAVoice] Evolution send failed: %s %s", r.status_code, r.text[:200])
        return {"status": "sent" if ok else "send_failed", "phone": phone, "audio_bytes": len(audio)}
    except Exception as exc:
        logger.warning("[WAVoice] Send error: %s", exc)
        return {"status": "error", "phone": phone, "detail": str(exc)}


async def send_proposal_voice_summary(lead_id: str) -> dict[str, Any]:
    """
    Fetch lead + proposal data and send a 30-second voice summary via WhatsApp.
    Called after a proposal is emailed, as an added-value touchpoint.
    """
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import text as sqla_text

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(sqla_text(
                "SELECT l.company_name, l.contact_name, l.contact_phone, "
                "p.title, p.total_value "
                "FROM leads l LEFT JOIN proposals p ON p.lead_id=l.id "
                "WHERE l.id=:lid ORDER BY p.created_at DESC LIMIT 1"
            ), {"lid": lead_id})
            row = result.fetchone()
    except Exception as exc:
        return {"status": "db_error", "detail": str(exc)}

    if not row or not row[2]:
        return {"status": "no_phone", "lead_id": lead_id}

    company, contact, phone, proposal_title, value = row
    first_name = (contact or "").split()[0] if contact else "there"
    value_str = f"${value:,.0f}" if value else "our recommended package"

    script = (
        f"Hi {first_name}, this is the team from Aliyar Solutions. "
        f"We've just sent over a proposal for {company} — "
        f"{proposal_title or 'our solution'} at {value_str}. "
        "I wanted to personally follow up and make sure you received it. "
        "We'd love to walk you through it at your convenience. "
        "Please feel free to reply to this message or check your email. "
        "Looking forward to speaking with you."
    )

    return await send_voice_note(phone, script)


async def send_meeting_reminder_voice(
    phone: str, contact_name: str, meeting_time: str, meeting_topic: str = ""
) -> dict[str, Any]:
    """Send a voice reminder the day before a scheduled meeting."""
    first = contact_name.split()[0] if contact_name else "there"
    script = (
        f"Hi {first}, this is a friendly reminder from Aliyar Solutions. "
        f"You have a meeting scheduled with our team {meeting_time}. "
        f"{f'Topic: {meeting_topic}. ' if meeting_topic else ''}"
        "We're looking forward to the conversation. "
        "If you need to reschedule, please reply to this message."
    )
    return await send_voice_note(phone, script)
