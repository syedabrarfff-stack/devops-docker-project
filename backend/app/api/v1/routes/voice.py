"""
JARVIS Backend TTS — text-to-speech endpoint.
Chain: OpenAI (onyx) → ElevenLabs → Edge TTS (offline fallback).
Frontend calls this instead of direct browser synthesis for better quality.
"""
import logging
import base64
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from app.api.v1.routes.auth import get_current_captain
from pydantic import BaseModel, Field
from typing import Optional
from app.core.config import settings
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"], dependencies=[Depends(get_current_captain)])

JARVIS_VOICE_INSTRUCTIONS = (
    "You are JARVIS, a calm, highly capable executive AI assistant. "
    "Warm, measured, and confident. British executive demeanour. "
    "Speak clearly and precisely — this is voice output, no markdown."
)


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4_096)
    provider: Optional[str] = Field(default="auto", max_length=50)
    voice: Optional[str] = Field(default=None, max_length=100)


class TTSResponse(BaseModel):
    audio_base64: str
    mime_type: str
    provider: str
    characters: int


@router.post("/tts", response_model=TTSResponse)
@limiter.limit("10/minute")
async def text_to_speech(request: Request, body: TTSRequest):
    """
    Convert text to speech. Returns base64-encoded audio.
    Frontend plays it via: new Audio('data:<mime>;base64,<audio_base64>').play()
    """
    if not body.text or len(body.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="No text provided")

    text = body.text[:2000]  # Safety cap

    if body.provider == "openai" or body.provider == "auto":
        result = await _tts_openai(text)
        if result:
            return result

    if body.provider in ("elevenlabs", "auto"):
        result = await _tts_elevenlabs(text)
        if result:
            return result

    result = await _tts_edge(text)
    if result:
        return result

    raise HTTPException(status_code=503, detail="All TTS providers unavailable")


async def _tts_openai(text: str) -> Optional[TTSResponse]:
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "tts-1-hd",
                    "input": text,
                    "voice": "onyx",
                    "instructions": JARVIS_VOICE_INSTRUCTIONS,
                    "response_format": "mp3",
                    "speed": 0.95,
                },
            )
            if resp.status_code == 200:
                return TTSResponse(
                    audio_base64=base64.b64encode(resp.content).decode(),
                    mime_type="audio/mpeg",
                    provider="openai",
                    characters=len(text),
                )
            logger.warning(f"OpenAI TTS error {resp.status_code}")
    except Exception as e:
        logger.warning(f"OpenAI TTS exception: {e}")
    return None


async def _tts_elevenlabs(text: str) -> Optional[TTSResponse]:
    api_key = getattr(settings, "ELEVENLABS_API_KEY", None)
    voice_id = getattr(settings, "ELEVENLABS_VOICE_ID", "onwK4e9ZLuTAKqWW03F9")
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_turbo_v2_5",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.8,
                        "style": 0.2,
                        "use_speaker_boost": True,
                    },
                },
            )
            if resp.status_code == 200:
                return TTSResponse(
                    audio_base64=base64.b64encode(resp.content).decode(),
                    mime_type="audio/mpeg",
                    provider="elevenlabs",
                    characters=len(text),
                )
            logger.warning(f"ElevenLabs TTS error {resp.status_code}")
    except Exception as e:
        logger.warning(f"ElevenLabs TTS exception: {e}")
    return None


async def _tts_edge(text: str) -> Optional[TTSResponse]:
    """Offline fallback using edge-tts (British male voice)."""
    try:
        import edge_tts
        import io
        communicate = edge_tts.Communicate(text=text, voice="en-GB-RyanNeural", rate="-5%", pitch="-5Hz")
        audio_io = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_io.write(chunk["data"])
        audio_bytes = audio_io.getvalue()
        if audio_bytes:
            return TTSResponse(
                audio_base64=base64.b64encode(audio_bytes).decode(),
                mime_type="audio/mpeg",
                provider="edge_tts",
                characters=len(text),
            )
    except ImportError:
        logger.debug("edge-tts not installed — skipping offline fallback")
    except Exception as e:
        logger.warning(f"Edge TTS exception: {e}")
    return None


@router.get("/providers")
async def voice_providers():
    """Which TTS providers are available."""
    has_openai = bool(getattr(settings, "OPENAI_API_KEY", None))
    has_elevenlabs = bool(getattr(settings, "ELEVENLABS_API_KEY", None))

    try:
        import edge_tts
        has_edge = True
    except ImportError:
        has_edge = False

    return {
        "providers": {
            "openai": {"available": has_openai, "model": "tts-1-hd", "voice": "onyx", "quality": "premium"},
            "elevenlabs": {"available": has_elevenlabs, "model": "eleven_turbo_v2_5", "voice": "Daniel", "quality": "ultra"},
            "edge_tts": {"available": has_edge, "voice": "en-GB-RyanNeural", "quality": "good"},
        },
        "active_provider": "openai" if has_openai else ("elevenlabs" if has_elevenlabs else ("edge_tts" if has_edge else "none")),
        "note": "Frontend uses browser TTS as a last resort if all backend providers fail.",
    }
