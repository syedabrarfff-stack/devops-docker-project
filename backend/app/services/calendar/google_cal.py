"""
Google Calendar integration — read and create events via REST API.
Requires Gmail OAuth token (same token includes Calendar scope).
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

CAL_BASE = "https://www.googleapis.com/calendar/v3"


async def _get_token(db) -> Optional[str]:
    from app.services.auth.gmail_oauth import _get_valid_token
    return await _get_valid_token(db)


async def list_events(db, calendar_id: str = "primary",
                       days_ahead: int = 7, max_results: int = 20) -> list[dict]:
    """Fetch upcoming events from Google Calendar."""
    token = await _get_token(db)
    if not token:
        return []
    now   = datetime.now(timezone.utc)
    until = now + timedelta(days=days_ahead)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{CAL_BASE}/calendars/{calendar_id}/events",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "timeMin":    now.isoformat(),
                    "timeMax":    until.isoformat(),
                    "maxResults": max_results,
                    "orderBy":    "startTime",
                    "singleEvents": "true",
                },
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning(f"Calendar list_events failed: {e}")
        return []

    return [_format_event(e) for e in data.get("items", [])]


async def create_event(db, summary: str, description: str = "",
                        start: Optional[datetime] = None,
                        end: Optional[datetime] = None,
                        attendees: Optional[list[str]] = None,
                        calendar_id: str = "primary") -> Optional[dict]:
    """Create a calendar event."""
    token = await _get_token(db)
    if not token:
        return None
    start = start or datetime.now(timezone.utc) + timedelta(hours=1)
    end   = end   or start + timedelta(hours=1)

    body = {
        "summary":     summary,
        "description": description,
        "start":       {"dateTime": start.isoformat(), "timeZone": "UTC"},
        "end":         {"dateTime": end.isoformat(),   "timeZone": "UTC"},
    }
    if attendees:
        body["attendees"] = [{"email": e} for e in attendees]

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{CAL_BASE}/calendars/{calendar_id}/events",
                headers={"Authorization": f"Bearer {token}"},
                json=body,
            )
            r.raise_for_status()
            return _format_event(r.json())
    except Exception as e:
        logger.warning(f"Calendar create_event failed: {e}")
        return None


async def delete_event(db, event_id: str, calendar_id: str = "primary") -> bool:
    token = await _get_token(db)
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.delete(
                f"{CAL_BASE}/calendars/{calendar_id}/events/{event_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            return r.status_code in (200, 204)
    except Exception:
        return False


async def list_calendars(db) -> list[dict]:
    token = await _get_token(db)
    if not token:
        return []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{CAL_BASE}/users/me/calendarList",
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
            return [{"id": c["id"], "summary": c.get("summary", ""), "primary": c.get("primary", False)}
                    for c in r.json().get("items", [])]
    except Exception as e:
        logger.warning(f"Calendar list_calendars failed: {e}")
        return []


async def schedule_meeting(db, lead_email: str, lead_name: str,
                             company: str, service: str) -> Optional[dict]:
    """AI-suggested meeting slot creation for a lead."""
    from datetime import date
    # Default: next business day at 10 AM UTC
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    while tomorrow.weekday() >= 5:  # skip weekend
        tomorrow += timedelta(days=1)
    start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
    return await create_event(
        db,
        summary=f"Discovery call — {company} ({lead_name})",
        description=f"JARVIS-scheduled discovery call.\nService: {service}\nContact: {lead_email}",
        start=start,
        end=start + timedelta(hours=1),
        attendees=[lead_email],
    )


def _format_event(event: dict) -> dict:
    start = event.get("start", {})
    end   = event.get("end", {})
    return {
        "id":          event.get("id"),
        "summary":     event.get("summary", "Untitled"),
        "description": event.get("description", ""),
        "start":       start.get("dateTime") or start.get("date"),
        "end":         end.get("dateTime")   or end.get("date"),
        "attendees":   [a["email"] for a in event.get("attendees", [])],
        "html_link":   event.get("htmlLink"),
        "status":      event.get("status", "confirmed"),
    }
