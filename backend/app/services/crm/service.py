"""
CRM service — contacts, companies, deals.
All write operations require Captain approval for bulk actions.
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.models.crm import Contact, Company, Deal

logger = logging.getLogger(__name__)


# ── Contacts ─────────────────────────────────────────────────────────────────

async def create_contact(db: AsyncSession, data: dict) -> Contact:
    c = Contact(**{k: v for k, v in data.items() if hasattr(Contact, k)})
    db.add(c)
    await db.flush()
    await db.refresh(c)
    return c


async def get_contact(db: AsyncSession, contact_id: int) -> Optional[Contact]:
    r = await db.execute(select(Contact).where(Contact.id == contact_id))
    return r.scalar_one_or_none()


async def list_contacts(db: AsyncSession, status: Optional[str] = None,
                        company_id: Optional[int] = None,
                        limit: int = 50, offset: int = 0) -> list[Contact]:
    q = select(Contact).order_by(desc(Contact.created_at)).limit(limit).offset(offset)
    if status:
        q = q.where(Contact.status == status)
    if company_id is not None:
        q = q.where(Contact.company_id == company_id)
    r = await db.execute(q)
    return list(r.scalars().all())


async def update_contact(db: AsyncSession, contact_id: int, data: dict) -> Optional[Contact]:
    c = await get_contact(db, contact_id)
    if not c:
        return None
    for k, v in data.items():
        if hasattr(c, k):
            setattr(c, k, v)
    await db.flush()
    return c


async def delete_contact(db: AsyncSession, contact_id: int) -> bool:
    c = await get_contact(db, contact_id)
    if not c:
        return False
    await db.delete(c)
    return True


async def contact_stats(db: AsyncSession) -> dict:
    rows = (await db.execute(
        select(Contact.status, func.count().label("n"))
        .group_by(Contact.status)
    )).all()
    by_status = {s: 0 for s in ("lead", "prospect", "qualified", "client", "churned")}
    total = 0
    for status, count in rows:
        if status in by_status:
            by_status[status] = count
        total += count
    return {"total": total, "by_status": by_status}


# ── Companies ─────────────────────────────────────────────────────────────────

async def create_company(db: AsyncSession, data: dict) -> Company:
    c = Company(**{k: v for k, v in data.items() if hasattr(Company, k)})
    db.add(c)
    await db.flush()
    await db.refresh(c)
    return c


async def list_companies(
    db: AsyncSession,
    industry: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Company]:
    q = select(Company).order_by(desc(Company.score)).limit(limit).offset(offset)
    if industry:
        q = q.where(Company.industry == industry)
    if country:
        q = q.where(Company.country == country)
    r = await db.execute(q)
    return list(r.scalars().all())


async def get_company(db: AsyncSession, company_id: int) -> Optional[Company]:
    r = await db.execute(select(Company).where(Company.id == company_id))
    return r.scalar_one_or_none()


# ── Deals ─────────────────────────────────────────────────────────────────────

async def create_deal(db: AsyncSession, data: dict) -> Deal:
    d = Deal(**{k: v for k, v in data.items() if hasattr(Deal, k)})
    db.add(d)
    await db.flush()
    await db.refresh(d)
    return d


async def list_deals(db: AsyncSession, stage: Optional[str] = None,
                     min_value: float = 0,
                     limit: int = 50) -> list[Deal]:
    q = select(Deal).order_by(desc(Deal.value)).limit(limit)
    if stage:
        q = q.where(Deal.stage == stage)
    if min_value:
        q = q.where(Deal.value >= min_value)
    r = await db.execute(q)
    return list(r.scalars().all())


async def update_deal(db: AsyncSession, deal_id: int, data: dict) -> Optional[Deal]:
    r = await db.execute(select(Deal).where(Deal.id == deal_id))
    d = r.scalar_one_or_none()
    if not d:
        return None
    for k, v in data.items():
        if hasattr(d, k):
            setattr(d, k, v)
    await db.flush()
    return d


async def pipeline_stats(db: AsyncSession) -> dict:
    stages = ("discovery", "proposal", "negotiation", "closed_won", "closed_lost")
    rows = (await db.execute(
        select(Deal.stage, func.count().label("n"), func.coalesce(func.sum(Deal.value), 0).label("v"))
        .where(Deal.stage.in_(stages))
        .group_by(Deal.stage)
    )).all()
    agg = {s: (0, 0.0) for s in stages}
    for stage, count, value in rows:
        agg[stage] = (count, float(value))
    pipeline = {s: {"count": agg[s][0], "value": round(agg[s][1], 2)} for s in stages}
    total_value = sum(agg[s][1] for s in stages if s != "closed_lost")
    return {"pipeline": pipeline, "total_pipeline_value": round(total_value, 2)}
