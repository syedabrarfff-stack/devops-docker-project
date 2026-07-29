"""Tests for V6-2: ElevenLabs TTS → Telegram voice briefing delivery."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestTtsElevenLabs:
    @pytest.mark.asyncio
    async def test_returns_audio_bytes(self):
        fake_audio = b"\xff\xfb\x90\x00" * 512  # fake MP3 header-ish bytes

        with (
            patch("app.services.voice.briefing_voice.settings") as cfg,
            patch("app.services.voice.briefing_voice.httpx") as mock_httpx,
        ):
            cfg.ELEVENLABS_API_KEY = "el_test_key"
            cfg.ELEVENLABS_VOICE_ID = "voice_abc"

            mock_resp = MagicMock(status_code=200)
            mock_resp.content = fake_audio
            mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(post=AsyncMock(return_value=mock_resp))
            )
            mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.voice.briefing_voice import _tts_elevenlabs
            result = await _tts_elevenlabs("Good morning Captain.")
            assert isinstance(result, bytes)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_api_error_returns_none(self):
        with (
            patch("app.services.voice.briefing_voice.settings") as cfg,
            patch("app.services.voice.briefing_voice.httpx") as mock_httpx,
        ):
            cfg.ELEVENLABS_API_KEY = "el_test_key"
            cfg.ELEVENLABS_VOICE_ID = "voice_abc"

            mock_resp = MagicMock(status_code=429)
            mock_resp.content = b""
            mock_resp.text = "rate limited"
            mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(post=AsyncMock(return_value=mock_resp))
            )
            mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.voice.briefing_voice import _tts_elevenlabs
            # Non-200 is handled (logged + returns None), not raised — the
            # caller (deliver_briefing_as_voice) treats voice delivery as
            # non-fatal so text briefings still go out.
            result = await _tts_elevenlabs("Morning briefing text")
            assert result is None


class TestSendTelegramVoice:
    @pytest.mark.asyncio
    async def test_sends_to_telegram(self):
        fake_audio = b"audio_data"
        with (
            patch("app.services.voice.briefing_voice.settings") as cfg,
            patch("app.services.voice.briefing_voice.httpx") as mock_httpx,
        ):
            cfg.TELEGRAM_BOT_TOKEN = "12345:bot_token"
            cfg.TELEGRAM_CHAT_ID = "-100123456"

            mock_resp = MagicMock(status_code=200)
            mock_resp.json.return_value = {"ok": True, "result": {"message_id": 42}}
            mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(post=AsyncMock(return_value=mock_resp))
            )
            mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.voice.briefing_voice import _send_telegram_voice
            result = await _send_telegram_voice(fake_audio, caption="Morning Briefing")
            assert result is True


class TestDeliverBriefingAsVoice:
    @pytest.mark.asyncio
    async def test_long_text_is_truncated_to_800_chars(self):
        long_text = "A" * 1500
        captured = []

        async def fake_tts(text, voice_id=None):
            captured.append(text)
            return b"audio"

        with (
            patch("app.services.voice.briefing_voice._tts_elevenlabs", side_effect=fake_tts),
            patch("app.services.voice.briefing_voice._send_telegram_voice", return_value={"ok": True}),
        ):
            from app.services.voice.briefing_voice import deliver_briefing_as_voice
            await deliver_briefing_as_voice(long_text)
            assert len(captured[0]) <= 800

    @pytest.mark.asyncio
    async def test_short_text_passes_through(self):
        text = "Short morning briefing for Captain."
        captured = []

        async def fake_tts(text, voice_id=None):
            captured.append(text)
            return b"audio"

        with (
            patch("app.services.voice.briefing_voice._tts_elevenlabs", side_effect=fake_tts),
            patch("app.services.voice.briefing_voice._send_telegram_voice", return_value={"ok": True}),
        ):
            from app.services.voice.briefing_voice import deliver_briefing_as_voice
            await deliver_briefing_as_voice(text)
            assert captured[0] == text
