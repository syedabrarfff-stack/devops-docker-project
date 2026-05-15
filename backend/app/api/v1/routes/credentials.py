from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.services.operations.capabilities import CREDENTIAL_SPECS, credential_status
from app.services.storage.secure import delete_credential, set_credential


router = APIRouter(prefix="/credentials", tags=["Credentials"])

ALLOWED_KEYS = {spec.key for spec in CREDENTIAL_SPECS}


class CredentialUpsert(BaseModel):
    key: str = Field(..., min_length=2, max_length=120)
    value: str = Field(..., min_length=1, max_length=5000)


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db)):
    return {"credentials": await credential_status(db)}


@router.post("/bootstrap-env")
async def bootstrap_from_environment(db: AsyncSession = Depends(get_db)):
    """
    Copy credentials that already exist in server environment/settings into the
    encrypted credential vault. This lets JARVIS self-connect anything the
    server already has without exposing secret values to the browser.
    """
    imported: list[str] = []
    skipped: list[str] = []

    defaults = {
        "N8N_BASE_URL": settings.N8N_BASE_URL,
        "N8N_WEBHOOK_BASE_URL": settings.N8N_WEBHOOK_BASE_URL or settings.N8N_BASE_URL.rstrip("/") + "/webhook",
    }

    for spec in CREDENTIAL_SPECS:
        value = defaults.get(spec.key) or getattr(settings, spec.key, None)
        if value:
            await set_credential(db, spec.key, str(value))
            imported.append(spec.key)
        else:
            skipped.append(spec.key)

    await db.commit()
    return {
        "imported": imported,
        "skipped": skipped,
        "message": "Jarvis imported every credential already available in the server environment. Skipped keys require account authorization or manual key creation.",
    }


@router.post("")
async def upsert_credential(payload: CredentialUpsert, db: AsyncSession = Depends(get_db)):
    key = payload.key.strip().upper()
    if key not in ALLOWED_KEYS:
        raise HTTPException(400, f"Unsupported credential key: {key}")
    await set_credential(db, key, payload.value.strip())
    await db.commit()
    return {"key": key, "configured": True}


@router.delete("/{key}")
async def revoke_credential(key: str, db: AsyncSession = Depends(get_db)):
    key = key.strip().upper()
    if key not in ALLOWED_KEYS:
        raise HTTPException(400, f"Unsupported credential key: {key}")
    await delete_credential(db, key)
    await db.commit()
    return {"key": key, "configured": False}
