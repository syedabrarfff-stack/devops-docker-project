import redis.asyncio as redis_lib
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, get_current_user, verify_password
from app.models.user import User
from app.services.refresh_tokens import (
    consume_refresh_token,
    issue_refresh_token,
    revoke_refresh_token,
)

router = APIRouter(tags=["auth"])
settings = get_settings()

REFRESH_COOKIE_NAME = "sarah_refresh"

LOGIN_MAX_ATTEMPTS = 8
LOGIN_WINDOW_SECONDS = 300

# A precomputed bcrypt hash of a value nobody can type (never matches any real
# password), used only to give the "no such user" login path the same bcrypt
# cost as a real comparison. Fixed rather than hashed at import time so it
# costs nothing extra per request, and identical process-to-process.
_DUMMY_HASH = "$2b$12$2/f.sDv9fZqEogfcEWIZY.nTamxBuXJxrUSzzrBFBSFnkZNw/HvHa"


async def _check_login_rate_limit(key: str) -> None:
    r = redis_lib.from_url(settings.redis_url)
    try:
        attempts = await r.incr(f"login:attempts:{key}")
        if attempts == 1:
            await r.expire(f"login:attempts:{key}", LOGIN_WINDOW_SECONDS)
        if attempts > LOGIN_MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Try again in a few minutes.",
            )
    finally:
        await r.aclose()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    clinic_id: str | None
    organization_id: str | None
    full_name: str


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    await _check_login_rate_limit(f"{payload.email}:{client_ip}")

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    # A nonexistent email must take the same time as a wrong password on a real
    # one -- skipping bcrypt here would make "no such user" measurably faster
    # than "wrong password", letting an attacker enumerate registered emails
    # (relevant on a system handling patient/clinic PII) purely from response
    # timing. verify_password always runs, against a dummy hash when there's
    # no real user to compare against.
    password_ok = verify_password(payload.password, user.hashed_password if user else _DUMMY_HASH)

    if not user or not password_ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    access_token = _mint_access_token(user)
    refresh_token = await issue_refresh_token(user.id)
    _set_refresh_cookie(response, refresh_token)

    return LoginResponse(
        access_token=access_token,
        role=user.role,
        clinic_id=user.clinic_id,
        organization_id=user.organization_id,
        full_name=user.full_name,
    )


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    response: Response,
    db: AsyncSession = Depends(get_db),
    sarah_refresh: str | None = Cookie(default=None),
):
    """Rotate the refresh token and mint a new short-lived access token.

    The old refresh token is consumed (deleted) inside consume_refresh_token
    -- one-shot use. A stolen token is therefore useful for at most one
    refresh; the legitimate client's next attempt will fail, which is the
    observable signal that theft happened.

    Returns 401 rather than 403 on invalid/expired cookies so the frontend
    can distinguish "session over, redirect to login" from "user lacks
    permission" cleanly.
    """
    if not sarah_refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh cookie")

    user_id = await consume_refresh_token(sarah_refresh)
    if not user_id:
        # Clear the bad cookie so the client doesn't keep sending it.
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalid or expired")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer active")

    new_refresh = await issue_refresh_token(user.id)
    _set_refresh_cookie(response, new_refresh)
    return RefreshResponse(access_token=_mint_access_token(user))


@router.post("/logout")
async def logout(response: Response, sarah_refresh: str | None = Cookie(default=None)):
    """Revoke the refresh token and clear the cookie. Idempotent: logging
    out when already logged out is not an error."""
    if sarah_refresh:
        await revoke_refresh_token(sarah_refresh)
    _clear_refresh_cookie(response)
    return {"status": "logged_out"}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user


def _mint_access_token(user: User) -> str:
    return create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "clinic_id": user.clinic_id,
        "organization_id": user.organization_id,
    })


def _set_refresh_cookie(response: Response, token: str) -> None:
    """SameSite=None + Secure is intentional: app./admin./sarah. are
    different subdomains of aliyarsolutions.com, and a Strict/Lax cookie
    would not be sent on the app. -> sarah. cross-subdomain refresh call.
    Secure is non-negotiable when SameSite=None; both portals are HTTPS-only
    in prod, and local dev uses samesite=Lax via the settings default."""
    same_site = "none" if settings.is_production else "lax"
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.is_production,
        samesite=same_site,
        domain=settings.refresh_cookie_domain or None,
        path="/api/v1/auth",  # cookie is only sent to auth endpoints, minimizing exposure
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        domain=settings.refresh_cookie_domain or None,
        path="/api/v1/auth",
    )
