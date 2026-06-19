"""
Notification management — persistent log, read/unread, broadcast.
"""
import uuid
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update
from app.core.config import settings
from app.core.database import get_db
from app.models.notifications import NotificationLog
from app.api.v1.routes.ws import broadcast_notification


def _system_tenant_id() -> uuid.UUID:
    return uuid.UUID(settings.JARVIS_DEFAULT_TENANT_ID) if settings.JARVIS_DEFAULT_TENANT_ID else uuid.UUID("00000000-0000-0000-0000-000000000000")

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotifyIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1, max_length=10_000)
    level: str = Field(default="info", max_length=20)
    category: Optional[str] = Field(default=None, max_length=100)
    reference: Optional[str] = Field(default=None, max_length=500)
    channels: Optional[list[str]] = None  # telegram | slack | websocket


@router.get("/")
async def list_notifications(
    unread_only: bool = False,
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(NotificationLog).order_by(desc(NotificationLog.created_at)).limit(limit)
    if unread_only:
        q = q.where(NotificationLog.read == False)
    if category:
        q = q.where(NotificationLog.category == category)
    rows = (await db.execute(q)).scalars().all()
    return [{
        "id": n.id, "channel": n.channel, "title": n.title,
        "body": n.body, "level": n.level, "category": n.category,
        "reference": n.reference, "read": n.read, "delivered": n.delivered,
        "created_at": str(n.created_at),
    } for n in rows]


@router.get("/unread-count")
async def unread_count(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    count = await db.scalar(
        select(func.count()).select_from(NotificationLog)
        .where(NotificationLog.read == False)
    ) or 0
    return {"unread": count}


@router.post("/{notification_id}/read")
async def mark_read(notification_id: int, db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(NotificationLog)
        .where(NotificationLog.id == notification_id)
        .values(read=True)
    )
    await db.commit()
    return {"read": True}


@router.post("/read-all")
async def mark_all_read(db: AsyncSession = Depends(get_db)):
    await db.execute(update(NotificationLog).values(read=True))
    await db.commit()
    return {"marked": True}


@router.post("/broadcast")
async def send_notification(body: NotifyIn, db: AsyncSession = Depends(get_db)):
    """Send notification across all specified channels."""
    channels = body.channels or ["websocket"]
    sent = {}

    if "websocket" in channels:
        await broadcast_notification(body.title, body.body, body.level,
                                      body.category, body.reference)
        sent["websocket"] = True

    if "telegram" in channels:
        from app.services.notifications.telegram import notify_telegram
        sent["telegram"] = await notify_telegram(f"*{body.title}*\n{body.body}")

    if "slack" in channels:
        from app.services.notifications.slack import notify_system_event
        sent["slack"] = await notify_system_event(body.title, body.body, body.level)

    # Persist
    notif = NotificationLog(
        tenant_id=_system_tenant_id(),
        channel=",".join(channels), title=body.title, body=body.body,
        level=body.level, category=body.category, reference=body.reference,
        delivered=any(sent.values()),
    )
    db.add(notif)
    await db.commit()
    return {"sent": sent, "id": notif.id}


@router.delete("/clear")
async def clear_old(days: int = Query(30, ge=1), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import delete
    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        delete(NotificationLog).where(NotificationLog.created_at < cutoff)
    )
    await db.commit()
    return {"deleted": result.rowcount}
