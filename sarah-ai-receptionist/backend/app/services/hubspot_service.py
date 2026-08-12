"""
HubSpot lead capture — creates or updates a CRM Contact whenever Sarah
collects enough identifying information (a phone number, optionally a name)
during a call to actually be a followable lead.

Optional integration, same pattern as Stripe/Twilio elsewhere in this
codebase: HUBSPOT_ACCESS_TOKEN unset means this silently does nothing rather
than affecting a caller's real appointment. A caller who never gives a name
or phone has nothing HubSpot can index a contact on anyway -- the browser
demo never asks for an email, so phone is the only usable identifier.

The token is a HubSpot Private App access token (Settings -> Integrations ->
Private Apps in the target HubSpot portal, with crm.objects.contacts.write
and crm.objects.notes.write scopes) -- not an OAuth app, and not the same
kind of credential as the interactive MCP connection used elsewhere.
"""

import logging
import time

import httpx

from app.config.settings import get_settings
from app.core.redact import redact_phone

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.hubapi.com"
# Short and bounded like every other outbound integration in this codebase
# (see app/core/redis.py) -- a HubSpot outage must cost the caller
# milliseconds of extra latency at most, never seconds, since this runs in
# the same turn as their booking confirmation.
_REQUEST_TIMEOUT = httpx.Timeout(5.0, connect=3.0)

# HubSpot's documented default association type ID for "note to contact"
# (HUBSPOT_DEFINED associations). Distinct from custom association types,
# which are portal-specific numeric IDs assigned when created -- this one is
# a fixed HubSpot constant, safe to hardcode.
_NOTE_TO_CONTACT_ASSOCIATION_TYPE_ID = 202


def _describe_action(action: str, params: dict) -> str:
    service = params.get("service", "an appointment")
    when = params.get("datetime", "an unspecified time")
    if action == "BOOK":
        return f"Booked {service} for {when} via Sarah (AI receptionist demo)."
    if action == "RESCHEDULE":
        return f"Requested to reschedule to {when} via Sarah (AI receptionist demo)."
    if action == "CANCEL":
        return "Requested to cancel their appointment via Sarah (AI receptionist demo)."
    return f"Talked to Sarah (AI receptionist demo): {action}."


async def _find_contact_id_by_phone(client: httpx.AsyncClient, headers: dict, phone: str) -> str | None:
    resp = await client.post(
        f"{_BASE_URL}/crm/v3/objects/contacts/search",
        headers=headers,
        json={
            "filterGroups": [{"filters": [{"propertyName": "phone", "operator": "EQ", "value": phone}]}],
            "limit": 1,
        },
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return results[0]["id"] if results else None


async def _upsert_contact(
    client: httpx.AsyncClient, headers: dict, contact_id: str | None, properties: dict
) -> str:
    if contact_id:
        resp = await client.patch(
            f"{_BASE_URL}/crm/v3/objects/contacts/{contact_id}", headers=headers, json={"properties": properties}
        )
        resp.raise_for_status()
        return contact_id
    resp = await client.post(f"{_BASE_URL}/crm/v3/objects/contacts", headers=headers, json={"properties": properties})
    resp.raise_for_status()
    return resp.json()["id"]


async def _log_note(client: httpx.AsyncClient, headers: dict, contact_id: str, note_body: str) -> None:
    resp = await client.post(
        f"{_BASE_URL}/crm/v3/objects/notes",
        headers=headers,
        json={
            "properties": {
                "hs_note_body": note_body,
                "hs_timestamp": str(int(time.time() * 1000)),
            },
            "associations": [
                {
                    "to": {"id": contact_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": _NOTE_TO_CONTACT_ASSOCIATION_TYPE_ID,
                        }
                    ],
                }
            ],
        },
    )
    resp.raise_for_status()


async def upsert_lead_from_call(
    *, phone: str | None, name: str | None, clinic_name: str, action: str, params: dict
) -> None:
    """Create or update a HubSpot Contact for this caller, with a Note
    describing what Sarah just did for them.

    Never raises -- called from inside the live call/turn-taking loop, and a
    HubSpot outage or bad token must not affect a caller's actual
    appointment. Mirrors notification_service.py's SMS pattern: log and
    move on.
    """
    settings = get_settings()
    if not settings.hubspot_enabled:
        return

    phone = (phone or "").strip()
    if not phone:
        # Nothing to search or index a contact on. Silent at info level, not
        # an error -- most demo turns legitimately have no phone yet.
        logger.info(f"Skipping HubSpot lead capture for {action}: no phone number given")
        return

    headers = {
        "Authorization": f"Bearer {settings.hubspot_access_token}",
        "Content-Type": "application/json",
    }
    first_name, _, last_name = (name or "").strip().partition(" ")
    properties: dict[str, str] = {"phone": phone}
    if first_name:
        properties["firstname"] = first_name
    if last_name:
        properties["lastname"] = last_name

    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            contact_id = await _find_contact_id_by_phone(client, headers, phone)
            if not contact_id:
                # Only stamp lead status on genuinely new contacts -- an
                # existing patient calling back to reschedule shouldn't be
                # silently reset to "new lead" every time they call.
                properties.setdefault("lifecyclestage", "lead")
            contact_id = await _upsert_contact(client, headers, contact_id, properties)
            note = f"{_describe_action(action, params)} Clinic: {clinic_name}."
            await _log_note(client, headers, contact_id, note)
    except Exception as e:
        logger.error(f"HubSpot lead capture failed for {redact_phone(phone)}: {e}")
