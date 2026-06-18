"""Auth routes — captain login and legacy Gmail OAuth compatibility stubs."""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.services.outreach.email_transport import get_outbound_email_status

router = APIRouter(prefix="/auth", tags=["Auth"])

_bearer = HTTPBearer(auto_error=False)


async def get_current_captain(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> dict:
    """FastAPI dependency — validates Captain JWT and returns payload."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        if payload.get("role") != "captain":
            raise HTTPException(status_code=403, detail="Not authorised")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=1, max_length=256)

    @field_validator("username", "password")
    @classmethod
    def no_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v


@router.post("/login")
async def captain_login(req: LoginRequest):
    """Authenticate Captain and return a signed JWT for subsequent API calls."""
    username_ok = secrets.compare_digest(
        req.username.strip().lower(), settings.CAPTAIN_USERNAME.lower()
    )
    password_ok = secrets.compare_digest(req.password, settings.CAPTAIN_PASSWORD)
    if not (username_ok and password_ok):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": "captain",
        "tenant_id": settings.JARVIS_DEFAULT_TENANT_ID or "captain",
        "role": "captain",
        "jti": secrets.token_hex(16),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=7)).timestamp()),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return {
        "token": token,
        "user": "captain",
        "expires_in_days": 7,
        "system": "JARVIS",
    }


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
