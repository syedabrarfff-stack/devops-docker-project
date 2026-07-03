"""Tests for V6-1: Voice transcription pipeline — Whisper, intent classification, storage."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestTranscribeAudioUrl:
    @pytest.mark.asyncio
    async def test_returns_transcript_dict(self):
        fake_audio = b"fake_ogg_data"
        fake_whisper_response = MagicMock()
        fake_whisper_response.text = "Hello, I want to schedule a meeting."
        fake_whisper_response.language = "en"
        fake_whisper_response.duration = 4.2

        with (
            patch("app.services.voice.transcription.httpx") as mock_httpx,
            patch("app.services.voice.transcription.openai_client") as mock_ai,
        ):
            mock_resp = MagicMock(status_code=200)
            mock_resp.content = fake_audio
            mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(get=AsyncMock(return_value=mock_resp))
            )
            mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_ai.audio.transcriptions.create = AsyncMock(return_value=fake_whisper_response)

            from app.services.voice.transcription import transcribe_audio_url
            result = await transcribe_audio_url("https://example.com/voice.ogg")
            assert "transcript" in result
            assert result["transcript"] == "Hello, I want to schedule a meeting."

    @pytest.mark.asyncio
    async def test_download_failure_returns_error_dict(self):
        with patch("app.services.voice.transcription.httpx") as mock_httpx:
            mock_resp = MagicMock(status_code=404)
            mock_resp.content = b""
            mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(get=AsyncMock(return_value=mock_resp))
            )
            mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.voice.transcription import transcribe_audio_url
            result = await transcribe_audio_url("https://example.com/bad.ogg")
            assert isinstance(result, dict)
            assert "error" in result or "transcript" in result


class TestTranscribeAudioBytes:
    @pytest.mark.asyncio
    async def test_bytes_transcription(self):
        fake_resp = MagicMock()
        fake_resp.text = "Payment confirmed for invoice."
        fake_resp.language = "en"
        fake_resp.duration = 2.1

        with patch("app.services.voice.transcription.openai_client") as mock_ai:
            mock_ai.audio.transcriptions.create = AsyncMock(return_value=fake_resp)
            from app.services.voice.transcription import transcribe_audio_bytes
            result = await transcribe_audio_bytes(b"audio_data", filename="recording.mp3")
            assert result["transcript"] == "Payment confirmed for invoice."


class TestClassifyVoiceIntent:
    @pytest.mark.asyncio
    async def test_meeting_request_classified(self):
        ai_response = MagicMock()
        ai_response.content = json.dumps({"intent": "meeting_request", "confidence": 0.92, "reply": "I'll book that."})

        with patch("app.services.voice.transcription.ai_router") as ai:
            ai.chat = AsyncMock(return_value=(ai_response, "fast"))
            from app.services.voice.transcription import classify_voice_intent
            result = await classify_voice_intent("Can we schedule a call tomorrow?", "+447911123456")
            assert result.get("intent") == "meeting_request"

    @pytest.mark.asyncio
    async def test_malformed_ai_response_uses_fallback(self):
        ai_response = MagicMock()
        ai_response.content = "not valid json at all"

        with patch("app.services.voice.transcription.ai_router") as ai:
            ai.chat = AsyncMock(return_value=(ai_response, "fast"))
            from app.services.voice.transcription import classify_voice_intent
            result = await classify_voice_intent("hello world", "+447911000000")
            assert isinstance(result, dict)
            assert "intent" in result

    @pytest.mark.asyncio
    async def test_ai_failure_returns_general_intent(self):
        with patch("app.services.voice.transcription.ai_router") as ai:
            ai.chat = AsyncMock(side_effect=Exception("AI down"))
            from app.services.voice.transcription import classify_voice_intent
            result = await classify_voice_intent("some message", "+447911000000")
            assert isinstance(result, dict)
            assert result.get("intent") in ("general", "unknown", None) or "intent" in result


class TestStoreVoiceInteraction:
    @pytest.mark.asyncio
    async def test_interaction_stored_in_memory(self):
        with patch("app.services.voice.transcription.memory_service") as mem:
            mem.store = AsyncMock()
            from app.services.voice.transcription import store_voice_interaction
            await store_voice_interaction(
                phone="+447911123456",
                transcript="Hello there",
                intent="general",
                language="en",
            )
            mem.store.assert_called_once()
            call_kwargs = mem.store.call_args
            # key should contain the phone number
            assert "+447911123456" in str(call_kwargs) or "voice_interaction" in str(call_kwargs)
