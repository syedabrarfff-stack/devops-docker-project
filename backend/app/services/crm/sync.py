"""Bridges the Lead pipeline into the CRM (Contact/Company/Deal) tables.

The Lead pipeline (UUID-keyed, tenant-scoped) and the CRM tables (integer-keyed,
single-tenant) were built independently — nothing ever wrote from one into the
other, so the CRM tab stayed empty no matter how active real outreach was. This
gives a lead a CRM footprint the moment it receives real outreach.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import Company, Contact, Deal
from app.models.lead import Lead

logger = logging.getLogger(__name__)


async def sync_lead_to_crm(db: AsyncSession, lead: Lead) -> None:
    """Upsert a Company/Contact/Deal for a lead that has just received real outreach.

    Best-effort — callers should invoke this after their own commit/flush and
    wrap it in a try/except so a CRM sync issue never blocks or fails an
    outreach send.
    """
    if not lead.email:
        return

    company = None
    if lead.company_name:
        result = await db.execute(select(Company).where(Company.name == lead.company_name))
        company = result.scalar_one_or_none()
        if company is None:
            company = Company(
                name=lead.company_name,
                industry=lead.industry,
                country=lead.country,
                status="prospect",
                score=int(lead.score or 0),
            )
            db.add(company)
            await db.flush()

    result = await db.execute(select(Contact).where(Contact.email == lead.email))
    contact = result.scalar_one_or_none()
    if contact is None:
        contact = Contact(
            name=lead.contact_name or lead.company_name or lead.email,
            email=lead.email,
            phone=lead.phone,
            company_id=company.id if company else None,
            country=lead.country,
            status="prospect",
            score=int(lead.score or 0),
            source=lead.source or "outreach",
            last_contacted=lead.last_contact,
        )
        db.add(contact)
        await db.flush()
    else:
        contact.score = max(contact.score or 0, int(lead.score or 0))
        contact.last_contacted = lead.last_contact

    existing_deal = await db.execute(
        select(Deal).where(
            Deal.contact_id == contact.id,
            Deal.stage.notin_(["closed_won", "closed_lost"]),
        )
    )
    if existing_deal.scalar_one_or_none() is None:
        db.add(Deal(
            title=f"{lead.company_name or contact.name} — {lead.industry or 'Engagement'}",
            contact_id=contact.id,
            company_id=company.id if company else None,
            stage="discovery",
            probability=10,
            service_type=lead.industry,
        ))
        await db.flush()
