import redis.asyncio as redis_lib
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, get_current_user, verify_password
from app.models.user import User

router = APIRouter(tags=["auth"])
settings = get_settings()

LOGIN_MAX_ATTEMPTS = 8
LOGIN_WINDOW_SECONDS = 300


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
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    await _check_login_rate_limit(f"{payload.email}:{client_ip}")

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "clinic_id": user.clinic_id,
        "organization_id": user.organization_id,
    })

    return LoginResponse(
        access_token=token,
        role=user.role,
        clinic_id=user.clinic_id,
        organization_id=user.organization_id,
        full_name=user.full_name,
    )


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user
