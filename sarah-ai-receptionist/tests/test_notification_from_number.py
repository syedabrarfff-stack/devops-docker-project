"""
Every SMS (confirmation, reschedule/cancel, escalation, reminder) previously
sent `from_=settings.twilio_phone_number` unconditionally -- the single
platform-wide default number, regardless of which number the patient
actually called. A clinic using its own existing number (forwarded to a
Twilio number Sarah holds, or a number attached directly during onboarding)
would have every SMS arrive from a different, unfamiliar number than the one
they dialed.

These pin that each notification function now prefers an explicit
from_number (the clinic's own twilio_phone_number) over the platform
default, and falls back to the platform default only when the clinic has
none set.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services import notification_service  # noqa: E402


@pytest.fixture
def mock_twilio_client():
    client = MagicMock()
    with patch.object(notification_service, "get_twilio_client", return_value=client):
        yield client


def test_resolve_from_number_prefers_clinic_number():
    assert notification_service._resolve_from_number("+9665551112222") == "+9665551112222"


def test_resolve_from_number_falls_back_to_platform_default():
    fallback = notification_service._resolve_from_number(None)
    assert fallback == notification_service.get_settings().twilio_phone_number


@pytest.mark.asyncio
async def test_confirmation_sms_sent_from_clinics_own_number(mock_twilio_client):
    await notification_service.send_appointment_confirmation(
        "+15550001111", "Smile Dental", "cleaning", "Monday 10am", from_number="+9665551112222"
    )
    _, kwargs = mock_twilio_client.messages.create.call_args
    assert kwargs["from_"] == "+9665551112222"


@pytest.mark.asyncio
async def test_appointment_change_sms_sent_from_clinics_own_number(mock_twilio_client):
    await notification_service.send_appointment_change(
        "+15550001111", "Smile Dental", "cancelled", "cleaning", "Monday 10am", from_number="+9665551112222"
    )
    _, kwargs = mock_twilio_client.messages.create.call_args
    assert kwargs["from_"] == "+9665551112222"


@pytest.mark.asyncio
async def test_urgent_escalation_sms_sent_from_clinics_own_number(mock_twilio_client):
    await notification_service.send_urgent_escalation(
        "+15550009999", "Smile Dental", "+15550001111", "caller in pain", from_number="+9665551112222"
    )
    _, kwargs = mock_twilio_client.messages.create.call_args
    assert kwargs["from_"] == "+9665551112222"


@pytest.mark.asyncio
async def test_reminder_sms_sent_from_clinics_own_number(mock_twilio_client):
    await notification_service.send_appointment_reminder(
        "+15550001111", "Smile Dental", "cleaning", "Monday 10am", from_number="+9665551112222"
    )
    _, kwargs = mock_twilio_client.messages.create.call_args
    assert kwargs["from_"] == "+9665551112222"


@pytest.mark.asyncio
async def test_confirmation_sms_falls_back_to_platform_default_without_a_clinic_number(mock_twilio_client):
    await notification_service.send_appointment_confirmation(
        "+15550001111", "Smile Dental", "cleaning", "Monday 10am"
    )
    _, kwargs = mock_twilio_client.messages.create.call_args
    assert kwargs["from_"] == notification_service.get_settings().twilio_phone_number
