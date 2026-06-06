"""
Google Calendar routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.calendar.google_cal import (
    list_events, create_event, delete_event,
    list_calendars, schedule_meeting,
)

router = APIRouter(prefix="/calendar", tags=["Calendar"])


class EventIn(BaseModel):
    summary: str
    description: Optional[str] = ""
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    attendees: Optional[list[str]] = None
    calendar_id: str = "primary"


class MeetingIn(BaseModel):
    lead_email: str
    lead_name: str
    company: str
    service: str = "AI automation"


@router.get("/events")
async def get_events(
    days_ahead: int = Query(7, ge=1, le=90),
    max_results: int = Query(20, le=100),
    calendar_id: str = "primary",
    db: AsyncSession = Depends(get_db),
):
    events = await list_events(db, calendar_id=calendar_id,
                                days_ahead=days_ahead, max_results=max_results)
    return events


@router.post("/events")
async def add_event(body: EventIn, db: AsyncSession = Depends(get_db)):
    event = await create_event(
        db, body.summary, body.description or "",
        start=body.start, end=body.end,
        attendees=body.attendees, calendar_id=body.calendar_id,
    )
    if not event:
        raise HTTPException(503, "Calendar not connected — complete the provider connection first")
    return event


@router.delete("/events/{event_id}")
async def remove_event(event_id: str, calendar_id: str = "primary",
                        db: AsyncSession = Depends(get_db)):
    ok = await delete_event(db, event_id, calendar_id)
    if not ok:
        raise HTTPException(404, "Event not found or calendar not connected")
    return {"deleted": True, "event_id": event_id}


@router.get("/calendars")
async def get_calendars(db: AsyncSession = Depends(get_db)):
    return await list_calendars(db)


@router.post("/meetings/schedule")
async def schedule_lead_meeting(body: MeetingIn, db: AsyncSession = Depends(get_db)):
    event = await schedule_meeting(
        db, body.lead_email, body.lead_name, body.company, body.service
    )
    if not event:
        raise HTTPException(503, "Calendar not connected — complete the provider connection first")
    await db.commit()
    return event
