"""
Aliyar Solutions Service Catalog API - canonical 25 AIONX capability modules.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.catalog.catalog_service import (
    get_all_divisions,
    get_division_by_code,
    get_groups,
    update_division,
    get_catalog_stats,
    get_capability_modules,
    seed_catalog,
    sync_canonical_catalog,
)

router = APIRouter(prefix="/catalog", tags=["Service Catalog"])


@router.get("/divisions")
async def list_divisions(
    group: Optional[str] = None,
    featured_only: bool = False,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    await seed_catalog(db)
    divisions = await get_all_divisions(db, group=group, featured_only=featured_only, active_only=active_only)
    return {
        "divisions": [_serialize(d) for d in divisions],
        "total": len(divisions),
    }


@router.get("/divisions/{code}")
async def get_division(code: str, db: AsyncSession = Depends(get_db)):
    division = await get_division_by_code(db, code.upper())
    if not division:
        raise HTTPException(status_code=404, detail=f"Division '{code}' not found")
    return _serialize(division)


@router.get("/groups")
async def list_groups(db: AsyncSession = Depends(get_db)):
    await seed_catalog(db)
    groups = await get_groups(db)
    return {"groups": groups}


@router.get("/stats")
async def catalog_stats(db: AsyncSession = Depends(get_db)):
    await seed_catalog(db)
    return await get_catalog_stats(db)


@router.get("/capability-modules")
async def capability_modules():
    """Canonical AIONX service catalog: 25 capability modules with HIA ownership."""
    return get_capability_modules()


@router.post("/seed")
async def trigger_seed(db: AsyncSession = Depends(get_db)):
    """Force re-seed if catalog is empty. Idempotent — skips if already seeded."""
    return await sync_canonical_catalog(db)


@router.post("/sync-canonical")
async def trigger_canonical_sync(db: AsyncSession = Depends(get_db)):
    """Delete legacy catalog rows and repopulate the finalized 25 capability modules."""
    return await sync_canonical_catalog(db)


@router.patch("/divisions/{code}")
async def update_service(code: str, payload: dict, db: AsyncSession = Depends(get_db)):
    allowed = {"name", "description", "price_range_usd", "pricing_model", "duration_estimate", "is_active", "is_featured"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    division = await update_division(db, code.upper(), **updates)
    if not division:
        raise HTTPException(status_code=404, detail=f"Division '{code}' not found")
    return _serialize(division)


def _serialize(d) -> dict:
    return {
        "id": d.id,
        "code": d.code,
        "name": d.name,
        "division_group": d.division_group,
        "description": d.description,
        "deliverables": d.deliverables or [],
        "technologies": d.technologies or [],
        "target_industries": d.target_industries or [],
        "pricing_model": d.pricing_model,
        "price_range_usd": d.price_range_usd or {},
        "duration_estimate": d.duration_estimate,
        "is_active": d.is_active,
        "is_featured": d.is_featured,
        "sort_order": d.sort_order,
    }
