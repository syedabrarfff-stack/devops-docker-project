import base64
import io
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings


router = APIRouter(prefix="/voice", tags=["voice"])

OPENAI_TTS_MODEL = "tts-1-hd"
OPENAI_VOICE = "onyx"
ELEVENLABS_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
EDGE_VOICE = "en-GB-RyanNeural"

JARVIS_VOICE_INSTRUCTIONS = (
    "Speak like a calm, highly capable executive AI assistant. "
    "Warm, measured, confident, cinematic but not theatrical. "
    "Use natural pauses, subtle emphasis, and avoid robotic monotone delivery. "
    "Address the user as Captain only when it sounds natural."
)


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2400)
    mood: Literal["briefing", "calm", "urgent", "friendly"] = "briefing"
    provider: Literal["auto", "edge", "elevenlabs", "openai"] = "auto"


class SpeakResponse(BaseModel):
    audio_base64: str
    mime_type: str
    provider: str


def _trim_text(text: str) -> str:
    return " ".join(text.split())[:2400]


async def _speak_with_elevenlabs(text: str) -> SpeakResponse:
    if not settings.ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY is not configured")

    voice_id = getattr(settings, "ELEVENLABS_VOICE_ID", None) or ELEVENLABS_VOICE_ID
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.42,
            "similarity_boost": 0.82,
            "style": 0.32,
            "use_speaker_boost": True,
        },
    }
    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return SpeakResponse(
            audio_base64=base64.b64encode(response.content).decode("ascii"),
            mime_type="audio/mpeg",
            provider="elevenlabs",
        )


async def _speak_with_edge(text: str, mood: str) -> SpeakResponse:
    import edge_tts

    rates = {
        "briefing": "-10%",
        "calm": "-14%",
        "urgent": "-4%",
        "friendly": "-8%",
    }
    pitches = {
        "briefing": "-7Hz",
        "calm": "-9Hz",
        "urgent": "-4Hz",
        "friendly": "-5Hz",
    }

    stream = io.BytesIO()
    communicate = edge_tts.Communicate(
        text,
        EDGE_VOICE,
        rate=rates[mood],
        pitch=pitches[mood],
        volume="+0%",
    )
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            stream.write(chunk["data"])

    audio = stream.getvalue()
    if not audio:
        raise RuntimeError("Edge neural voice returned no audio")

    return SpeakResponse(
        audio_base64=base64.b64encode(audio).decode("ascii"),
        mime_type="audio/mpeg",
        provider="edge",
    )


async def _speak_with_openai(text: str, mood: str) -> SpeakResponse:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    from openai import AsyncOpenAI

    mood_instruction = {
        "briefing": "Delivery should feel like a concise mission briefing with thoughtful pauses.",
        "calm": "Delivery should be calm, grounded, and human.",
        "urgent": "Delivery should be focused and serious, but never rushed.",
        "friendly": "Delivery should be warm and conversational.",
    }[mood]

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    response = await client.audio.speech.create(
        model=OPENAI_TTS_MODEL,
        voice=OPENAI_VOICE,
        input=text,
        response_format="mp3",
        speed=0.92 if mood != "urgent" else 0.98,
    )
    content = response.content
    return SpeakResponse(
        audio_base64=base64.b64encode(content).decode("ascii"),
        mime_type="audio/mpeg",
        provider="openai",
    )


@router.get("/status")
async def voice_status():
    return {
        "advanced_voice": bool(settings.ELEVENLABS_API_KEY or settings.OPENAI_API_KEY),
        "providers": {
            "edge": True,
            "elevenlabs": bool(settings.ELEVENLABS_API_KEY),
            "openai": bool(settings.OPENAI_API_KEY),
        },
        "fallback": "browser_speech",
    }


@router.post("/speak", response_model=SpeakResponse)
async def speak(req: SpeakRequest):
    text = _trim_text(req.text)
    providers = (
        [req.provider]
        if req.provider != "auto"
        else ["edge", "openai", "elevenlabs"]
    )

    errors: list[str] = []
    for provider in providers:
        try:
            if provider == "edge":
                return await _speak_with_edge(text, req.mood)
            if provider == "elevenlabs":
                return await _speak_with_elevenlabs(text)
            if provider == "openai":
                return await _speak_with_openai(text, req.mood)
        except Exception as exc:
            errors.append(f"{provider}: {exc}")

    raise HTTPException(
        status_code=503,
        detail={
            "message": "Advanced voice is not available. Configure ELEVENLABS_API_KEY or OPENAI_API_KEY.",
            "errors": errors,
        },
    )
