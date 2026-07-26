from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_current_user
from app.models.user import User

router = APIRouter(tags=["auth"])


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
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
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
