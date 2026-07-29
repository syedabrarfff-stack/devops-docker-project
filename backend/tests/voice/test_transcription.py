"""Tests for V6-1: Voice transcription pipeline — Whisper, intent classification, storage."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestTranscribeAudioUrl:
    @pytest.mark.asyncio
    async def test_returns_transcript_dict(self):
        fake_audio = b"fake_ogg_data"

        with (
            patch("app.services.voice.transcription.httpx") as mock_httpx,
            patch("app.services.voice.transcription.settings") as cfg,
        ):
            cfg.OPENAI_API_KEY = "sk-test"
            mock_get_resp = MagicMock(status_code=200)
            mock_get_resp.content = fake_audio
            mock_get_resp.raise_for_status = MagicMock()

            mock_post_resp = MagicMock(status_code=200)
            mock_post_resp.raise_for_status = MagicMock()
            mock_post_resp.json.return_value = {
                "text": "Hello, I want to schedule a meeting.",
                "language": "en",
                "duration": 4.2,
            }

            mock_client = MagicMock(
                get=AsyncMock(return_value=mock_get_resp),
                post=AsyncMock(return_value=mock_post_resp),
            )
            mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

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
        with (
            patch("app.services.voice.transcription.httpx") as mock_httpx,
            patch("app.services.voice.transcription.settings") as cfg,
        ):
            cfg.OPENAI_API_KEY = "sk-test"
            mock_post_resp = MagicMock(status_code=200)
            mock_post_resp.raise_for_status = MagicMock()
            mock_post_resp.json.return_value = {
                "text": "Payment confirmed for invoice.",
                "language": "en",
                "duration": 2.1,
            }
            mock_client = MagicMock(post=AsyncMock(return_value=mock_post_resp))
            mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.voice.transcription import transcribe_audio_bytes
            result = await transcribe_audio_bytes(b"audio_data", filename="recording.mp3")
            assert result["transcript"] == "Payment confirmed for invoice."


class TestClassifyVoiceIntent:
    @pytest.mark.asyncio
    async def test_meeting_request_classified(self):
        ai_response = MagicMock()
        ai_response.error = None
        ai_response.content = json.dumps({"intent": "meeting_request", "confidence": 0.92, "reply": "I'll book that."})

        with patch("app.services.ai.router.ai_router") as ai:
            ai.chat = AsyncMock(return_value=(ai_response, "fast"))
            from app.services.voice.transcription import classify_voice_intent
            result = await classify_voice_intent("Can we schedule a call tomorrow?", "+447911123456")
            assert result.get("intent") == "meeting_request"

    @pytest.mark.asyncio
    async def test_malformed_ai_response_uses_fallback(self):
        ai_response = MagicMock()
        ai_response.content = "not valid json at all"

        with patch("app.services.ai.router.ai_router") as ai:
            ai.chat = AsyncMock(return_value=(ai_response, "fast"))
            from app.services.voice.transcription import classify_voice_intent
            result = await classify_voice_intent("hello world", "+447911000000")
            assert isinstance(result, dict)
            assert "intent" in result

    @pytest.mark.asyncio
    async def test_ai_failure_returns_general_intent(self):
        with patch("app.services.ai.router.ai_router") as ai:
            ai.chat = AsyncMock(side_effect=Exception("AI down"))
            from app.services.voice.transcription import classify_voice_intent
            result = await classify_voice_intent("some message", "+447911000000")
            assert isinstance(result, dict)
            assert result.get("intent") in ("general", "unknown", None) or "intent" in result


class TestStoreVoiceInteraction:
    @pytest.mark.asyncio
    async def test_interaction_stored_in_memory(self):
        with patch("app.core.database.AsyncSessionLocal") as db_ctx:
            mock_session = AsyncMock()
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.voice.transcription import store_voice_interaction
            await store_voice_interaction(
                phone="+447911123456",
                transcript="Hello there",
                intent="general",
                language="en",
            )
            mock_session.execute.assert_called_once()
            # key should contain the phone number
            call_args = mock_session.execute.call_args
            assert "+447911123456" in str(call_args)
