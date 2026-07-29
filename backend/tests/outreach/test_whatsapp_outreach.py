"""Multi-channel outreach: WhatsApp send flow (Captain directive — SES + WhatsApp
both must actually send, not just exist as dead code). Locks in:
  - OutreachEngine.send_whatsapp_to_lead requires lead.phone
  - do-not-contact is checked against the lead's EMAIL (the DNC table is
    email-keyed; passing a phone number there would silently never match)
  - outreach_paused blocks the send
  - a successful send updates lead.status/outreach_count and logs an
    OutreachLog row with channel=WHATSAPP
  - _send_via_whatsapp calls communication.whatsapp_transport.send_text with
    the real (db, tenant_id=, number=, text=, lead_id=) signature, not a
    two-positional-arg shape
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.lead import Lead, LeadStatus
from app.models.outreach import OutreachChannel, OutreachStatus
from app.services.outreach.engine import OutreachEngine, _send_via_whatsapp


def _make_lead(**overrides) -> Lead:
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        company_name="Acme Corp",
        contact_name="Jane Doe",
        email="jane@acme.com",
        contact_email=None,
        phone="+15551234567",
        status=LeadStatus.NEW,
        outreach_count=0,
        enrichment_data={},
    )
    defaults.update(overrides)
    return Lead(**defaults)


class TestSendViaWhatsapp:
    @pytest.mark.asyncio
    async def test_calls_send_text_with_correct_kwargs(self):
        session = AsyncMock()
        tenant_id = uuid.uuid4()
        lead_id = uuid.uuid4()

        with patch(
            "app.services.communication.whatsapp_transport.send_text",
            new_callable=AsyncMock,
            return_value={"sent": True, "event_id": "evt-123", "transport": {}},
        ) as mock_send:
            success, result = await _send_via_whatsapp(session, tenant_id, "+15551234567", "Hello there", lead_id=lead_id)

        assert success is True
        assert result == "evt-123"
        mock_send.assert_awaited_once()
        _, kwargs = mock_send.call_args
        assert kwargs["tenant_id"] == tenant_id
        assert kwargs["number"] == "+15551234567"
        assert kwargs["text"] == "Hello there"
        assert kwargs["lead_id"] == lead_id

    @pytest.mark.asyncio
    async def test_returns_false_when_transport_reports_not_sent(self):
        session = AsyncMock()
        with patch(
            "app.services.communication.whatsapp_transport.send_text",
            new_callable=AsyncMock,
            return_value={"sent": False, "event_id": "evt-456", "transport": {}},
        ):
            success, error = await _send_via_whatsapp(session, uuid.uuid4(), "+15551234567", "Hi", lead_id=None)
        assert success is False
        assert error == "evolution_send_failed"

    @pytest.mark.asyncio
    async def test_exception_from_transport_is_caught(self):
        session = AsyncMock()
        with patch(
            "app.services.communication.whatsapp_transport.send_text",
            new_callable=AsyncMock,
            side_effect=RuntimeError("evolution unreachable"),
        ):
            success, error = await _send_via_whatsapp(session, uuid.uuid4(), "+15551234567", "Hi")
        assert success is False
        assert "evolution unreachable" in error


class TestSendWhatsappToLead:
    @pytest.mark.asyncio
    async def test_fails_fast_when_lead_has_no_phone(self):
        engine = OutreachEngine()
        lead = _make_lead(phone=None)
        tenant_id = lead.tenant_id

        fake_session = AsyncMock()

        class _Ctx:
            async def __aenter__(self):
                return None
            async def __aexit__(self, *a):
                return False
        fake_session.begin = MagicMock(return_value=_Ctx())

        with (
            patch("app.services.outreach.engine.AsyncSessionLocal") as db_ctx,
            patch("app.services.outreach.engine.set_tenant_context", new_callable=AsyncMock),
            patch.object(engine, "_get_lead", new_callable=AsyncMock, return_value=lead),
        ):
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=fake_session)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await engine.send_whatsapp_to_lead(lead.id, tenant_id)

        assert result == {"success": False, "error": "phone_not_set"}

    @pytest.mark.asyncio
    async def test_blocked_when_outreach_paused(self):
        engine = OutreachEngine()
        lead = _make_lead()
        fake_session = AsyncMock()

        class _Ctx:
            async def __aenter__(self):
                return None
            async def __aexit__(self, *a):
                return False
        fake_session.begin = MagicMock(return_value=_Ctx())

        with (
            patch("app.services.outreach.engine.AsyncSessionLocal") as db_ctx,
            patch("app.services.outreach.engine.set_tenant_context", new_callable=AsyncMock),
            patch.object(engine, "_get_lead", new_callable=AsyncMock, return_value=lead),
            patch(
                "app.services.outreach.compliance.outreach_compliance.is_outreach_paused",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=fake_session)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await engine.send_whatsapp_to_lead(lead.id, lead.tenant_id)

        assert result == {"success": False, "error": "outreach_paused"}

    @pytest.mark.asyncio
    async def test_blocked_when_lead_email_is_do_not_contact(self):
        engine = OutreachEngine()
        lead = _make_lead(email="dnc@acme.com")
        fake_session = AsyncMock()

        class _Ctx:
            async def __aenter__(self):
                return None
            async def __aexit__(self, *a):
                return False
        fake_session.begin = MagicMock(return_value=_Ctx())

        with (
            patch("app.services.outreach.engine.AsyncSessionLocal") as db_ctx,
            patch("app.services.outreach.engine.set_tenant_context", new_callable=AsyncMock),
            patch.object(engine, "_get_lead", new_callable=AsyncMock, return_value=lead),
            patch(
                "app.services.outreach.compliance.outreach_compliance.is_outreach_paused",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.services.outreach.compliance.outreach_compliance.is_do_not_contact",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_dnc,
        ):
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=fake_session)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await engine.send_whatsapp_to_lead(lead.id, lead.tenant_id)

        assert result == {"success": False, "error": "do_not_contact"}
        # DNC must be checked against the EMAIL, never the phone number
        # (DoNotContact is an email-keyed table).
        _, called_email = mock_dnc.call_args[0][1], mock_dnc.call_args[0][2]
        assert called_email == "dnc@acme.com"

    @pytest.mark.asyncio
    async def test_successful_send_updates_lead_and_logs_outreach(self):
        engine = OutreachEngine()
        lead = _make_lead()
        fake_session = AsyncMock()

        class _Ctx:
            async def __aenter__(self):
                return None
            async def __aexit__(self, *a):
                return False
        fake_session.begin = MagicMock(return_value=_Ctx())
        fake_session.add = MagicMock()
        fake_session.flush = AsyncMock()

        with (
            patch("app.services.outreach.engine.AsyncSessionLocal") as db_ctx,
            patch("app.services.outreach.engine.set_tenant_context", new_callable=AsyncMock),
            patch.object(engine, "_get_lead", new_callable=AsyncMock, return_value=lead),
            patch.object(engine, "_audit", new_callable=AsyncMock),
            patch(
                "app.services.outreach.compliance.outreach_compliance.is_outreach_paused",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.services.outreach.compliance.outreach_compliance.is_do_not_contact",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.services.outreach.engine._send_via_whatsapp",
                new_callable=AsyncMock,
                return_value=(True, "evt-789"),
            ),
        ):
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=fake_session)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await engine.send_whatsapp_to_lead(lead.id, lead.tenant_id, message="Custom message")

        assert result["success"] is True
        assert result["channel"] == "whatsapp"
        assert result["message_id"] == "evt-789"
        assert lead.status == LeadStatus.CONTACTED
        assert lead.outreach_count == 1
        assert lead.last_contact is not None

        # One OutreachLog row added with the WHATSAPP channel and custom message.
        assert fake_session.add.call_count == 1
        added_log = fake_session.add.call_args[0][0]
        assert added_log.channel == OutreachChannel.WHATSAPP
        assert added_log.body_text == "Custom message"
        assert added_log.status == OutreachStatus.SENT

    @pytest.mark.asyncio
    async def test_falls_back_to_generated_message_when_none_given(self):
        engine = OutreachEngine()
        lead = _make_lead()
        fake_session = AsyncMock()

        class _Ctx:
            async def __aenter__(self):
                return None
            async def __aexit__(self, *a):
                return False
        fake_session.begin = MagicMock(return_value=_Ctx())
        fake_session.add = MagicMock()
        fake_session.flush = AsyncMock()

        with (
            patch("app.services.outreach.engine.AsyncSessionLocal") as db_ctx,
            patch("app.services.outreach.engine.set_tenant_context", new_callable=AsyncMock),
            patch.object(engine, "_get_lead", new_callable=AsyncMock, return_value=lead),
            patch.object(engine, "_audit", new_callable=AsyncMock),
            patch.object(engine, "_generate_steps_with_ai", new_callable=AsyncMock, return_value=[]),
            patch(
                "app.services.outreach.compliance.outreach_compliance.is_outreach_paused",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.services.outreach.compliance.outreach_compliance.is_do_not_contact",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.services.outreach.engine._send_via_whatsapp",
                new_callable=AsyncMock,
                return_value=(True, "evt-000"),
            ),
        ):
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=fake_session)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await engine.send_whatsapp_to_lead(lead.id, lead.tenant_id)

        assert result["success"] is True
        added_log = fake_session.add.call_args[0][0]
        assert "Aliyar Solutions" in added_log.body_text
        assert lead.company_name in added_log.body_text

    @pytest.mark.asyncio
    async def test_failed_send_does_not_mark_lead_contacted(self):
        engine = OutreachEngine()
        lead = _make_lead()
        fake_session = AsyncMock()

        class _Ctx:
            async def __aenter__(self):
                return None
            async def __aexit__(self, *a):
                return False
        fake_session.begin = MagicMock(return_value=_Ctx())
        fake_session.add = MagicMock()
        fake_session.flush = AsyncMock()

        with (
            patch("app.services.outreach.engine.AsyncSessionLocal") as db_ctx,
            patch("app.services.outreach.engine.set_tenant_context", new_callable=AsyncMock),
            patch.object(engine, "_get_lead", new_callable=AsyncMock, return_value=lead),
            patch.object(engine, "_audit", new_callable=AsyncMock),
            patch(
                "app.services.outreach.compliance.outreach_compliance.is_outreach_paused",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.services.outreach.compliance.outreach_compliance.is_do_not_contact",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.services.outreach.engine._send_via_whatsapp",
                new_callable=AsyncMock,
                return_value=(False, "evolution_send_failed"),
            ),
        ):
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=fake_session)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await engine.send_whatsapp_to_lead(lead.id, lead.tenant_id, message="Hi")

        assert result["success"] is False
        assert lead.status == LeadStatus.NEW
        assert lead.outreach_count == 0
        added_log = fake_session.add.call_args[0][0]
        assert added_log.status == OutreachStatus.BOUNCED
