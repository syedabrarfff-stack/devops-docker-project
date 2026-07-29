"""V6-1 + V6-3 Route: Voice webhook endpoints.

POST /api/v1/webhooks/voice/transcribe  — transcribe an audio URL (Evolution API callback)
POST /api/v1/webhooks/voice/call-ended  — process a finished call recording
POST /api/v1/voice/send-note            — send a WhatsApp voice note (Captain-only)
POST /api/v1/voice/proposal-followup    — send proposal voice summary (Captain-only)
"""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional

from app.api.v1.routes.auth import get_current_captain
from app.core.config import settings
from app.services.voice.transcription import (
    transcribe_audio_url,
    transcribe_audio_bytes,
    classify_voice_intent,
    store_voice_interaction,
)
from app.services.voice.call_summariser import process_call_recording
from app.services.voice.whatsapp_voice import send_voice_note, send_proposal_voice_summary

router = APIRouter(prefix="", tags=["Voice Webhooks"])


def verify_voice_webhook_secret(request: Request) -> None:
    """
    These three routes are called by external systems (Evolution API, call
    recording integrations) with no user session to attach a JWT to — same
    situation as the Telegram/Zapier/Slack webhooks, which all validate a
    shared secret header instead. Previously the ONLY thing gating these was
    nginx's blanket Basic Auth in front of /api/ — removing that (in favor of
    a single JWT-based auth layer, per the Captain's direction) would have
    left them fully open to unauthenticated calls that trigger paid
    transcription/AI work. This restores equivalent protection at the
    application layer, matching the pattern already used by the other
    external webhooks in this codebase.
    """
    if not settings.VOICE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Voice webhook not configured")
    header = request.headers.get("X-Voice-Webhook-Secret", "")
    if not secrets.compare_digest(header, settings.VOICE_WEBHOOK_SECRET):
        raise HTTPException(status_code=403, detail="Forbidden")


# ── Schemas ───────────────────────────────────────────────────────────────────

class TranscribeRequest(BaseModel):
    audio_url: str = Field(min_length=5, max_length=2000)
    sender_phone: str = Field(default="", max_length=50)
    language: Optional[str] = Field(default=None, max_length=10)
    classify_intent: bool = False


class CallEndedRequest(BaseModel):
    recording_url: str = Field(min_length=5, max_length=2000)
    caller_name: str = Field(default="", max_length=200)
    caller_phone: str = Field(default="", max_length=50)
    duration_seconds: int = Field(default=0, ge=0)
    call_type: str = Field(default="inbound", max_length=20)


class SendVoiceRequest(BaseModel):
    phone: str = Field(min_length=7, max_length=20)
    text: str = Field(min_length=5, max_length=2000)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/webhooks/voice/transcribe", dependencies=[Depends(verify_voice_webhook_secret)])
async def transcribe_voice(body: TranscribeRequest):
    """
    Transcribe a voice message from an audio URL.
    Called by Evolution API webhook when a WhatsApp voice message arrives.
    """
    result = await transcribe_audio_url(body.audio_url, language=body.language)

    if body.classify_intent and result.get("transcript"):
        intent_data = await classify_voice_intent(
            result["transcript"], body.sender_phone
        )
        result["intent"] = intent_data.get("intent")
        result["intent_confidence"] = intent_data.get("confidence")
        result["suggested_reply"] = intent_data.get("reply")

    if body.sender_phone and result.get("transcript"):
        await store_voice_interaction(
            phone=body.sender_phone,
            transcript=result["transcript"],
            intent=result.get("intent", "general"),
            language=result.get("language", "unknown"),
        )

    return result


@router.post("/webhooks/voice/call-ended", dependencies=[Depends(verify_voice_webhook_secret)])
async def call_ended(body: CallEndedRequest):
    """
    Process a completed call recording.
    Called by Calendly, Google Meet integration, or directly after a call.
    """
    return await process_call_recording(
        recording_url=body.recording_url,
        caller_name=body.caller_name,
        caller_phone=body.caller_phone,
        duration_seconds=body.duration_seconds,
        call_type=body.call_type,
    )


@router.post("/webhooks/voice/upload-transcribe", dependencies=[Depends(verify_voice_webhook_secret)])
async def upload_and_transcribe(file: UploadFile = File(...)):
    """Upload an audio file and return its transcript."""
    audio_bytes = await file.read()
    if len(audio_bytes) > 25 * 1024 * 1024:  # 25 MB Whisper limit
        from fastapi import HTTPException
        raise HTTPException(status_code=413, detail="Audio file exceeds 25 MB limit")
    return await transcribe_audio_bytes(audio_bytes, filename=file.filename or "audio.ogg")


@router.post("/api/v1/voice/send-note", dependencies=[Depends(get_current_captain)])
async def captain_send_voice_note(body: SendVoiceRequest):
    """Captain-only: send a custom voice note to any phone number."""
    return await send_voice_note(body.phone, body.text)


@router.post("/api/v1/voice/proposal-followup/{lead_id}", dependencies=[Depends(get_current_captain)])
async def proposal_voice_followup(lead_id: str):
    """Captain-only: send a proposal voice summary to the lead's phone."""
    return await send_proposal_voice_summary(lead_id)
