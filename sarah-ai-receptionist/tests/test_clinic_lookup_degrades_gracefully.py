"""
A database outage during clinic lookup must not kill the call.

_load_clinic_config used to let a database exception propagate straight out
of it, uncaught, all the way through the /media-stream WebSocket handler --
which had nothing catching it either. A caller dialing in during a database
outage got dead air and then a hangup, not a degraded-but-functioning Sarah.

The "no clinic found for this number" case already returns None safely --
CallManager and AIBrain both treat None as "use the default sample clinic
config" (see ai_brain.py's `clinic_config or get_default_clinic_config()`).
This test pins that a database *outage* takes that same safe path, not a
different (crashing) one.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.routes import call_handler


@pytest.mark.asyncio
async def test_a_database_outage_returns_none_instead_of_crashing_the_call(monkeypatch):
    @asynccontextmanager
    async def _broken_db_context():
        raise ConnectionError("simulated: database unreachable")
        yield  # pragma: no cover -- unreachable, but keeps this a generator-based CM

    monkeypatch.setattr(call_handler, "get_db_context", _broken_db_context)

    result = await call_handler._load_clinic_config("+15550001234")

    assert result is None


@pytest.mark.asyncio
async def test_no_twilio_number_short_circuits_before_touching_the_database(monkeypatch):
    """The browser demo and any call with no called-number metadata must not
    even attempt a database round-trip -- confirmed by making the database
    call explode if it's reached at all."""

    async def _explode(*a, **k):
        raise AssertionError("get_db_context must not be called with no twilio_number")

    monkeypatch.setattr(call_handler, "get_db_context", AsyncMock(side_effect=_explode))

    result = await call_handler._load_clinic_config(None)

    assert result is None
