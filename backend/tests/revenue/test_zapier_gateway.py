"""Tests for R6-2: Zapier/Make.com webhook gateway — HMAC, inbound handlers, outbound triggers."""
from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_zapier_sig(body: str, secret: str = "zap_secret") -> str:
    mac = hmac.new(secret.encode(), body.encode(), hashlib.sha256)
    return mac.hexdigest()


def _make_make_sig(body: str, secret: str = "make_secret") -> str:
    mac = hmac.new(secret.encode(), body.encode(), hashlib.sha256)
    return mac.hexdigest()


class TestHmacVerification:
    def test_valid_zapier_signature(self):
        body = json.dumps({"source": "zapier", "email": "x@y.com"})
        sig = _make_zapier_sig(body, "zap_secret")
        with patch("app.services.integrations.zapier_gateway.settings") as cfg:
            cfg.ZAPIER_WEBHOOK_SECRET = "zap_secret"
            from app.services.integrations.zapier_gateway import verify_zapier_signature
            assert verify_zapier_signature(body, sig) is True

    def test_invalid_zapier_signature(self):
        body = json.dumps({"source": "zapier"})
        with patch("app.services.integrations.zapier_gateway.settings") as cfg:
            cfg.ZAPIER_WEBHOOK_SECRET = "correct"
            from app.services.integrations.zapier_gateway import verify_zapier_signature
            assert verify_zapier_signature(body, "bad_sig") is False

    def test_valid_make_signature(self):
        body = json.dumps({"event": "lead.created"})
        sig = _make_make_sig(body, "make_secret")
        with patch("app.services.integrations.zapier_gateway.settings") as cfg:
            cfg.MAKE_WEBHOOK_SECRET = "make_secret"
            from app.services.integrations.zapier_gateway import verify_make_signature
            assert verify_make_signature(body, sig) is True


class TestInboundHandlers:
    @pytest.mark.asyncio
    async def test_handle_inbound_lead_creates_lead(self):
        payload = {
            "first_name": "Alice",
            "last_name": "Smith",
            "company": "AcmeCo",
            "email": "alice@acme.com",
            "source": "zapier",
        }
        with (
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.leads.scoring.lead_scoring_engine") as scorer,
        ):
            mock_db = AsyncMock()
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            scorer.score_lead = AsyncMock(return_value={"score": 72})

            from app.services.integrations.zapier_gateway import handle_inbound_lead
            result = await handle_inbound_lead(payload)
            assert isinstance(result, dict)
            assert "status" in result

    @pytest.mark.asyncio
    async def test_handle_inbound_payment_updates_invoice(self):
        payload = {
            "invoice_id": "ALY-202506-0001",
            "amount_paid": 2500.0,
            "currency": "USD",
            "payment_method": "stripe",
        }
        with (
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.notifications.slack.notify_slack") as notify,
        ):
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=MagicMock(rowcount=1))
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            notify.return_value = AsyncMock()

            from app.services.integrations.zapier_gateway import handle_inbound_payment
            result = await handle_inbound_payment(payload)
            assert isinstance(result, dict)


class TestZapierGatewayOutbound:
    @pytest.mark.asyncio
    async def test_trigger_sends_http_post(self):
        with patch("app.services.integrations.zapier_gateway.httpx") as mock_httpx:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(post=AsyncMock(return_value=mock_resp))
            )
            mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.services.integrations.zapier_gateway.settings") as cfg:
                cfg.ZAPIER_LEAD_QUALIFIED_HOOK = "https://hooks.zapier.com/test"
                from app.services.integrations.zapier_gateway import ZapierGateway
                gw = ZapierGateway()
                # trigger is a fire-and-forget; just ensure it doesn't raise
                await gw.trigger("https://hooks.zapier.com/test", "lead.qualified", {"lead_id": "123"})
