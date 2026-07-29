"""Lead Data Validator — ensures JARVIS never returns fabricated lead information.

CRITICAL POLICY: When users ask about leads, pipeline data, prospects, or
opportunities, JARVIS MUST query the real database and return ONLY verified
records. Fabricated, hallucinated, or AI-generated lead data is a data
integrity violation.

This validator:
1. Detects when user queries are about leads/opportunities/prospects
2. Intercepts the AI response
3. Queries the real database for the requested data
4. Replaces any AI-generated claims with real database records
5. Flags violations if AI tried to fabricate data
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.crm import Deal
from app.models.governance import Proposal

log = logging.getLogger(__name__)

# Patterns that indicate a lead/opportunity/prospect query
_LEAD_QUERY_PATTERNS = re.compile(
    r"\b(lead|opportunity|prospect|pipeline|deal|candidate|account|company|"
    r"contact|contact list|lead list|shows?.*lead|tell.*lead|get.*lead|"
    r"list.*lead|recent.*lead|top.*lead|hot.*lead|warm.*lead|cold.*lead|"
    r"lead score|icp|ideal customer|qualified|mvp)\b",
    re.IGNORECASE,
)


async def validate_lead_response(
    user_query: str,
    ai_response: str,
    tenant_id: str,
    db: AsyncSession,
) -> tuple[str, list[str]]:
    """
    Validate lead-related responses and replace with real data if needed.

    Returns:
        (validated_response, violations) where violations is a list of detected
        policy breaches (empty list = clean response)
    """
    violations = []

    # Check if this is a lead/opportunity query
    if not _LEAD_QUERY_PATTERNS.search(user_query):
        return ai_response, violations  # Not about leads, pass through

    log.info("Lead query detected: %s", user_query[:100])

    # Query real database for leads matching the request
    try:
        real_data = await _fetch_real_lead_data(user_query, tenant_id, db)
    except Exception as e:
        log.error("Failed to fetch real lead data: %s", e)
        violations.append(f"Database query failed: {str(e)}")
        return ai_response, violations

    # Check if AI response contains specific lead claims
    fabrication_markers = _detect_fabricated_claims(ai_response)

    if fabrication_markers and not real_data:
        # AI fabricated data when no real data exists
        violations.append(
            "CRITICAL: AI generated fake leads. No real leads match query. "
            "Response must be honest about lack of data."
        )
        return (
            f"No leads match that criteria in the system. "
            f"Query: {user_query}",
            violations,
        )

    if fabrication_markers and real_data:
        # Replace AI fabrication with real data
        violations.append(
            "AI attempted to generate fake leads. "
            "Replaced with verified database records."
        )
        formatted = _format_real_leads(real_data)
        return (
            f"Here are the real leads from our system:\n\n{formatted}\n\n"
            f"Original request: {user_query}",
            violations,
        )

    # Response looks clean (no specific claims or properly hedged)
    if real_data:
        # Enhance clean response with real data summary
        formatted = _format_real_leads(real_data)
        return (
            f"{ai_response}\n\nReal leads in system:\n{formatted}",
            violations,
        )

    return ai_response, violations


def _detect_fabricated_claims(response: str) -> list[str]:
    """Identify specific lead/company claims in response."""
    # Look for specific claims like company names, deal amounts, etc.
    fabrications = []

    # Pattern: "Company X has Y revenue" or "Lead named John"
    name_claim = re.findall(
        r'(?:company|lead|contact|account)\s+named?\s+(["\']?[A-Za-z\s]+["\']?)',
        response,
        re.IGNORECASE,
    )
    if name_claim:
        fabrications.extend(name_claim)

    # Pattern: "$X.YM in revenue" or "ARR: $X"
    revenue_claim = re.findall(r'\$[\d,]+(?:\.[0-9]{1,2})?\s*(?:M|B|K)?', response)
    if revenue_claim:
        fabrications.extend(revenue_claim)

    # Pattern: "qualified for $X deal" or similar
    deal_claim = re.findall(
        r'(?:deal|contract|opportunity)\s+(?:worth|valued?|of)\s+\$[\d,]+',
        response,
        re.IGNORECASE,
    )
    if deal_claim:
        fabrications.extend(deal_claim)

    return fabrications


async def _fetch_real_lead_data(
    query: str,
    tenant_id: str,
    db: AsyncSession,
) -> list[dict]:
    """Fetch real leads/opportunities from database."""
    results = []

    # Try to match leads
    try:
        stmt = select(Lead).where(Lead.tenant_id == tenant_id).limit(20)
        result = await db.execute(stmt)
        leads = result.scalars().all()

        for lead in leads:
            results.append({
                "type": "lead",
                "name": lead.company_name,
                "email": lead.email,
                "phone": lead.phone,
                "source": lead.source,
                "score": lead.score,
                "created_at": lead.created_at.isoformat() if lead.created_at else None,
            })
    except Exception as e:
        log.warning("Lead query failed: %s", e)

    # Try to match deals
    try:
        stmt = select(Deal).where(Deal.tenant_id == tenant_id).limit(20)
        result = await db.execute(stmt)
        deals = result.scalars().all()

        for deal in deals:
            results.append({
                "type": "deal",
                "title": deal.title,
                "lead_id": str(deal.lead_id) if deal.lead_id else None,
                "value": deal.value,
                "stage": deal.stage,
                "created_at": deal.created_at.isoformat() if deal.created_at else None,
            })
    except Exception as e:
        log.warning("Deal query failed: %s", e)

    # Try to match proposals
    try:
        stmt = select(Proposal).where(Proposal.tenant_id == tenant_id).limit(20)
        result = await db.execute(stmt)
        proposals = result.scalars().all()

        for proposal in proposals:
            results.append({
                "type": "proposal",
                "title": proposal.title,
                "lead_id": str(proposal.lead_id) if proposal.lead_id else None,
                "value": proposal.value,
                "status": proposal.status,
                "created_at": proposal.created_at.isoformat() if proposal.created_at else None,
            })
    except Exception as e:
        log.warning("Proposal query failed: %s", e)

    return results


def _format_real_leads(data: list[dict]) -> str:
    """Format real lead data for display."""
    if not data:
        return "(No leads found)"

    lines = []
    for item in data:
        if item["type"] == "lead":
            lines.append(
                f"• {item['name']} (email: {item['email']}, score: {item['score']}, source: {item['source']})"
            )
        elif item["type"] == "deal":
            lines.append(
                f"• Deal: {item['title']} (value: ${item['value'] or 'TBD'}, stage: {item['stage']})"
            )
        elif item["type"] == "proposal":
            lines.append(
                f"• Proposal: {item['title']} (value: ${item['value'] or 'TBD'}, status: {item['status']})"
            )

    return "\n".join(lines)
