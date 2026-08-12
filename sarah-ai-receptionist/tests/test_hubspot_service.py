"""
HubSpot lead capture: creates/updates a Contact + logs a Note whenever Sarah
collects a phone number during a BOOK/RESCHEDULE/CANCEL, on either call path.

Optional integration, same shape as Stripe/Twilio elsewhere in this codebase:
disabled by default, and a HubSpot outage or bad token must never propagate
into the live call/turn-taking loop -- a caller's actual appointment cannot
depend on a CRM write succeeding.
"""

import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.config.settings import Settings
from app.services import hubspot_service
from app.services.hubspot_service import upsert_lead_from_call


def _settings(**overrides) -> Settings:
    base = {
        "openrouter_api_key": "x",
        "twilio_account_sid": "",
        "twilio_auth_token": "",
        "twilio_phone_number": "",
        "deepgram_api_key": "x",
        "elevenlabs_api_key": "x",
        "elevenlabs_voice_id": "x",
        "database_url": "postgresql+asyncpg://t:t@localhost/t",
        "jwt_secret_key": "x",
        "hubspot_access_token": "",
    }
    base.update(overrides)
    return Settings(**base)


class _FakeResponse:
    def __init__(self, json_data: dict, status_code: int = 200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("simulated HubSpot error", request=None, response=self)

    def json(self):
        return self._json


class _FakeHubSpotClient:
    """Records every call; the search result is scripted so a test controls
    whether the code path is "create new contact" or "update existing"."""

    def __init__(self, search_results: list[dict] | None = None):
        self.calls: list[tuple[str, str, dict]] = []
        self._search_results = search_results or []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, headers=None, json=None):
        self.calls.append(("POST", url, json))
        if url.endswith("/contacts/search"):
            return _FakeResponse({"results": self._search_results})
        if url.endswith("/objects/contacts"):
            return _FakeResponse({"id": "new-contact-id"})
        if url.endswith("/notes"):
            return _FakeResponse({"id": "note-id"})
        raise AssertionError(f"unexpected POST {url}")

    async def patch(self, url, headers=None, json=None):
        self.calls.append(("PATCH", url, json))
        contact_id = url.rsplit("/", 1)[-1]
        return _FakeResponse({"id": contact_id})


def _patch_client(monkeypatch, fake_client: _FakeHubSpotClient):
    monkeypatch.setattr(hubspot_service.httpx, "AsyncClient", lambda **kwargs: fake_client)


def _explode_if_constructed(monkeypatch):
    """Asserts no HubSpot client is ever built -- used to prove a code path
    is skipped entirely, not just that its result is discarded."""

    def _boom(**kwargs):
        raise AssertionError("httpx.AsyncClient must not be constructed on this path")

    monkeypatch.setattr(hubspot_service.httpx, "AsyncClient", _boom)


# ---- config -------------------------------------------------------------------


def test_disabled_by_default():
    assert _settings().hubspot_enabled is False


def test_enabled_once_a_token_is_set():
    assert _settings(hubspot_access_token="pat-na1-xxx").hubspot_enabled is True


# ---- skip conditions ------------------------------------------------------------


@pytest.mark.asyncio
async def test_does_nothing_when_hubspot_is_not_configured(monkeypatch):
    monkeypatch.setattr(hubspot_service, "get_settings", lambda: _settings())
    _explode_if_constructed(monkeypatch)

    await upsert_lead_from_call(
        phone="+15550001111", name="Jane Doe", clinic_name="Smile Dental", action="BOOK", params={}
    )


@pytest.mark.asyncio
async def test_does_nothing_when_no_phone_was_given(monkeypatch):
    """The browser demo never asks for an email, so phone is the only
    identifier HubSpot can index a contact on -- nothing to write without
    it, even when HubSpot is fully configured."""
    monkeypatch.setattr(hubspot_service, "get_settings", lambda: _settings(hubspot_access_token="pat-x"))
    _explode_if_constructed(monkeypatch)

    await upsert_lead_from_call(phone=None, name="Jane Doe", clinic_name="Smile Dental", action="BOOK", params={})
    await upsert_lead_from_call(phone="   ", name="Jane Doe", clinic_name="Smile Dental", action="BOOK", params={})


# ---- create vs update -----------------------------------------------------------


@pytest.mark.asyncio
async def test_creates_a_new_contact_when_no_match_is_found(monkeypatch):
    monkeypatch.setattr(hubspot_service, "get_settings", lambda: _settings(hubspot_access_token="pat-x"))
    fake = _FakeHubSpotClient(search_results=[])
    _patch_client(monkeypatch, fake)

    await upsert_lead_from_call(
        phone="+15550001111",
        name="Jane Doe",
        clinic_name="Smile Dental",
        action="BOOK",
        params={"service": "cleaning", "datetime": "tomorrow at 2pm"},
    )

    methods = [c[0] for c in fake.calls]
    assert methods == ["POST", "POST", "POST"]  # search, create contact, log note

    _, search_url, search_body = fake.calls[0]
    assert search_url.endswith("/contacts/search")
    assert search_body["filterGroups"][0]["filters"][0]["value"] == "+15550001111"

    _, create_url, create_body = fake.calls[1]
    assert create_url.endswith("/objects/contacts")
    assert create_body["properties"]["phone"] == "+15550001111"
    assert create_body["properties"]["firstname"] == "Jane"
    assert create_body["properties"]["lastname"] == "Doe"
    assert create_body["properties"]["lifecyclestage"] == "lead"

    _, note_url, note_body = fake.calls[2]
    assert note_url.endswith("/notes")
    assert "cleaning" in note_body["properties"]["hs_note_body"]
    assert note_body["associations"][0]["to"]["id"] == "new-contact-id"


@pytest.mark.asyncio
async def test_updates_the_existing_contact_when_the_phone_matches(monkeypatch):
    """A returning caller must not spawn a duplicate contact -- this is what
    the search-by-phone step exists for."""
    monkeypatch.setattr(hubspot_service, "get_settings", lambda: _settings(hubspot_access_token="pat-x"))
    fake = _FakeHubSpotClient(search_results=[{"id": "existing-123"}])
    _patch_client(monkeypatch, fake)

    await upsert_lead_from_call(
        phone="+15550001111",
        name="Jane Doe",
        clinic_name="Smile Dental",
        action="RESCHEDULE",
        params={"datetime": "Friday at 10am"},
    )

    methods = [c[0] for c in fake.calls]
    assert methods == ["POST", "PATCH", "POST"]  # search, update contact, log note

    _, update_url, update_body = fake.calls[1]
    assert update_url.endswith("/contacts/existing-123")
    # An existing contact must not be silently reset to a fresh lead every
    # time they call back -- lifecyclestage is only stamped on creation.
    assert "lifecyclestage" not in update_body["properties"]

    _, note_url, note_body = fake.calls[2]
    assert note_body["associations"][0]["to"]["id"] == "existing-123"


@pytest.mark.asyncio
async def test_a_single_word_name_only_sets_first_name(monkeypatch):
    monkeypatch.setattr(hubspot_service, "get_settings", lambda: _settings(hubspot_access_token="pat-x"))
    fake = _FakeHubSpotClient(search_results=[])
    _patch_client(monkeypatch, fake)

    await upsert_lead_from_call(
        phone="+15550001111", name="Cher", clinic_name="Smile Dental", action="BOOK", params={}
    )

    _, _, create_body = fake.calls[1]
    assert create_body["properties"]["firstname"] == "Cher"
    assert "lastname" not in create_body["properties"]


# ---- resilience -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_hubspot_failure_never_raises(monkeypatch):
    """This runs inside the live call/turn-taking loop on both call paths --
    an outage or bad token must degrade to a log line, never an exception
    that could affect a caller's actual appointment."""
    monkeypatch.setattr(hubspot_service, "get_settings", lambda: _settings(hubspot_access_token="pat-x"))

    class _ExplodingClient(_FakeHubSpotClient):
        async def post(self, url, headers=None, json=None):
            raise httpx.ConnectError("simulated HubSpot outage")

    _patch_client(monkeypatch, _ExplodingClient())

    await upsert_lead_from_call(
        phone="+15550001111", name="Jane Doe", clinic_name="Smile Dental", action="BOOK", params={}
    )  # must not raise


# ---- note wording -------------------------------------------------------------------


def test_note_wording_per_action():
    assert "Booked" in hubspot_service._describe_action("BOOK", {"service": "a cleaning", "datetime": "3pm"})
    assert "reschedule" in hubspot_service._describe_action("RESCHEDULE", {"datetime": "3pm"})
    assert "cancel" in hubspot_service._describe_action("CANCEL", {})


# ---- wiring: both call paths actually invoke this, not just define it -------------


def test_the_demo_call_path_invokes_lead_capture_on_lead_worthy_actions():
    import inspect

    from app.services import demo_call_manager

    source = inspect.getsource(demo_call_manager.DemoCallManager._handle_action)
    assert "upsert_lead_from_call" in source
    for action in ("BOOK", "RESCHEDULE", "CANCEL"):
        assert action in demo_call_manager._LEAD_WORTHY_ACTIONS


def test_the_phone_call_path_invokes_lead_capture_on_lead_worthy_actions():
    import inspect

    from app.services import call_manager

    source = inspect.getsource(call_manager.CallManager._stream_ai_response)
    assert "upsert_lead_from_call" in source


def test_lead_capture_is_not_invoked_for_control_flow_actions():
    """TRANSFER/END/LOOKUP_PATIENT are not sales leads on their own -- only
    BOOK/RESCHEDULE/CANCEL (which require a phone number to have been
    captured) are lead-worthy."""
    from app.services.demo_call_manager import _LEAD_WORTHY_ACTIONS

    assert "TRANSFER" not in _LEAD_WORTHY_ACTIONS
    assert "END" not in _LEAD_WORTHY_ACTIONS
    assert "LOOKUP_PATIENT" not in _LEAD_WORTHY_ACTIONS
