"""
OAuth2 authentication routes.
GET  /auth/gmail/status      — check if Gmail OAuth is connected
GET  /auth/gmail/initiate    — get OAuth consent URL
GET  /auth/gmail/callback    — exchange code for tokens (redirect target)
POST /auth/gmail/revoke      — revoke and delete tokens
GET  /auth/gmail/profile     — get connected Gmail profile
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.services.auth.gmail_oauth import (
    get_oauth_url, exchange_code, get_gmail_profile,
    is_oauth_connected, _is_oauth_configured,
)
from app.services.storage.secure import get_oauth_token, delete_credential

router = APIRouter(prefix="/auth", tags=["Auth"])

def _public_base_url(request: Request | None = None) -> str:
    configured = (settings.APP_BASE_URL or "").rstrip("/")
    if configured and "localhost" not in configured and "127.0.0.1" not in configured:
        return configured
    if request is not None:
        proto = request.headers.get("X-Forwarded-Proto") or request.url.scheme
        host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host")
        if host:
            return f"{proto}://{host}".rstrip("/")
    return configured or "https://aliyarsolutions.com"


def _default_redirect(request: Request | None = None) -> str:
    return f"{_public_base_url(request)}/api/v1/auth/gmail/callback"


def _frontend_redirect(request: Request | None = None) -> str:
    base = _public_base_url(request)
    return f"{base}/outreach?gmail_connected=1"


def _gmail_success_html(request: Request | None = None) -> str:
    origin = _public_base_url(request)
    fallback = _frontend_redirect(request)
    return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Gmail connected</title>
    <style>
      body {{ background:#07111f; color:#e8f2ff; font-family:Arial,sans-serif; display:grid; place-items:center; min-height:100vh; margin:0; }}
      main {{ max-width:520px; padding:32px; border:1px solid rgba(255,255,255,.12); border-radius:18px; background:rgba(255,255,255,.06); }}
      h1 {{ margin:0 0 10px; font-size:24px; }}
      p {{ color:rgba(232,242,255,.72); line-height:1.5; }}
      a {{ color:#7dd3fc; }}
    </style>
  </head>
  <body>
    <main>
      <h1>Gmail connected</h1>
      <p>JARVIS has stored the Gmail authorization. You can return to Outreach now.</p>
      <p><a href="{fallback}">Open Outreach</a></p>
    </main>
    <script>
      const message = {{ type: "jarvis:gmail-connected", connected: true }};
      try {{
        if (window.opener && !window.opener.closed) {{
          window.opener.postMessage(message, "{origin}");
          window.close();
        }}
      }} catch (error) {{}}
      setTimeout(() => {{ window.location.href = "{fallback}"; }}, 1200);
    </script>
  </body>
</html>"""


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
    request: Request,
    redirect_uri: str = Query(None),
    state: str = Query("jarvis"),
):
    if not _is_oauth_configured():
        raise HTTPException(400, "GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET not configured")
    final_redirect_uri = redirect_uri or _default_redirect(request)
    url = get_oauth_url(state=state, redirect_uri=final_redirect_uri)
    return {"auth_url": url, "redirect_uri": final_redirect_uri}


@router.get("/gmail/callback")
async def gmail_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(""),
    redirect_uri: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Exchange OAuth code for tokens. Redirects to dashboard on success."""
    if not _is_oauth_configured():
        raise HTTPException(400, "OAuth not configured")
    try:
        await exchange_code(code, redirect_uri or _default_redirect(request), db)
        await db.commit()
        return HTMLResponse(_gmail_success_html(request))
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
