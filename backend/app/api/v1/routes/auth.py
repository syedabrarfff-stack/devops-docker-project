"""Legacy auth routes retained for compatibility.

The outbound email architecture has moved to AWS SES, so legacy mailbox OAuth
endpoints are now deprecated and disabled.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.outreach.email_transport import get_outbound_email_status

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/gmail/status")
async def gmail_status(db: AsyncSession = Depends(get_db)):
    status = await get_outbound_email_status(validate_provider=True)
    return {
        "connected": bool(status.get("connected")),
        "enabled": bool(status.get("connected")),
        "provider": "ses",
        "message": "AWS SES is the active outbound provider. Legacy mailbox OAuth is retired.",
        "legacy_google_oauth": False,
        "executive_identity": {
            "name": status.get("from_name"),
            "title": status.get("from_title"),
            "email": status.get("from_email"),
        },
    }


@router.get("/gmail/initiate")
async def gmail_initiate():
    raise HTTPException(status_code=410, detail="Legacy mailbox OAuth is retired. Use AWS SES instead.")


@router.get("/gmail/callback")
async def gmail_callback():
    raise HTTPException(status_code=410, detail="Legacy mailbox OAuth is retired. Use AWS SES instead.")


@router.post("/gmail/revoke")
async def gmail_revoke():
    return {"revoked": False, "message": "Legacy mailbox OAuth is retired. No tokens are stored."}


@router.get("/gmail/profile")
async def gmail_profile():
    raise HTTPException(status_code=404, detail="Legacy mailbox OAuth is retired.")
