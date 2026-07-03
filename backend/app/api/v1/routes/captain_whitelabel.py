"""R6-3 Route: Captain White-label Licensing Management.

Captain-only endpoints for managing white-label tenants,
license keys, plan upgrades, and MRR reporting.

All routes require Captain JWT.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routes.auth import get_current_captain
from app.core.database import get_db
from app.services.whitelabel.license_manager import license_manager

router = APIRouter(
    prefix="/captain/licensing",
    tags=["Captain — White-label Licensing"],
    dependencies=[Depends(get_current_captain)],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class ProvisionRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    admin_email: str = Field(min_length=5, max_length=255)
    plan_tier: str = Field(default="STARTER", max_length=50)


class PlanUpgradeRequest(BaseModel):
    new_plan: str = Field(max_length=50)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/tenants")
async def provision_tenant(
    body: ProvisionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Provision a new white-label tenant with a fresh license key."""
    try:
        return await license_manager.provision_tenant(
            company_name=body.company_name,
            admin_email=body.admin_email,
            plan_tier=body.plan_tier,
            session=db,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/tenants")
async def list_tenants(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List all white-label tenants (paginated)."""
    return await license_manager.list_tenants(db, page=page, per_page=per_page)


@router.post("/tenants/{tenant_id}/license/rotate")
async def rotate_license_key(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Invalidate the existing license key and issue a new one."""
    return await license_manager.rotate_license_key(tenant_id, db)


@router.put("/tenants/{tenant_id}/plan")
async def upgrade_plan(
    tenant_id: UUID,
    body: PlanUpgradeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Upgrade or downgrade a tenant's plan tier."""
    try:
        return await license_manager.upgrade_plan(tenant_id, body.new_plan, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/mrr")
async def mrr_snapshot(db: AsyncSession = Depends(get_db)):
    """MRR snapshot: revenue by plan tier and total recurring revenue."""
    return await license_manager.get_mrr_snapshot(db)


@router.post("/license/validate")
async def validate_license(
    license_key: str,
    db: AsyncSession = Depends(get_db),
):
    """Validate a license key and return tenant metadata."""
    result = await license_manager.validate_license(license_key, db)
    if not result:
        raise HTTPException(status_code=404, detail="Invalid or inactive license key")
    return result
