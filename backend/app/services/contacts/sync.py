"""
Contact synchronization — Apollo.io → JARVIS CRM.
Pulls people matching ICP, creates/updates contacts and companies.
"""
import logging
from typing import Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

APOLLO_BASE = "https://api.apollo.io/v1"


async def _apollo_search(payload: dict) -> dict:
    if not settings.APOLLO_API_KEY:
        return {}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{APOLLO_BASE}/mixed_people/search",
                headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
                json={**payload, "api_key": settings.APOLLO_API_KEY},
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

    data = await _apollo_search({
        "person_titles":      ["CEO", "CTO", "Founder", "VP Engineering", "Head of Operations"],
        "organization_num_employees_ranges": ["1,50", "51,200"],
        "person_locations":   countries,
        "organization_industries": industries,
        "per_page": min(limit, 25),
        "page": 1,
    })

    people = data.get("people", [])
    count = 0
    for person in people:
        try:
            synced = await _upsert_contact(db, person)
            if synced:
                count += 1
        except Exception as e:
            logger.warning(f"Contact sync error for {person.get('name')}: {e}")

    logger.info(f"Apollo sync: {count}/{len(people)} contacts upserted")
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


async def enrich_contact(db, contact_id: int) -> Optional[dict]:
    """Enrich a CRM contact with Apollo data."""
    from sqlalchemy import select
    from app.models.crm import Contact
    contact = (await db.execute(select(Contact).where(Contact.id == contact_id))).scalar_one_or_none()
    if not contact or not contact.email:
        return None

    if not settings.APOLLO_API_KEY:
        return None

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{APOLLO_BASE}/people/match",
                json={"email": contact.email, "api_key": settings.APOLLO_API_KEY},
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
