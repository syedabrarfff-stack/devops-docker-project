import secrets
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError, jwt
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.core.rate_limit import limiter
from app.models.tenant import Tenant
from app.services.tenancy import TenantManager


router = APIRouter(prefix="/admin/tenants", tags=["Tenancy"])


class CreateTenantRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    plan_tier: str = Field(default="STARTER")
    admin_email: str = Field(..., max_length=255)
    admin_password: str = Field(..., min_length=12, max_length=200)

    @field_validator("admin_email")
    @classmethod
    def validate_admin_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            raise ValueError("A valid admin email is required")
        return email


class TenantLimitsRequest(BaseModel):
    max_leads: int | None = Field(default=None, ge=0)
    max_agents: int | None = Field(default=None, ge=0)
    max_ai_calls: int | None = Field(default=None, ge=0)


class RotateApiKeyRequest(BaseModel):
    name: str = Field(default="rotated", max_length=120)


async def require_captain(request: Request) -> bool:
    configured_token = settings.CAPTAIN_ADMIN_TOKEN
    provided_token = request.headers.get("X-Captain-Token", "")
    if configured_token and secrets.compare_digest(provided_token, configured_token):
        return True

    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        try:
            claims = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            role = str(claims.get("role") or "").upper()
            if claims.get("is_captain") is True or role == "CAPTAIN":
                return True
        except JWTError:
            pass

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Captain authorization required",
    )


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_tenant(
    request: Request,
    payload: CreateTenantRequest,
    _: bool = Depends(require_captain),
):
    manager = TenantManager()
    try:
        tenant, user = await manager.create_tenant(
            name=payload.name,
            plan_tier=payload.plan_tier,
            admin_email=payload.admin_email,
            admin_password=payload.admin_password,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    return {
        "tenant": _tenant_payload(tenant),
        "admin_user": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "is_captain": user.is_captain,
        },
        "api_key": getattr(tenant, "_plain_api_key", None),
        "api_key_visible_once": True,
    }


@router.get("")
async def list_tenants(_: bool = Depends(require_captain)):
    tenants = await TenantManager().list_tenants()
    return {"tenants": [_tenant_payload(tenant) for tenant in tenants]}


@router.put("/{tenant_id}/limits")
@limiter.limit("5/minute")
async def update_tenant_limits(
    request: Request,
    tenant_id: uuid.UUID,
    payload: TenantLimitsRequest,
    _: bool = Depends(require_captain),
):
    limits = payload.model_dump(exclude_none=True)
    try:
        tenant = await TenantManager().update_plan_limits(tenant_id, limits)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return {"tenant": _tenant_payload(tenant)}


@router.post("/{tenant_id}/api-key")
@limiter.limit("3/minute")
async def rotate_tenant_api_key(
    request: Request,
    tenant_id: uuid.UUID,
    payload: RotateApiKeyRequest | None = None,
    _: bool = Depends(require_captain),
):
    try:
        key_record, api_key = await TenantManager().rotate_api_key(
            tenant_id,
            name=(payload.name if payload else "rotated"),
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    return {
        "tenant_id": str(tenant_id),
        "api_key": api_key,
        "api_key_visible_once": True,
        "key_prefix": key_record.key_prefix,
        "key_name": key_record.name,
    }


def _tenant_payload(tenant: Tenant) -> dict[str, Any]:
    settings_payload = tenant.settings or {}
    return {
        "id": str(tenant.id),
        "tenant_id": str(tenant.tenant_id),
        "name": tenant.name,
        "slug": tenant.slug,
        "plan_tier": tenant.plan_tier.value,
        "limits": settings_payload.get("limits"),
        "is_active": tenant.is_active,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        "updated_at": tenant.updated_at.isoformat() if tenant.updated_at else None,
        "provisioned": {
            "personas": len(settings_payload.get("personas") or []),
            "agent_configs": len(settings_payload.get("agent_configs") or []),
            "service_catalog_entries": len(settings_payload.get("service_catalog") or []),
            "governance_rules": len(settings_payload.get("governance_rules") or []),
        },
    }
