"""V6-2: Voice Briefing Activation.

Converts morning briefing text to an ElevenLabs voice note and
delivers it to Captain via Telegram sendVoice API.

This activates the framework already in aionx/voice_integration.py
by wiring it into the morning briefing scheduler job.

Chain: briefing text → ElevenLabs TTS → .ogg bytes → Telegram sendVoice
"""
from __future__ import annotations

import io
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
_TELEGRAM_SEND_VOICE = "https://api.telegram.org/bot{token}/sendVoice"

# Optimal ElevenLabs settings for executive voice delivery
_VOICE_SETTINGS = {
    "stability": 0.65,
    "similarity_boost": 0.80,
    "style": 0.10,
    "use_speaker_boost": True,
}


async def _tts_elevenlabs(text: str, voice_id: str | None = None) -> bytes | None:
    """Call ElevenLabs TTS API. Returns raw MP3 bytes or None on failure."""
    if not settings.ELEVENLABS_API_KEY:
        logger.debug("[BriefingVoice] ELEVENLABS_API_KEY not set")
        return None

    vid = voice_id or settings.ELEVENLABS_VOICE_ID or "onwK4e9ZLuTAKqWW03F9"
    url = _ELEVENLABS_TTS_URL.format(voice_id=vid)

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                url,
                headers={
                    "xi-api-key": settings.ELEVENLABS_API_KEY,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": text[:2500],
                    "model_id": "eleven_turbo_v2",
                    "voice_settings": _VOICE_SETTINGS,
                },
            )
        if r.status_code == 200:
            return r.content
        logger.warning("[BriefingVoice] ElevenLabs %s: %s", r.status_code, r.text[:200])
        return None
    except Exception as exc:
        logger.warning("[BriefingVoice] ElevenLabs error: %s", exc)
        return None


async def _send_telegram_voice(
    audio_bytes: bytes, caption: str = "JARVIS Morning Briefing"
) -> bool:
    """Send voice note to Captain via Telegram sendVoice."""
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", None)

    if not token or not chat_id:
        logger.debug("[BriefingVoice] Telegram not configured — voice delivery skipped")
        return False

    url = _TELEGRAM_SEND_VOICE.format(token=token)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                url,
                data={"chat_id": chat_id, "caption": caption},
                files={"voice": ("briefing.mp3", io.BytesIO(audio_bytes), "audio/mpeg")},
            )
        ok = r.status_code == 200 and r.json().get("ok", False)
        if not ok:
            logger.warning("[BriefingVoice] Telegram sendVoice failed: %s", r.text[:200])
        return ok
    except Exception as exc:
        logger.warning("[BriefingVoice] Telegram voice send error: %s", exc)
        return False


async def deliver_briefing_as_voice(briefing_text: str) -> dict[str, Any]:
    """
    Full pipeline: text → ElevenLabs MP3 → Telegram voice note to Captain.
    Called by the morning_briefing scheduler job (hook in engine.py).
    Non-fatal: failure does not prevent text briefing from being sent.
    """
    if not briefing_text or not briefing_text.strip():
        return {"delivered": False, "reason": "empty_text"}

    # Trim to a reasonable voice length (~60 seconds max)
    MAX_CHARS = 800
    if len(briefing_text) > MAX_CHARS:
        suffix = " — briefing continues in dashboard."
        voice_text = briefing_text[:MAX_CHARS - len(suffix)].rsplit(" ", 1)[0] + suffix
    else:
        voice_text = briefing_text

    logger.info("[BriefingVoice] Generating voice for %d chars", len(voice_text))

    audio = await _tts_elevenlabs(voice_text)
    if not audio:
        return {"delivered": False, "reason": "tts_failed"}

    sent = await _send_telegram_voice(audio, caption="🎙️ JARVIS Morning Briefing (voice)")
    result = {"delivered": sent, "audio_bytes": len(audio), "text_chars": len(voice_text)}
    logger.info("[BriefingVoice] Delivery result: %s", result)
    return result


async def send_alert_voice(alert_text: str, caption: str = "⚠️ JARVIS Alert") -> dict[str, Any]:
    """Send a critical alert as a voice note to Captain."""
    audio = await _tts_elevenlabs(alert_text[:500])
    if not audio:
        return {"delivered": False, "reason": "tts_failed"}
    sent = await _send_telegram_voice(audio, caption=caption)
    return {"delivered": sent, "audio_bytes": len(audio)}
