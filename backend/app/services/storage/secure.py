"""
Secure credential storage — HMAC-SHA256-CTR encryption (pure Python stdlib).
Local SQLite storage + optional AWS SSM mirror.
Uses only hashlib/hmac/os/base64 — no C-extension dependencies.

Usage:
    await set_credential(db, "GMAIL_REFRESH_TOKEN", value)
    val = await get_credential(db, "GMAIL_REFRESH_TOKEN")
"""
import os
import hmac
import hashlib
import struct
import base64
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Pure-stdlib encryption (HMAC-SHA256 as PRF in counter mode) ──────────────

def _derive_key(secret: str) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", secret.encode(), b"jarvis-aliyar-salt-v1", 100_000)


_KEY: Optional[bytes] = None

def _key() -> bytes:
    global _KEY
    if _KEY is None:
        _KEY = _derive_key(settings.SECRET_KEY)
    return _KEY


def _prf(key: bytes, nonce: bytes, counter: int) -> bytes:
    msg = nonce + struct.pack(">Q", counter)
    return hmac.new(key, msg, hashlib.sha256).digest()


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    stream = bytearray()
    counter = 0
    while len(stream) < length:
        stream.extend(_prf(key, nonce, counter))
        counter += 1
    return bytes(stream[:length])


def encrypt(plaintext: str) -> str:
    """Encrypt a string → base64-encoded (nonce + ciphertext)."""
    data   = plaintext.encode("utf-8")
    nonce  = os.urandom(16)
    stream = _keystream(_key(), nonce, len(data))
    ct     = bytes(a ^ b for a, b in zip(data, stream))
    return base64.urlsafe_b64encode(nonce + ct).decode()


def decrypt(token: str) -> str:
    """Decrypt a base64-encoded token → plaintext string."""
    raw    = base64.urlsafe_b64decode(token.encode())
    nonce, ct = raw[:16], raw[16:]
    stream = _keystream(_key(), nonce, len(ct))
    return bytes(a ^ b for a, b in zip(ct, stream)).decode("utf-8")


# ── AWS SSM (no-op when USE_AWS=false or boto3 unavailable) ──────────────────

def _ssm_get(key: str) -> Optional[str]:
    if not settings.USE_AWS:
        return None
    try:
        import boto3
        ssm = boto3.client(
            "ssm", region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        r = ssm.get_parameter(Name=f"{settings.AWS_SSM_PREFIX}/{key}", WithDecryption=True)
        return r["Parameter"]["Value"]
    except Exception as e:
        logger.debug(f"SSM get {key} skipped: {e}")
        return None


def _ssm_put(key: str, value: str) -> bool:
    if not settings.USE_AWS:
        return False
    try:
        import boto3
        ssm = boto3.client(
            "ssm", region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        ssm.put_parameter(
            Name=f"{settings.AWS_SSM_PREFIX}/{key}", Value=value,
            Type="SecureString", Overwrite=True,
        )
        return True
    except Exception as e:
        logger.debug(f"SSM put {key} skipped: {e}")
        return False


# ── Public async API ──────────────────────────────────────────────────────────

async def get_credential(db, key: str) -> Optional[str]:
    """Retrieve: encrypted DB → AWS SSM → settings attr."""
    from sqlalchemy import select
    from app.models.credentials import SecureCredential
    row = (await db.execute(
        select(SecureCredential).where(SecureCredential.key == key)
    )).scalar_one_or_none()
    if row:
        try:
            return decrypt(row.value)
        except Exception:
            pass
    ssm_val = _ssm_get(key)
    if ssm_val:
        return ssm_val
    return getattr(settings, key, None)


async def set_credential(db, key: str, value: str) -> None:
    from sqlalchemy import select
    from app.models.credentials import SecureCredential
    enc = encrypt(value)
    row = (await db.execute(
        select(SecureCredential).where(SecureCredential.key == key)
    )).scalar_one_or_none()
    if row:
        row.value = enc
    else:
        db.add(SecureCredential(key=key, value=enc, source="local"))
    await db.flush()
    _ssm_put(key, value)


async def delete_credential(db, key: str) -> None:
    from sqlalchemy import delete
    from app.models.credentials import SecureCredential
    await db.execute(delete(SecureCredential).where(SecureCredential.key == key))
    await db.flush()


# ── OAuth token helpers ───────────────────────────────────────────────────────

async def store_oauth_token(db, provider: str, account: str,
                             access_token: str,
                             refresh_token: Optional[str] = None,
                             expiry=None, scopes: Optional[str] = None) -> None:
    from sqlalchemy import select
    from app.models.credentials import OAuthToken
    row = (await db.execute(
        select(OAuthToken)
        .where(OAuthToken.provider == provider, OAuthToken.account == account)
    )).scalar_one_or_none()
    if row:
        row.access_token  = encrypt(access_token)
        row.refresh_token = encrypt(refresh_token) if refresh_token else row.refresh_token
        row.token_expiry  = expiry
        row.scopes        = scopes or row.scopes
        row.is_valid      = True
    else:
        db.add(OAuthToken(
            provider=provider, account=account,
            access_token=encrypt(access_token),
            refresh_token=encrypt(refresh_token) if refresh_token else None,
            token_expiry=expiry, scopes=scopes, is_valid=True,
        ))
    await db.flush()


async def get_oauth_token(db, provider: str, account: str) -> Optional[dict]:
    from sqlalchemy import select
    from app.models.credentials import OAuthToken
    row = (await db.execute(
        select(OAuthToken)
        .where(OAuthToken.provider == provider, OAuthToken.account == account)
    )).scalar_one_or_none()
    if not row or not row.is_valid:
        return None
    try:
        return {
            "access_token":  decrypt(row.access_token),
            "refresh_token": decrypt(row.refresh_token) if row.refresh_token else None,
            "expiry":        row.token_expiry,
            "scopes":        row.scopes,
        }
    except Exception:
        return None
