"""
Number-porting orchestration on top of Twilio's Porting API.

The user-facing "just plug in your existing number" path breaks into two
very different pieces:

1. Attach a number *already in this Twilio account* -- one API call, done
   in seconds. That's the existing onboarding.existing_twilio_number code
   path, already shipped.

2. Port a number *from another carrier* into this Twilio account -- 5-10
   business days of carrier back-and-forth with legally-binding LOA docs,
   a bill copy, and specific verification fields from the losing carrier.
   That is what this module is for. The code here manages our side of the
   process (persistence, submission, status polling); the actual carrier
   transfer happens outside our control, at Twilio and the losing carrier.

The Twilio Porting API is called via raw HTTPS rather than the twilio-python
SDK because the SDK's coverage of the newer Porting endpoints has been
inconsistent -- doing it directly keeps this working across SDK versions
and makes the payloads reviewable in code without having to read SDK
source.
"""

import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.models.port_request import PortRequest

logger = logging.getLogger(__name__)

_PORTING_BASE = "https://numbers.twilio.com/v1/Porting"


class PortingError(Exception):
    """Raised for expected Twilio API failures (validation, auth, config
    problems). Handlers turn these into 4xx to the operator; unexpected
    exceptions bubble as 500s via the middleware error envelope."""


def _client() -> httpx.AsyncClient:
    settings = get_settings()
    return httpx.AsyncClient(
        auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        timeout=httpx.Timeout(30.0, connect=10.0),
    )


async def submit_port_in(db: AsyncSession, port_request: PortRequest) -> PortRequest:
    """Submit a draft PortRequest to Twilio and stash the resulting PortIn SID.

    Idempotent when called twice on the same row: if the record already
    carries a twilio_port_in_sid, this refreshes status from Twilio instead
    of creating a duplicate order (which Twilio would reject anyway with a
    400 for the same number). That protects an operator who clicks
    "Submit" twice.
    """
    if port_request.status != "draft" and port_request.twilio_port_in_sid:
        logger.info(f"Port request {port_request.id} already submitted; refreshing status")
        return await refresh_port_status(db, port_request)

    payload = {
        "TargetAccountSid": get_settings().twilio_account_sid,
        "NumberSid": None,  # populated by Twilio once the port completes; not needed at submit
        "PhoneNumber": port_request.phone_number,
        # LosingCarrier* fields Twilio requires to file the port with the
        # losing carrier. All of these come off the customer's most recent
        # bill from that carrier.
        "LosingCarrierName": port_request.losing_carrier_name,
        "LosingCarrierAccountNumber": port_request.losing_account_number,
        "LosingCarrierAccountPin": port_request.losing_account_pin,
        "BillingName": port_request.billing_name,
        "BillingAddress": port_request.billing_address,
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    async with _client() as client:
        try:
            response = await client.post(f"{_PORTING_BASE}/PortIn", data=payload)
        except httpx.HTTPError as e:
            raise PortingError(f"Twilio Porting API unreachable: {e}") from e

        if response.status_code >= 400:
            # Twilio returns a JSON body with `code` and `message`; the raw
            # string is enough context for the operator without leaking the
            # LOA docs or account PIN in an exception message.
            raise PortingError(f"Twilio rejected port-in submission: HTTP {response.status_code} — {response.text[:400]}")

        body = response.json()

    port_request.twilio_port_in_sid = body.get("sid")
    port_request.status = _translate_status(body.get("status"), "submitted")
    port_request.status_details = _extract_status_details(body)
    if body.get("target_port_in_date"):
        try:
            port_request.target_completion_date = datetime.fromisoformat(body["target_port_in_date"])
        except (ValueError, TypeError):
            pass
    await db.flush()
    logger.info(
        f"Submitted port-in {port_request.twilio_port_in_sid} for clinic {port_request.clinic_id}, "
        f"number {port_request.phone_number}"
    )
    return port_request


async def refresh_port_status(db: AsyncSession, port_request: PortRequest) -> PortRequest:
    """Fetch the latest state from Twilio for an already-submitted port.

    The port lifecycle spans days at Twilio's side; this is what a nightly
    Arq job would call to keep the dashboard status current."""
    if not port_request.twilio_port_in_sid:
        raise PortingError(f"Port request {port_request.id} has not been submitted yet")

    async with _client() as client:
        try:
            response = await client.get(f"{_PORTING_BASE}/PortIn/{port_request.twilio_port_in_sid}")
        except httpx.HTTPError as e:
            raise PortingError(f"Twilio Porting API unreachable: {e}") from e

    if response.status_code == 404:
        # The order was canceled or purged upstream. Prefer marking it here
        # to letting operators think it is still in flight.
        port_request.status = "canceled"
        port_request.status_details = {"error": "Twilio no longer knows this port order (404)"}
        await db.flush()
        return port_request

    if response.status_code >= 400:
        raise PortingError(f"Twilio status refresh failed: HTTP {response.status_code} — {response.text[:400]}")

    body = response.json()
    port_request.status = _translate_status(body.get("status"), port_request.status)
    port_request.status_details = _extract_status_details(body)
    if port_request.status == "completed" and not port_request.completed_at:
        port_request.completed_at = datetime.now(timezone.utc)
    await db.flush()
    return port_request


async def cancel_port_in(db: AsyncSession, port_request: PortRequest) -> PortRequest:
    """Cancel a submitted port. Only possible before the losing carrier's
    approval window closes -- Twilio returns 400 outside that window and we
    surface that verbatim rather than pretending we canceled."""
    if not port_request.twilio_port_in_sid:
        port_request.status = "canceled"
        await db.flush()
        return port_request

    async with _client() as client:
        try:
            response = await client.delete(f"{_PORTING_BASE}/PortIn/{port_request.twilio_port_in_sid}")
        except httpx.HTTPError as e:
            raise PortingError(f"Twilio Porting API unreachable: {e}") from e

    if response.status_code >= 400 and response.status_code != 404:
        raise PortingError(f"Twilio refused cancel: HTTP {response.status_code} — {response.text[:400]}")

    port_request.status = "canceled"
    await db.flush()
    return port_request


# Twilio's PortIn status vocabulary maps to ours below. Values not in this
# map are passed through verbatim rather than lost -- Twilio adds states
# occasionally and losing information is worse than an unfamiliar label.
_STATUS_MAP = {
    "draft": "draft",
    "pending-loa": "pending_documents",
    "pending-documents": "pending_documents",
    "in-progress": "pending_carrier",
    "submitted": "submitted",
    "completed": "completed",
    "canceled": "canceled",
    "failed": "failed",
}


def _translate_status(twilio_status: str | None, fallback: str) -> str:
    if not twilio_status:
        return fallback
    return _STATUS_MAP.get(twilio_status.lower(), twilio_status.lower())


def _extract_status_details(body: dict[str, Any]) -> dict[str, Any]:
    """Compact, non-sensitive subset of Twilio's response for the operator UI."""
    return {
        "twilio_status": body.get("status"),
        "notification_email": body.get("notification_email"),
        "target_port_in_date": body.get("target_port_in_date"),
        "target_port_in_time_range_start": body.get("target_port_in_time_range_start"),
        "target_port_in_time_range_end": body.get("target_port_in_time_range_end"),
        "port_in_authorization_document_sid": body.get("port_in_authorization_document_sid"),
        "date_created": body.get("date_created"),
    }
