"""AIONX Voice Integration — ElevenLabs TTS for Captain briefings and council sessions.

Converts key intelligence outputs to voice for Captain's morning briefing, council
sessions, and alerts. Uses ElevenLabs API for premium voice synthesis.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ElevenLabs configuration
ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY", "")
ELEVEN_LABS_VOICE_ID = "Daniel"  # Daniel = British male voice (configured in system)

# Voice personas for different contexts
VOICE_PERSONAS = {
    "BRIEFING": {
        "voice_id": "Daniel",
        "tone": "professional",
        "speed": 1.0,
        "context": "Captain's morning briefing",
    },
    "ALERT": {
        "voice_id": "Daniel",
        "tone": "urgent",
        "speed": 1.1,
        "context": "Emergency alert",
    },
    "COUNCIL": {
        "voice_id": "Daniel",
        "tone": "formal",
        "speed": 0.95,
        "context": "Council session recommendation",
    },
    "NOTIFICATION": {
        "voice_id": "Daniel",
        "tone": "conversational",
        "speed": 1.0,
        "context": "Standard notification",
    },
}


async def generate_briefing_voice(
    briefing_text: str,
    voice_persona: str = "BRIEFING",
) -> dict[str, Any]:
    """Generate voice synthesis for Captain's morning briefing."""

    if not ELEVEN_LABS_API_KEY:
        logger.warning("ElevenLabs API key not configured — voice synthesis disabled")
        return {
            "audio_url": None,
            "status": "VOICE_DISABLED",
            "reason": "API key not configured",
        }

    if voice_persona not in VOICE_PERSONAS:
        voice_persona = "BRIEFING"

    persona = VOICE_PERSONAS[voice_persona]

    logger.info(
        "Voice Briefing: Generating %s audio for Captain (persona=%s, length=%d chars)",
        persona["tone"], voice_persona, len(briefing_text)
    )

    # Prepare text for TTS (limit to ~2000 chars for API)
    clean_text = _prepare_tts_text(briefing_text)

    # In production, would call:
    # response = await elevenlabs.text_to_speech(
    #     text=clean_text,
    #     voice_id=persona["voice_id"],
    #     stability=0.5,
    #     similarity_boost=0.75,
    #     model_id="eleven_monolingual_v1"
    # )

    return {
        "briefing_text": clean_text,
        "voice_persona": voice_persona,
        "tone": persona["tone"],
        "speed": persona["speed"],
        "status": "READY_FOR_VOICE",
        "expected_duration_seconds": len(clean_text) / 20,  # ~20 chars/sec
        "note": "ElevenLabs voice synthesis mocked in non-production environment",
    }


async def generate_council_voice(
    council_recommendation: str,
    council_name: str = "Convergence Council",
) -> dict[str, Any]:
    """Generate voice for council session recommendation to Captain."""

    logger.info(
        "Council Voice: Generating recommendation audio for %s (%d chars)",
        council_name, len(council_recommendation)
    )

    clean_text = _prepare_tts_text(council_recommendation)

    return {
        "council_name": council_name,
        "recommendation_text": clean_text,
        "voice_persona": "COUNCIL",
        "status": "READY_FOR_VOICE",
        "expected_duration_seconds": len(clean_text) / 20,
    }


async def generate_alert_voice(
    alert_message: str,
    severity: str = "HIGH",
) -> dict[str, Any]:
    """Generate urgent alert voice for Captain."""

    logger.warning("Alert Voice: Generating %s severity alert (%d chars)", severity, len(alert_message))

    clean_text = _prepare_tts_text(alert_message)

    return {
        "alert_message": clean_text,
        "severity": severity,
        "voice_persona": "ALERT",
        "status": "READY_FOR_VOICE",
        "expected_duration_seconds": len(clean_text) / 22,  # Faster for alerts
    }


def _prepare_tts_text(text: str, max_chars: int = 2000) -> str:
    """Clean and prepare text for text-to-speech synthesis."""
    # Remove markdown formatting
    clean = text.replace("**", "").replace("__", "").replace("`", "")
    # Replace common abbreviations
    clean = clean.replace("CEO", "Chief Executive Officer")
    clean = clean.replace("KPI", "Key Performance Indicator")
    clean = clean.replace("AI", "Artificial Intelligence")
    clean = clean.replace("$", "dollar ")
    clean = clean.replace("%", " percent")
    # Truncate if needed
    if len(clean) > max_chars:
        clean = clean[:max_chars] + "..."
    return clean.strip()


async def stream_briefing_to_captain(
    briefing_data: dict[str, Any],
    captain_contact: str = "syed@aliyarsolutions.com",
) -> dict[str, Any]:
    """Send briefing voice + text to Captain via multiple channels."""

    voice_output = await generate_briefing_voice(briefing_data.get("narrative", ""))

    logger.info(
        "Captain Briefing Stream: Sending to %s (voice=%s, channels=slack+telegram+ws)",
        captain_contact, voice_output["status"]
    )

    return {
        "captain_contact": captain_contact,
        "briefing_summary": briefing_data.get("summary"),
        "voice_status": voice_output["status"],
        "channels": ["slack", "telegram", "websocket"],
        "timestamp": "now",
        "note": "In production, would trigger Slack/Telegram webhooks and WebSocket push",
    }


async def transcribe_council_session(
    audio_data: bytes,
) -> dict[str, Any]:
    """Transcribe council session audio (reverse: audio → text)."""

    logger.info("Council Transcription: Processing %d bytes of audio", len(audio_data))

    # In production, would call:
    # response = await elevenlabs.transcribe_audio(audio_data)

    return {
        "audio_bytes": len(audio_data),
        "status": "TRANSCRIPTION_READY",
        "note": "ElevenLabs transcription mocked in non-production environment",
    }
