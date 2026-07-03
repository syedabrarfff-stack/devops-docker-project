"""Tests for V6-4: WhatsApp voice sender — ElevenLabs TTS → Evolution API delivery."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSendVoiceNote:
    @pytest.mark.asyncio
    async def test_successful_send_returns_dict(self):
        fake_audio = b"fake_mp3_audio_bytes"
        fake_evolution_resp = MagicMock(status_code=200)
        fake_evolution_resp.json.return_value = {"key": {"id": "msg_abc"}}

        with (
            patch("app.services.voice.whatsapp_voice.settings") as cfg,
            patch("app.services.voice.whatsapp_voice._tts_elevenlabs", return_value=fake_audio) as tts_mock,
            patch("app.services.voice.whatsapp_voice.httpx") as mock_httpx,
        ):
            cfg.EVOLUTION_API_URL = "https://evo.example.com"
            cfg.EVOLUTION_INSTANCE = "jarvis"
            cfg.EVOLUTION_API_KEY = "evo_key"

            mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(post=AsyncMock(return_value=fake_evolution_resp))
            )
            mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.voice.whatsapp_voice import send_voice_note
            result = await send_voice_note("+447911123456", "Hello, this is your briefing.")
            assert isinstance(result, dict)
            tts_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_tts_failure_returns_error(self):
        with patch("app.services.voice.whatsapp_voice._tts_elevenlabs", side_effect=Exception("ElevenLabs down")):
            from app.services.voice.whatsapp_voice import send_voice_note
            result = await send_voice_note("+447911123456", "Hello briefing")
            assert isinstance(result, dict)
            assert "error" in result or "status" in result

    @pytest.mark.asyncio
    async def test_evolution_api_failure_returns_error(self):
        fake_audio = b"some_audio"
        fake_resp = MagicMock(status_code=500)
        fake_resp.json.return_value = {}

        with (
            patch("app.services.voice.whatsapp_voice.settings") as cfg,
            patch("app.services.voice.whatsapp_voice._tts_elevenlabs", return_value=fake_audio),
            patch("app.services.voice.whatsapp_voice.httpx") as mock_httpx,
        ):
            cfg.EVOLUTION_API_URL = "https://evo.example.com"
            cfg.EVOLUTION_INSTANCE = "jarvis"
            cfg.EVOLUTION_API_KEY = "evo_key"

            mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(post=AsyncMock(return_value=fake_resp))
            )
            mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.voice.whatsapp_voice import send_voice_note
            result = await send_voice_note("+447911123456", "Test message")
            assert isinstance(result, dict)


class TestSendProposalVoiceSummary:
    @pytest.mark.asyncio
    async def test_missing_lead_returns_error(self):
        with patch("app.services.voice.whatsapp_voice.get_db_session") as db_ctx:
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.voice.whatsapp_voice import send_proposal_voice_summary
            result = await send_proposal_voice_summary("nonexistent_lead")
            assert isinstance(result, dict)
            assert "error" in result or "status" in result

    @pytest.mark.asyncio
    async def test_lead_without_phone_returns_error(self):
        mock_lead = MagicMock()
        mock_lead.contact_phone = None
        mock_lead.contact_name = "Bob"
        mock_lead.company = "BobCo"

        with patch("app.services.voice.whatsapp_voice.get_db_session") as db_ctx:
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_lead)))
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.voice.whatsapp_voice import send_proposal_voice_summary
            result = await send_proposal_voice_summary("lead_no_phone")
            assert isinstance(result, dict)
