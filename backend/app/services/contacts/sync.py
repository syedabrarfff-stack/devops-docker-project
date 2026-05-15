"""
Contact synchronization — Apollo.io → JARVIS CRM.
Pulls people matching ICP, creates/updates contacts and companies.
"""
import logging
from typing import Optional
import httpx
from app.services.storage.secure import get_credential

logger = logging.getLogger(__name__)

APOLLO_BASE = "https://api.apollo.io/v1"


async def _apollo_key(db) -> Optional[str]:
    key = await get_credential(db, "APOLLO_API_KEY")
    return key.strip() if key else None


async def _apollo_search(db, payload: dict) -> dict:
    api_key = await _apollo_key(db)
    if not api_key:
        return {}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{APOLLO_BASE}/mixed_people/search",
                headers={
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                    "X-Api-Key": api_key,
                },
                json=payload,
            )
            return r.json() if r.status_code == 200 else {}
    except Exception as e:
        logger.warning(f"Apollo search failed: {e}")
        return {}


async def sync_from_apollo(db, limit: int = 50,
                            industries: Optional[list] = None,
                            countries: Optional[list] = None) -> int:
    """Fetch leads from Apollo and upsert into JARVIS CRM."""
    industries = industries or ["SaaS", "Software", "Hotel", "Hospitality",
                                 "Healthcare", "Staffing"]
    countries  = countries  or ["US", "CA", "GB", "AU", "NZ", "DE", "IE", "SG"]

    per_page = min(limit, 25)
    pages = max(1, min(4, (limit + per_page - 1) // per_page))
    count = 0

    for page in range(1, pages + 1):
        data = await _apollo_search(db, {
        "person_titles":      ["CEO", "CTO", "Founder", "VP Engineering", "Head of Operations"],
        "organization_num_employees_ranges": ["1,50", "51,200"],
        "person_locations":   countries,
        "organization_industries": industries,
            "per_page": per_page,
            "page": page,
        })

        people = data.get("people", [])
        if not people:
            break
        for person in people:
            if count >= limit:
                break
            try:
                synced = await _upsert_contact(db, person)
                await _upsert_lead(db, person)
                if synced:
                    count += 1
            except Exception as e:
                logger.warning(f"Contact sync error for {person.get('name')}: {e}")

    logger.info(f"Apollo sync: {count} contacts upserted")
    return count


async def _upsert_contact(db, person: dict) -> bool:
    """Upsert a single Apollo person into JARVIS CRM."""
    from sqlalchemy import select
    from app.models.crm import Contact, Company

    email = (person.get("email") or "").strip().lower()
    name  = person.get("name") or "Unknown"
    org   = person.get("organization") or {}
    org_name = org.get("name", "")

    # Find or create company
    company_id = None
    if org_name:
        company = (await db.execute(
            select(Company).where(Company.name == org_name)
        )).scalar_one_or_none()
        if not company:
            company = Company(
                name=org_name,
                domain=org.get("website_url"),
                industry=_first(org.get("industries")),
                country=person.get("country"),
                size=_size_range(org.get("num_employees")),
            )
            db.add(company)
            await db.flush()
        company_id = company.id

    # Check if contact already exists
    existing = None
    if email:
        existing = (await db.execute(
            select(Contact).where(Contact.email == email)
        )).scalar_one_or_none()

    if existing:
        if company_id and not existing.company_id:
            existing.company_id = company_id
        return False  # already exists

    contact = Contact(
        name=name,
        email=email or None,
        title=person.get("title"),
        linkedin=person.get("linkedin_url"),
        company_id=company_id,
        country=person.get("country"),
        source="apollo",
        status="lead",
        tags=["apollo-sync"],
    )
    db.add(contact)
    await db.flush()
    return True


async def _upsert_lead(db, person: dict) -> bool:
    """Create a Lead row as well as the CRM contact so dashboards and scoring work."""
    from sqlalchemy import select
    from app.models.lead import Lead

    email = (person.get("email") or "").strip().lower()
    org = person.get("organization") or {}
    company = org.get("name") or person.get("organization_name") or "Unknown company"
    website = org.get("website_url") or org.get("primary_domain")
    industry = _first(org.get("industries"))

    existing = None
    if email:
        existing = (await db.execute(
            select(Lead).where(Lead.email == email)
        )).scalar_one_or_none()
    if existing:
        return False

    lead = Lead(
        company=company,
        company_name=company,
        contact_name=person.get("name"),
        email=email or None,
        contact_email=email or None,
        website=website,
        company_website=website,
        industry=industry,
        country=person.get("country"),
        status="new",
        source="apollo",
        pain_points=[],
        opportunity_type="AI automation and cloud operations",
        notes=f"Imported from Apollo. Title: {person.get('title') or 'unknown'}",
        metadata_={
            "apollo_person_id": person.get("id"),
            "linkedin_url": person.get("linkedin_url"),
            "organization": {
                "name": company,
                "size": _size_range(org.get("num_employees")),
                "domain": org.get("primary_domain"),
            },
        },
    )
    db.add(lead)
    await db.flush()
    return True


async def enrich_contact(db, contact_id: int) -> Optional[dict]:
    """Enrich a CRM contact with Apollo data."""
    from sqlalchemy import select
    from app.models.crm import Contact
    contact = (await db.execute(select(Contact).where(Contact.id == contact_id))).scalar_one_or_none()
    if not contact or not contact.email:
        return None

    api_key = await _apollo_key(db)
    if not api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{APOLLO_BASE}/people/match",
                headers={"Content-Type": "application/json", "X-Api-Key": api_key},
                json={"email": contact.email},
            )
            if r.status_code != 200:
                return None
            data = r.json().get("person", {})

        contact.linkedin = data.get("linkedin_url") or contact.linkedin
        contact.title    = data.get("title")        or contact.title
        if not contact.tags:
            contact.tags = []
        if "apollo-enriched" not in contact.tags:
            contact.tags = contact.tags + ["apollo-enriched"]
        await db.flush()
        return data
    except Exception as e:
        logger.warning(f"Apollo enrich failed for {contact.email}: {e}")
        return None


def _first(lst) -> Optional[str]:
    if isinstance(lst, list) and lst:
        return lst[0]
    return None


def _size_range(num: Optional[int]) -> Optional[str]:
    if not num:
        return None
    if num < 10:    return "1-10"
    if num < 50:    return "10-50"
    if num < 200:   return "50-200"
    if num < 1000:  return "200-1000"
    return "1000+"
