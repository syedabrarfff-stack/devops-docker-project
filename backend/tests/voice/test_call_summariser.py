"""Tests for V6-3: Call recording summariser — transcription, AI summary, lead update."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGenerateCallSummary:
    @pytest.mark.asyncio
    async def test_returns_structured_summary(self):
        ai_payload = {
            "summary": "Prospect interested in cloud infrastructure services.",
            "outcome": "interested",
            "next_action": "Send proposal by Friday.",
            "key_points": ["Budget £5k/month", "AWS migration", "Timeline Q3"],
            "sentiment": "positive",
        }
        ai_response = MagicMock(content=json.dumps(ai_payload))

        with patch("app.services.voice.call_summariser.ai_router") as ai:
            ai.chat = AsyncMock(return_value=(ai_response, "analysis"))
            from app.services.voice.call_summariser import _generate_call_summary
            result = await _generate_call_summary(
                transcript="We discussed AWS migration...",
                caller_name="John Doe",
                call_type="inbound",
                duration_s=360,
            )
            assert result["outcome"] == "interested"
            assert "next_action" in result
            assert "key_points" in result

    @pytest.mark.asyncio
    async def test_malformed_json_uses_fallback(self):
        ai_response = MagicMock(content="Summary: Great call. Outcome: needs_follow_up")

        with patch("app.services.voice.call_summariser.ai_router") as ai:
            ai.chat = AsyncMock(return_value=(ai_response, "analysis"))
            from app.services.voice.call_summariser import _generate_call_summary
            result = await _generate_call_summary(
                transcript="Something happened on the call.",
                caller_name="Jane",
                call_type="outbound",
                duration_s=120,
            )
            assert isinstance(result, dict)
            assert "summary" in result or "outcome" in result

    @pytest.mark.asyncio
    async def test_ai_failure_returns_error_dict(self):
        with patch("app.services.voice.call_summariser.ai_router") as ai:
            ai.chat = AsyncMock(side_effect=Exception("timeout"))
            from app.services.voice.call_summariser import _generate_call_summary
            result = await _generate_call_summary("transcript", "Caller", "inbound", 60)
            assert isinstance(result, dict)


class TestProcessCallRecording:
    @pytest.mark.asyncio
    async def test_full_pipeline_runs(self):
        fake_transcript_result = {
            "transcript": "Hi, I'm interested in your AI automation services.",
            "language": "en",
            "duration_s": 180,
        }
        fake_summary = {
            "summary": "Lead interested in AI automation.",
            "outcome": "interested",
            "next_action": "Schedule demo.",
            "key_points": ["AI automation", "Budget approved"],
            "sentiment": "positive",
        }

        with (
            patch("app.services.voice.call_summariser.transcribe_audio_url", return_value=fake_transcript_result),
            patch("app.services.voice.call_summariser._generate_call_summary", return_value=fake_summary) as gen_mock,
            patch("app.services.voice.call_summariser.get_db_session") as db_ctx,
            patch("app.services.voice.call_summariser.memory_service") as mem,
        ):
            mock_db = AsyncMock()
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mem.store = AsyncMock()

            from app.services.voice.call_summariser import process_call_recording
            result = await process_call_recording(
                recording_url="https://example.com/call.mp3",
                caller_name="Prospect A",
                caller_phone="+447911123456",
                duration_seconds=180,
                call_type="inbound",
            )
            assert isinstance(result, dict)
            gen_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcription_failure_returns_error(self):
        with patch(
            "app.services.voice.call_summariser.transcribe_audio_url",
            return_value={"error": "download_failed"},
        ):
            from app.services.voice.call_summariser import process_call_recording
            result = await process_call_recording(
                recording_url="https://bad.url/call.mp3",
                caller_name="Unknown",
                caller_phone="",
                duration_seconds=0,
                call_type="inbound",
            )
            assert isinstance(result, dict)
