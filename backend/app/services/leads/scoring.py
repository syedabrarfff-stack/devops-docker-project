from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select

from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.lead import Lead, LeadStatus
from app.models.outreach import FollowUpQueue, FollowUpStatus

logger = logging.getLogger(__name__)

ALIYAR_ICP = {
    "target_industries": [
        "e-commerce",
        "real estate",
        "consulting",
        "professional services",
        "SaaS",
        "healthcare",
        "logistics",
        "education",
        "finance",
        "retail",
    ],
    "target_countries": ["UK", "UAE", "USA", "Australia", "Canada", "Bahrain", "Europe"],
    "company_size": {"min_employees": 5, "max_employees": 200},
    "revenue_range": {"min_usd": 500000, "max_usd": 50000000},
    "pain_points": [
        "manual processes",
        "no automation",
        "poor lead generation",
        "no AI systems",
        "no tech team",
        "scaling problems",
    ],
    "disqualifiers": ["competitor", "no budget", "too large enterprise", "government"],
    "min_score_for_outreach": 60,
}

SCORING_WEIGHTS = {
    "industry_match": 25,
    "country_match": 20,
    "size_fit": 20,
    "pain_point_match": 25,
    "contact_quality": 10,
}

SALES_PERSONA = "Darren Mitchell"


class LeadScoringEngine:
    async def score_against_icp(self, lead: dict) -> tuple[float, dict]:
        text = _flatten_text(lead)
        disqualifiers = [
            item for item in ALIYAR_ICP["disqualifiers"]
            if item.lower() in text
        ]
        if disqualifiers:
            return 0.0, {
                "total": 0.0,
                "disqualified": True,
                "disqualifiers": disqualifiers,
                "components": _empty_components(),
                "decision": "blocked",
                "reason": "Lead matches ICP disqualifier.",
            }

        industry_score, industry_reason = _score_industry(lead)
        country_score, country_reason = _score_country(lead)
        size_score, size_reason = _score_size(lead)
        pain_score, pain_reason = _score_pain_points(lead)
        contact_score, contact_reason = _score_contact_quality(lead)
        total = round(industry_score + country_score + size_score + pain_score + contact_score, 1)

        reasoning = {
            "total": total,
            "disqualified": False,
            "components": {
                "industry_match": {"score": industry_score, "max": 25, "reason": industry_reason},
                "country_match": {"score": country_score, "max": 20, "reason": country_reason},
                "size_fit": {"score": size_score, "max": 20, "reason": size_reason},
                "pain_point_match": {"score": pain_score, "max": 25, "reason": pain_reason},
                "contact_quality": {"score": contact_score, "max": 10, "reason": contact_reason},
            },
            "decision": "promote" if total >= ALIYAR_ICP["min_score_for_outreach"] else "hold",
            "min_score_for_outreach": ALIYAR_ICP["min_score_for_outreach"],
        }
        return total, reasoning

    async def batch_score(self, leads: list[dict], tenant_id) -> list[Lead]:
        tenant_uuid = uuid.UUID(str(tenant_id))
        scored_leads: list[Lead] = []

        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                for lead_data in leads:
                    score, reasoning = await self.score_against_icp(lead_data)
                    lead = await self._upsert_lead(session, tenant_uuid, lead_data, score, reasoning)
                    scored_leads.append(lead)

        return sorted(scored_leads, key=lambda lead: lead.score or 0, reverse=True)

    async def promote_to_pipeline(self, lead_id, tenant_id) -> Lead:
        tenant_uuid = uuid.UUID(str(tenant_id))
        lead_uuid = uuid.UUID(str(lead_id))

        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                lead = await session.scalar(
                    select(Lead).where(Lead.tenant_id == tenant_uuid, Lead.id == lead_uuid)
                )
                if not lead:
                    raise ValueError("Lead not found")

                if (lead.score or 0) < ALIYAR_ICP["min_score_for_outreach"]:
                    await self._audit(
                        session,
                        tenant_uuid,
                        "lead_promotion_held",
                        lead.id,
                        {"score": lead.score, "threshold": ALIYAR_ICP["min_score_for_outreach"]},
                    )
                    return lead

                lead.status = LeadStatus.CONTACTED
                lead.assigned_persona = SALES_PERSONA
                lead.enrichment_data = {
                    **(lead.enrichment_data or {}),
                    "pipeline": {
                        "promoted_at": datetime.now(UTC).isoformat(),
                        "assigned_persona": SALES_PERSONA,
                        "promotion_reason": "ICP score met outreach threshold.",
                    },
                }

                existing_queue = await session.scalar(
                    select(FollowUpQueue.id)
                    .where(
                        FollowUpQueue.tenant_id == tenant_uuid,
                        FollowUpQueue.lead_id == lead.id,
                        FollowUpQueue.sequence_step == 1,
                        FollowUpQueue.status == FollowUpStatus.PENDING,
                    )
                    .limit(1)
                )
                if not existing_queue:
                    session.add(
                        FollowUpQueue(
                            tenant_id=tenant_uuid,
                            lead_id=lead.id,
                            sequence_step=1,
                            scheduled_at=datetime.now(UTC),
                            status=FollowUpStatus.PENDING,
                        )
                    )

                await self._audit(
                    session,
                    tenant_uuid,
                    "lead_promoted_to_pipeline",
                    lead.id,
                    {
                        "score": lead.score,
                        "assigned_persona": SALES_PERSONA,
                        "queued_sequence_step": 1,
                    },
                )
                return lead

    async def score_yesterday_new_leads(self, tenant_id, promote_limit: int = 20) -> int:
        tenant_uuid = uuid.UUID(str(tenant_id))
        now = datetime.now(UTC)
        yesterday_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_end = yesterday_start + timedelta(days=1)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                rows = (
                    await session.execute(
                        select(Lead)
                        .where(
                            Lead.tenant_id == tenant_uuid,
                            Lead.status == LeadStatus.NEW,
                            Lead.created_at >= yesterday_start,
                            Lead.created_at < yesterday_end,
                        )
                        .order_by(Lead.created_at.asc())
                    )
                ).scalars().all()

                for lead in rows:
                    score, reasoning = await self.score_against_icp(_lead_to_dict(lead))
                    lead.score = score
                    lead.enrichment_data = {
                        **(lead.enrichment_data or {}),
                        "icp_scoring": reasoning,
                    }
                    await self._audit(
                        session,
                        tenant_uuid,
                        "lead_icp_scored",
                        lead.id,
                        {"score": score, "reasoning": reasoning},
                    )

                top_leads = sorted(rows, key=lambda lead: lead.score or 0, reverse=True)[:promote_limit]
                promoted = 0
                for lead in top_leads:
                    if (lead.score or 0) >= ALIYAR_ICP["min_score_for_outreach"]:
                        lead.status = LeadStatus.CONTACTED
                        lead.assigned_persona = SALES_PERSONA
                        existing_queue = await session.scalar(
                            select(FollowUpQueue.id)
                            .where(
                                FollowUpQueue.tenant_id == tenant_uuid,
                                FollowUpQueue.lead_id == lead.id,
                                FollowUpQueue.sequence_step == 1,
                                FollowUpQueue.status == FollowUpStatus.PENDING,
                            )
                            .limit(1)
                        )
                        if not existing_queue:
                            session.add(
                                FollowUpQueue(
                                    tenant_id=tenant_uuid,
                                    lead_id=lead.id,
                                    sequence_step=1,
                                    scheduled_at=datetime.now(UTC),
                                    status=FollowUpStatus.PENDING,
                                )
                            )
                            promoted += 1

                if promoted:
                    session.add(
                        AuditLog(
                            tenant_id=tenant_uuid,
                            action="daily_lead_scoring_completed",
                            entity_type="lead",
                            actor="LeadScoringEngine",
                            after_json={"scored": len(rows), "promoted": promoted},
                            details={"promote_limit": promote_limit},
                        )
                    )

        return promoted

    async def _upsert_lead(self, session, tenant_id: uuid.UUID, data: dict, score: float, reasoning: dict) -> Lead:
        existing = await self._find_existing_lead(session, tenant_id, data)
        if existing:
            existing.score = score
            existing.enrichment_data = {
                **(existing.enrichment_data or {}),
                "icp_scoring": reasoning,
                "latest_batch_payload": data,
            }
            await self._audit(
                session,
                tenant_id,
                "lead_icp_rescored",
                existing.id,
                {"score": score, "reasoning": reasoning},
            )
            return existing

        company_name = data.get("company_name") or data.get("company") or data.get("organization_name")
        email = data.get("email") or data.get("contact_email") or data.get("decision_maker_email")
        website = data.get("website") or data.get("company_website") or data.get("domain")
        lead = Lead(
            tenant_id=tenant_id,
            company_name=company_name,
            company=company_name,
            contact_name=data.get("contact_name") or data.get("decision_maker_name"),
            email=email,
            contact_email=email,
            phone=data.get("phone"),
            country=data.get("country"),
            industry=data.get("industry") or data.get("sector"),
            score=score,
            status=LeadStatus.NEW,
            source=data.get("source") or "icp_batch",
            pain_points=_as_list(data.get("pain_points")),
            enrichment_data={**data, "icp_scoring": reasoning},
            website=website,
            company_website=website,
            opportunity_type=data.get("opportunity_type"),
            notes=data.get("notes"),
        )
        session.add(lead)
        await session.flush()
        await self._audit(
            session,
            tenant_id,
            "lead_icp_scored",
            lead.id,
            {"score": score, "reasoning": reasoning},
        )
        return lead

    async def _find_existing_lead(self, session, tenant_id: uuid.UUID, data: dict) -> Lead | None:
        conditions = []
        for column, value in (
            (Lead.email, data.get("email") or data.get("contact_email") or data.get("decision_maker_email")),
            (Lead.website, data.get("website") or data.get("domain")),
            (Lead.company_name, data.get("company_name") or data.get("company")),
        ):
            normalized = _clean_lower(value)
            if normalized:
                conditions.append(func.lower(column) == normalized)
        if not conditions:
            return None
        return await session.scalar(
            select(Lead).where(Lead.tenant_id == tenant_id, or_(*conditions)).limit(1)
        )

    async def _audit(self, session, tenant_id: uuid.UUID, action: str, lead_id: uuid.UUID, payload: dict) -> None:
        session.add(
            AuditLog(
                tenant_id=tenant_id,
                action=action,
                entity_type="lead",
                entity_id=lead_id,
                actor="LeadScoringEngine",
                after_json=payload,
                details=payload,
            )
        )


def _score_industry(lead: dict) -> tuple[float, str]:
    haystack = " ".join(str(lead.get(key) or "") for key in ("industry", "sector", "company_name", "notes")).lower()
    matches = [industry for industry in ALIYAR_ICP["target_industries"] if industry.lower() in haystack]
    if matches:
        return 25.0, f"Industry matches target ICP: {', '.join(matches)}."
    if any(word in haystack for word in ["clinic", "agency", "software", "commerce", "property", "restaurant", "hotel"]):
        return 15.0, "Industry is adjacent to target service markets."
    return 0.0, "No clear target industry match."


def _score_country(lead: dict) -> tuple[float, str]:
    country = str(lead.get("country") or lead.get("location") or "").lower()
    if any(target.lower() in country for target in ALIYAR_ICP["target_countries"]):
        return 20.0, "Country matches priority market."
    if any(word in country for word in ["england", "scotland", "wales", "dubai", "abu dhabi", "united states"]):
        return 20.0, "Country maps to a priority market."
    if country:
        return 8.0, "Country is known but outside primary market list."
    return 0.0, "Country is missing."


def _score_size(lead: dict) -> tuple[float, str]:
    employees = _extract_number(
        lead.get("employee_count")
        or lead.get("employees")
        or lead.get("size")
        or lead.get("company_size")
    )
    revenue = _extract_money(lead.get("estimated_revenue") or lead.get("revenue") or lead.get("revenue_range"))
    bounds = ALIYAR_ICP["company_size"]
    revenue_bounds = ALIYAR_ICP["revenue_range"]

    employee_score = 4.0
    employee_reason = "Company size is unknown."
    if employees is not None:
        if bounds["min_employees"] <= employees <= bounds["max_employees"]:
            employee_score = 12.0
            employee_reason = f"Employee count {employees} fits target range."
        elif 1 <= employees < bounds["min_employees"] or bounds["max_employees"] < employees <= 500:
            employee_score = 6.0
            employee_reason = f"Employee count {employees} is near target range."
        else:
            employee_score = 0.0
            employee_reason = f"Employee count {employees} is outside target range."

    revenue_score = 4.0
    revenue_reason = "Revenue is unknown."
    if revenue is not None:
        if revenue_bounds["min_usd"] <= revenue <= revenue_bounds["max_usd"]:
            revenue_score = 8.0
            revenue_reason = "Revenue fits target range."
        elif revenue < revenue_bounds["min_usd"] or revenue <= 100000000:
            revenue_score = 3.0
            revenue_reason = "Revenue is near target range."
        else:
            revenue_score = 0.0
            revenue_reason = "Revenue is outside target range."

    return min(employee_score + revenue_score, 20.0), f"{employee_reason} {revenue_reason}"


def _score_pain_points(lead: dict) -> tuple[float, str]:
    pain_values = _as_list(lead.get("pain_points"))
    haystack = f"{' '.join(str(item) for item in pain_values)} {lead.get('notes') or ''} {lead.get('opportunity_type') or ''}".lower()
    matches = [pain for pain in ALIYAR_ICP["pain_points"] if pain.lower() in haystack]
    if matches:
        return min(25.0, 10.0 + len(matches) * 5.0), f"Pain points match ICP: {', '.join(matches)}."
    if any(word in haystack for word in ["manual", "slow", "missed calls", "spreadsheet", "crm", "booking", "operations"]):
        return 15.0, "Pain signals indicate an automation or operations gap."
    return 0.0, "No strong pain signal found."


def _score_contact_quality(lead: dict) -> tuple[float, str]:
    score = 0.0
    reasons = []
    if lead.get("email") or lead.get("contact_email") or lead.get("decision_maker_email"):
        score += 4.0
        reasons.append("email")
    if lead.get("contact_name") or lead.get("decision_maker_name"):
        score += 2.0
        reasons.append("contact name")
    title = str(lead.get("title") or lead.get("decision_maker_title") or "").lower()
    if any(role in title for role in ["ceo", "founder", "director", "vp", "owner", "head"]):
        score += 3.0
        reasons.append("decision-maker title")
    if lead.get("phone") or lead.get("linkedin_url") or lead.get("decision_maker_linkedin"):
        score += 1.0
        reasons.append("secondary contact path")
    return min(score, 10.0), f"Contact quality: {', '.join(reasons)}." if reasons else "No contact details."


def _lead_to_dict(lead: Lead) -> dict:
    return {
        "company_name": lead.company_name or lead.company,
        "contact_name": lead.contact_name,
        "email": lead.email or lead.contact_email,
        "phone": lead.phone,
        "country": lead.country,
        "industry": lead.industry,
        "employee_count": (lead.enrichment_data or {}).get("employee_count"),
        "estimated_revenue": (lead.enrichment_data or {}).get("estimated_revenue"),
        "pain_points": lead.pain_points or [],
        "website": lead.website or lead.company_website,
        "opportunity_type": lead.opportunity_type,
        "notes": lead.notes,
    }


def _empty_components() -> dict:
    return {
        key: {"score": 0.0, "max": max_score, "reason": "Lead disqualified."}
        for key, max_score in SCORING_WEIGHTS.items()
    }


def _flatten_text(lead: dict) -> str:
    values = []
    for value in lead.values():
        if isinstance(value, list):
            values.extend(str(item) for item in value)
        elif isinstance(value, dict):
            values.append(_flatten_text(value))
        else:
            values.append(str(value or ""))
    return " ".join(values).lower()


def _extract_number(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).replace(",", "")
    match = re.search(r"\d+", text)
    return int(match.group(0)) if match else None


def _extract_money(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)

    text = str(value).strip().lower().replace(",", "").replace("$", "")
    match = re.search(r"(\d+(?:\.\d+)?)\s*([kmb])?", text)
    if not match:
        return None

    amount = float(match.group(1))
    suffix = match.group(2)
    if suffix == "k":
        amount *= 1_000
    elif suffix == "m":
        amount *= 1_000_000
    elif suffix == "b":
        amount *= 1_000_000_000
    return int(amount)


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _clean_lower(value: Any) -> str | None:
    if not value:
        return None
    return str(value).strip().lower()


lead_scoring_engine = LeadScoringEngine()
