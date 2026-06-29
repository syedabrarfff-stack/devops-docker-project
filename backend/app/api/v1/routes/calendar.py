"""
Google Calendar routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.api.v1.routes.auth import get_current_captain
from app.core.rate_limit import limiter
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.calendar.google_cal import (
    list_events, create_event, delete_event,
    list_calendars, schedule_meeting,
)

router = APIRouter(prefix="/calendar", tags=["Calendar"], dependencies=[Depends(get_current_captain)])


class EventIn(BaseModel):
    summary: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(default="", max_length=5_000)
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    attendees: Optional[list[str]] = None
    calendar_id: str = Field(default="primary", max_length=100)


class MeetingIn(BaseModel):
    lead_email: str = Field(..., max_length=320)
    lead_name: str = Field(..., max_length=200)
    company: str = Field(..., max_length=300)
    service: str = Field(default="AI automation", max_length=200)


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
@limiter.limit("20/minute")
async def add_event(request: Request, body: EventIn, db: AsyncSession = Depends(get_db)):
    event = await create_event(
        db, body.summary, body.description or "",
        start=body.start, end=body.end,
        attendees=body.attendees, calendar_id=body.calendar_id,
    )
    if not event:
        raise HTTPException(503, "Calendar not connected — complete the provider connection first")
    return event


@router.delete("/events/{event_id}")
@limiter.limit("20/minute")
async def remove_event(request: Request, event_id: str, calendar_id: str = "primary",
                        db: AsyncSession = Depends(get_db)):
    ok = await delete_event(db, event_id, calendar_id)
    if not ok:
        raise HTTPException(404, "Event not found or calendar not connected")
    return {"deleted": True, "event_id": event_id}


@router.get("/calendars")
async def get_calendars(db: AsyncSession = Depends(get_db)):
    return await list_calendars(db)


@router.post("/meetings/schedule")
@limiter.limit("10/minute")
async def schedule_lead_meeting(request: Request, body: MeetingIn, db: AsyncSession = Depends(get_db)):
    event = await schedule_meeting(
        db, body.lead_email, body.lead_name, body.company, body.service
    )
    if not event:
        raise HTTPException(503, "Calendar not connected — complete the provider connection first")
    await db.commit()
    return event
