from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from app.config.settings import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    return decode_token(credentials.credentials)


async def get_scoped_clinic_id(
    clinic_id: str | None = Query(
        default=None,
        description="Clinic to view. Required for platform_admin callers; ignored (the "
        "caller's own clinic is used) for clinic-user callers.",
    ),
    current_user: dict = Depends(get_current_user),
) -> str:
    """Resolve which clinic a request is scoped to.

    Clinic users are hard-scoped to the clinic_id baked into their JWT --
    the query param is ignored for them so a clinic user can never read
    another clinic's data by editing the URL. platform_admin tokens carry
    no clinic_id (an admin isn't a member of any one clinic), so admin
    requests must name the clinic explicitly via ?clinic_id=; this is how
    the admin console's per-clinic dashboard view works.
    """
    if current_user.get("role") == "platform_admin":
        if not clinic_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="clinic_id query parameter is required for admin access",
            )
        return clinic_id
    own_clinic_id = current_user.get("clinic_id")
    if not own_clinic_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No clinic access")
    return own_clinic_id


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "platform_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
