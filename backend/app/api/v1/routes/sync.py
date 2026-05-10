"""
Contact synchronization routes — Apollo → JARVIS CRM.
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.contacts.sync import sync_from_apollo, enrich_contact

router = APIRouter(prefix="/sync", tags=["Sync"])


class SyncConfig(BaseModel):
    industries: Optional[list[str]] = None
    countries: Optional[list[str]] = None
    limit: int = 50


@router.post("/apollo")
async def run_apollo_sync(body: SyncConfig = SyncConfig(), db: AsyncSession = Depends(get_db)):
    """Fetch contacts from Apollo.io and upsert into CRM."""
    count = await sync_from_apollo(
        db, limit=body.limit,
        industries=body.industries,
        countries=body.countries,
    )
    await db.commit()
    return {"synced": count, "source": "apollo"}


@router.post("/enrich/{contact_id}")
async def enrich(contact_id: int, db: AsyncSession = Depends(get_db)):
    """Enrich a single CRM contact with Apollo data."""
    result = await enrich_contact(db, contact_id)
    if result is None:
        return {"enriched": False, "reason": "Apollo not configured or contact has no email"}
    await db.commit()
    return {"enriched": True, "contact_id": contact_id}


@router.post("/telegram/webhook")
async def telegram_webhook(update: dict, db: AsyncSession = Depends(get_db)):
    """Receive Telegram bot webhook updates."""
    from app.services.notifications.telegram_bot import handle_update
    await handle_update(update, db)
    await db.commit()
    return {"ok": True}


@router.post("/telegram/webhook/register")
async def register_telegram_webhook(
    webhook_url: str = Query(..., description="Public HTTPS URL for Telegram to POST updates"),
):
    """Register a webhook URL with Telegram."""
    from app.services.notifications.telegram_bot import set_webhook
    result = await set_webhook(webhook_url)
    return result


@router.get("/telegram/webhook/info")
async def telegram_webhook_info():
    from app.services.notifications.telegram_bot import get_webhook_info
    return await get_webhook_info()
