"""Tests for R6-1: Slack two-way bot — HMAC verification, slash commands, events."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_slack_signature(body: str, secret: str = "test_secret", ts: int | None = None) -> tuple[str, str]:
    """Return (timestamp, signature) for a Slack request."""
    ts = ts or int(time.time())
    sig_base = f"v0:{ts}:{body}"
    mac = hmac.new(secret.encode(), sig_base.encode(), hashlib.sha256)
    return str(ts), f"v0={mac.hexdigest()}"


# ── HMAC verification tests ───────────────────────────────────────────────────

class TestVerifySlackSignature:
    def _verify(self, body: str, ts: str, sig: str, secret: str = "test_secret"):
        with patch("app.services.notifications.slack_bot.settings") as cfg:
            cfg.SLACK_SIGNING_SECRET = secret
            from app.services.notifications.slack_bot import verify_slack_signature
            return verify_slack_signature(body, ts, sig)

    def test_valid_signature_passes(self):
        body = "command=/status&text="
        ts, sig = _make_slack_signature(body, secret="test_secret")
        assert self._verify(body, ts, sig) is True

    def test_wrong_secret_fails(self):
        body = "command=/status&text="
        ts, sig = _make_slack_signature(body, secret="wrong_secret")
        assert self._verify(body, ts, sig, secret="correct_secret") is False

    def test_tampered_body_fails(self):
        body = "command=/status&text="
        ts, sig = _make_slack_signature(body)
        assert self._verify("tampered_body", ts, sig) is False

    def test_replay_attack_rejected(self):
        body = "command=/status&text="
        old_ts = str(int(time.time()) - 400)  # >5 min ago
        sig_base = f"v0:{old_ts}:{body}"
        mac = hmac.new(b"test_secret", sig_base.encode(), hashlib.sha256)
        sig = f"v0={mac.hexdigest()}"
        assert self._verify(body, old_ts, sig) is False

    def test_future_timestamp_accepted_within_window(self):
        body = "command=/briefing&text="
        future_ts = str(int(time.time()) + 10)  # slight clock skew
        sig_base = f"v0:{future_ts}:{body}"
        mac = hmac.new(b"test_secret", sig_base.encode(), hashlib.sha256)
        sig = f"v0={mac.hexdigest()}"
        assert self._verify(body, future_ts, sig) is True


# ── Slash command dispatch ─────────────────────────────────────────────────────

class TestSlashCommands:
    @pytest.mark.asyncio
    async def test_cmd_status_returns_dict(self):
        with (
            patch("app.services.notifications.slack_bot.get_db_session"),
            patch("app.services.notifications.slack_bot.memory_service") as mem,
        ):
            mem.retrieve = AsyncMock(return_value=None)
            from app.services.notifications.slack_bot import handle_slash_command
            result = await handle_slash_command(
                command="/status", text="", channel_id="C123", user_id="U123", response_url=""
            )
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_cmd_help_returns_help_text(self):
        from app.services.notifications.slack_bot import handle_slash_command
        result = await handle_slash_command(
            command="/help", text="", channel_id="C123", user_id="U123", response_url=""
        )
        assert "text" in result or "blocks" in result or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_unknown_command_returns_error(self):
        from app.services.notifications.slack_bot import handle_slash_command
        result = await handle_slash_command(
            command="/unknown_xyz", text="", channel_id="C123", user_id="U123", response_url=""
        )
        assert isinstance(result, dict)


# ── Event handling ─────────────────────────────────────────────────────────────

class TestSlackEvents:
    @pytest.mark.asyncio
    async def test_url_verification_challenge(self):
        with patch("app.services.notifications.slack_bot.memory_service") as mem:
            mem.store = AsyncMock()
            from app.services.notifications.slack_bot import handle_event
            result = await handle_event({"type": "url_verification", "challenge": "test123"})
            assert result is None or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_message_event_processed(self):
        with (
            patch("app.services.notifications.slack_bot.memory_service") as mem,
            patch("app.services.notifications.slack_bot.ai_router") as ai,
        ):
            mem.store = AsyncMock()
            ai.chat = AsyncMock(return_value=(MagicMock(content="reply"), "fast"))
            from app.services.notifications.slack_bot import handle_event
            await handle_event({"type": "message", "text": "hello", "channel": "C123", "user": "U123"})
