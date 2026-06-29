"""
Contact synchronization routes — Apollo → JARVIS CRM.
"""
import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from app.core.rate_limit import limiter
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db, set_tenant_context
from app.models.compliance import ProcessedWebhook
from app.services.contacts.sync import sync_from_apollo, enrich_contact

router = APIRouter(prefix="/sync", tags=["Sync"])


class SyncConfig(BaseModel):
    industries: Optional[list[str]] = None
    countries: Optional[list[str]] = None
    limit: int = Field(default=50, ge=1, le=200)


@router.post("/apollo")
@limiter.limit("5/minute")
async def run_apollo_sync(request: Request, body: SyncConfig = SyncConfig(), db: AsyncSession = Depends(get_db)):
    """Fetch contacts from Apollo.io and upsert into CRM."""
    count = await sync_from_apollo(
        db, limit=body.limit,
        industries=body.industries,
        countries=body.countries,
    )
    await db.commit()
    return {"synced": count, "source": "apollo"}


@router.post("/enrich/{contact_id}")
@limiter.limit("10/minute")
async def enrich(request: Request, contact_id: int, db: AsyncSession = Depends(get_db)):
    """Enrich a single CRM contact with Apollo data."""
    result = await enrich_contact(db, contact_id)
    if result is None:
        return {"enriched": False, "reason": "Apollo not configured or contact has no email"}
    await db.commit()
    return {"enriched": True, "contact_id": contact_id}


@router.post("/telegram/webhook")
@limiter.limit("60/minute")
async def telegram_webhook(request: Request, update: dict, db: AsyncSession = Depends(get_db)):
    """Receive Telegram bot webhook updates."""
    from app.core.config import settings as _s
    from fastapi import HTTPException
    secret = _s.TELEGRAM_WEBHOOK_SECRET
    if secret:
        provided = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not provided or provided != secret:
            raise HTTPException(status_code=403, detail="Invalid webhook secret")
    from app.services.notifications.telegram_bot import handle_update
    tenant_id = _default_tenant_id()
    payload_json = _stable_json(update)
    event_id = str(update.get("update_id") or hashlib.sha256(payload_json.encode("utf-8")).hexdigest())
    payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    await set_tenant_context(db, str(tenant_id))
    existing = await db.scalar(
        select(ProcessedWebhook.id).where(
            ProcessedWebhook.tenant_id == tenant_id,
            ProcessedWebhook.source == "telegram",
            ProcessedWebhook.event_id == event_id,
        )
    )
    if existing:
        return {"ok": True, "duplicate": True, "event_id": event_id}
    db.add(
        ProcessedWebhook(
            tenant_id=tenant_id,
            source="telegram",
            event_id=event_id,
            processed_at=datetime.now(UTC),
            payload_hash=payload_hash,
            metadata_json={"receiver": "telegram_webhook"},
        )
    )
    await handle_update(update, db)
    await db.commit()
    return {"ok": True, "duplicate": False, "event_id": event_id}


@router.post("/telegram/webhook/register")
@limiter.limit("3/minute")
async def register_telegram_webhook(
    request: Request,
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


def _stable_json(payload: dict) -> str:
    return json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), default=str)


def _default_tenant_id() -> UUID:
    if not settings.JARVIS_DEFAULT_TENANT_ID:
        raise ValueError("JARVIS_DEFAULT_TENANT_ID is required for webhook processing")
    return UUID(str(settings.JARVIS_DEFAULT_TENANT_ID))
