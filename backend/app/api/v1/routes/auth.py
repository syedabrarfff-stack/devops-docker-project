"""
OAuth2 authentication routes.
GET  /auth/gmail/status      — check if Gmail OAuth is connected
GET  /auth/gmail/initiate    — get OAuth consent URL
GET  /auth/gmail/callback    — exchange code for tokens (redirect target)
POST /auth/gmail/revoke      — revoke and delete tokens
GET  /auth/gmail/profile     — get connected Gmail profile
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.services.auth.gmail_oauth import (
    get_oauth_url, exchange_code, get_gmail_profile,
    is_oauth_connected, _is_oauth_configured,
)
from app.services.storage.secure import get_oauth_token, delete_credential

router = APIRouter(prefix="/auth", tags=["Auth"])

_DEFAULT_REDIRECT = lambda: f"{settings.APP_BASE_URL}/api/v1/auth/gmail/callback"


@router.get("/gmail/status")
async def gmail_status(db: AsyncSession = Depends(get_db)):
    token_data = await get_oauth_token(db, "gmail", "primary")
    connected = is_oauth_connected(token_data)
    profile = await get_gmail_profile(db) if connected else None
    return {
        "oauth_configured": _is_oauth_configured(),
        "connected": connected,
        "email": profile.get("emailAddress") if profile else None,
        "send_method": "gmail_api" if connected else "smtp",
    }


@router.get("/gmail/initiate")
async def gmail_initiate(
    redirect_uri: str = Query(None),
    state: str = Query("jarvis"),
):
    if not _is_oauth_configured():
        raise HTTPException(400, "GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET not configured")
    url = get_oauth_url(state=state, redirect_uri=redirect_uri or _DEFAULT_REDIRECT())
    return {"auth_url": url}


@router.get("/gmail/callback")
async def gmail_callback(
    code: str = Query(...),
    state: str = Query(""),
    redirect_uri: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Exchange OAuth code for tokens. Redirects to dashboard on success."""
    if not _is_oauth_configured():
        raise HTTPException(400, "OAuth not configured")
    try:
        data = await exchange_code(code, redirect_uri or _DEFAULT_REDIRECT(), db)
        await db.commit()
        # Redirect to dashboard with success indicator
        frontend_url = settings.CORS_ORIGINS.split(",")[0].strip()
        return RedirectResponse(url=f"{frontend_url}?gmail_connected=1")
    except Exception as e:
        raise HTTPException(400, f"Token exchange failed: {e}")


@router.post("/gmail/revoke")
async def gmail_revoke(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select, delete
    from app.models.credentials import OAuthToken
    await db.execute(
        delete(OAuthToken)
        .where(OAuthToken.provider == "gmail")
        .where(OAuthToken.account == "primary")
    )
    await db.commit()
    return {"revoked": True}


@router.get("/gmail/profile")
async def gmail_profile(db: AsyncSession = Depends(get_db)):
    profile = await get_gmail_profile(db)
    if not profile:
        raise HTTPException(404, "Gmail not connected")
    return profile
