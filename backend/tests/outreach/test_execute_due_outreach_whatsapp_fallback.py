"""execute_due_outreach previously returned 0 and audited
'outreach_execute_blocked_email_not_live' for the ENTIRE tenant whenever SES
wasn't in live send mode — even for leads that only have a phone number and
were always going to go out over WhatsApp, not email. That's the exact bug
behind "outreach is having SES and WhatsApp both, I want that to work also":
WhatsApp-only leads never got a chance because the email gate short-circuited
before the per-lead loop ever ran.

Fix: the email-liveness check moved from a blanket up-front return to a
per-lead gate that only applies to leads actually being emailed. Phone-only
leads now fall back to WhatsApp regardless of SES status.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.lead import Lead, LeadStatus
from app.models.outreach import FollowUpQueue, FollowUpStatus, OutreachChannel, OutreachStatus
from app.services.outreach.engine import OutreachEngine


def _make_lead(**overrides) -> Lead:
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        company_name="Acme Corp",
        contact_name="Jane Doe",
        email=None,
        contact_email=None,
        phone="+15551234567",
        status=LeadStatus.NEW,
        outreach_count=0,
        outreach_sent=False,
        enrichment_data={"outreach_sequence": [{"step": 1, "subject": "Hi", "body": "Quick question about your ops."}]},
    )
    defaults.update(overrides)
    return Lead(**defaults)


def _make_queue_item(lead_id, step=1) -> FollowUpQueue:
    return FollowUpQueue(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        lead_id=lead_id,
        sequence_step=step,
        status=FollowUpStatus.PENDING,
        scheduled_at=datetime.now(UTC),
    )


class _NoopCtx:
    async def __aenter__(self):
        return None

    async def __aexit__(self, *a):
        return False


def _fake_session(due_items, leads):
    session = AsyncMock()
    session.begin = MagicMock(return_value=_NoopCtx())
    session.add = MagicMock()
    session.flush = AsyncMock()

    due_result = MagicMock()
    due_result.scalars.return_value.all.return_value = due_items
    leads_result = MagicMock()
    leads_result.scalars.return_value.all.return_value = leads
    session.execute = AsyncMock(side_effect=[due_result, leads_result])
    return session


class TestExecuteDueOutreachWhatsappFallback:
    @pytest.mark.asyncio
    async def test_phone_only_lead_sends_via_whatsapp_even_when_ses_not_live(self):
        engine = OutreachEngine()
        lead = _make_lead()
        item = _make_queue_item(lead.id)
        tenant_id = uuid.uuid4()
        session = _fake_session([item], [lead])

        with (
            patch("app.services.outreach.engine.AsyncSessionLocal") as db_ctx,
            patch("app.services.outreach.engine.set_tenant_context", new_callable=AsyncMock),
            patch("app.core.config.settings.AUTO_SEND_OUTREACH", True),
            patch(
                "app.services.outreach.gmail.email_delivery_status",
                new_callable=AsyncMock,
                return_value={"send_mode": "sandbox", "blocker_code": "ses_sandbox_mode", "required_action": "..."},
            ),
            patch.object(engine, "_audit", new_callable=AsyncMock),
            patch(
                "app.services.outreach.engine._send_via_whatsapp",
                new_callable=AsyncMock,
                return_value=(True, "evt-abc"),
            ) as mock_wa_send,
        ):
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            sent = await engine.execute_due_outreach(tenant_id)

        # The WhatsApp fallback fired despite SES being in sandbox mode.
        mock_wa_send.assert_awaited_once()
        assert sent == 1
        assert item.status == FollowUpStatus.EXECUTED
        assert lead.status == LeadStatus.CONTACTED
        assert lead.outreach_count == 1

        added_log = session.add.call_args_list[0][0][0]
        assert added_log.channel == OutreachChannel.WHATSAPP
        assert added_log.status == OutreachStatus.SENT

    @pytest.mark.asyncio
    async def test_email_lead_is_deferred_not_dropped_when_ses_not_live(self):
        """A lead WITH an email should be politely rescheduled (PENDING), not
        silently lost, when SES isn't live — distinct from the old behavior
        of returning 0 for the whole tenant with no per-lead record at all."""
        engine = OutreachEngine()
        lead = _make_lead(phone=None, email="jane@acme.com")
        item = _make_queue_item(lead.id)
        tenant_id = uuid.uuid4()
        session = _fake_session([item], [lead])

        with (
            patch("app.services.outreach.engine.AsyncSessionLocal") as db_ctx,
            patch("app.services.outreach.engine.set_tenant_context", new_callable=AsyncMock),
            patch("app.core.config.settings.AUTO_SEND_OUTREACH", True),
            patch(
                "app.services.outreach.gmail.email_delivery_status",
                new_callable=AsyncMock,
                return_value={"send_mode": "sandbox", "blocker_code": "ses_sandbox_mode", "required_action": "..."},
            ),
            patch.object(engine, "_audit", new_callable=AsyncMock) as mock_audit,
        ):
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            sent = await engine.execute_due_outreach(tenant_id)

        assert sent == 0
        assert item.status == FollowUpStatus.PENDING
        audited_actions = [call.args[2] for call in mock_audit.call_args_list]
        assert "outreach_execute_blocked_email_not_live" in audited_actions

    @pytest.mark.asyncio
    async def test_lead_with_no_email_and_no_phone_still_fails(self):
        engine = OutreachEngine()
        lead = _make_lead(phone=None, email=None)
        item = _make_queue_item(lead.id)
        tenant_id = uuid.uuid4()
        session = _fake_session([item], [lead])

        with (
            patch("app.services.outreach.engine.AsyncSessionLocal") as db_ctx,
            patch("app.services.outreach.engine.set_tenant_context", new_callable=AsyncMock),
            patch("app.core.config.settings.AUTO_SEND_OUTREACH", True),
            patch(
                "app.services.outreach.gmail.email_delivery_status",
                new_callable=AsyncMock,
                return_value={"send_mode": "live", "blocker_code": None, "required_action": None},
            ),
            patch.object(engine, "_audit", new_callable=AsyncMock) as mock_audit,
        ):
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            sent = await engine.execute_due_outreach(tenant_id)

        assert sent == 0
        assert item.status == FollowUpStatus.FAILED
        audited_actions = [call.args[2] for call in mock_audit.call_args_list]
        assert "outreach_missing_email" in audited_actions
