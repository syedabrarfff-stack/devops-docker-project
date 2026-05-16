"""
Safe revenue engine for JARVIS.

The engine may discover, enrich, score, draft, prepare proposals, and open
approval packets automatically. It never sends client-facing messages unless a
Captain-approved approval request is executed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.approval import ApprovalRequest, AuditLog
from app.models.crm import Company, Contact, Deal
from app.models.governance import Proposal
from app.models.notifications import NotificationLog
from app.models.outreach import OutreachEmail, OutreachSequence
from app.services.storage.secure import get_credential

logger = logging.getLogger(__name__)


REVENUE_SEQUENCE_NAME = "JARVIS Revenue Engine - AI Automation"
APPROVAL_TITLE = "Review JARVIS revenue outreach batch"


@dataclass(slots=True)
class RevenueRunResult:
    synced_contacts: int = 0
    fallback_leads: int = 0
    scored_contacts: int = 0
    qualified_contacts: int = 0
    drafts_created: int = 0
    proposals_created: int = 0
    deals_created: int = 0
    approval_id: int | None = None
    blockers: list[str] | None = None

    def as_dict(self) -> dict:
        return {
            "synced_contacts": self.synced_contacts,
            "fallback_leads": self.fallback_leads,
            "scored_contacts": self.scored_contacts,
            "qualified_contacts": self.qualified_contacts,
            "drafts_created": self.drafts_created,
            "proposals_created": self.proposals_created,
            "deals_created": self.deals_created,
            "approval_id": self.approval_id,
            "blockers": self.blockers or [],
        }


async def run_revenue_engine(
    db: AsyncSession,
    *,
    limit: int = 25,
    create_proposals: bool = True,
) -> dict:
    """
    Run the first revenue loop:
    1. Pull fresh Apollo contacts when configured.
    2. Score and qualify contacts.
    3. Create outreach drafts and proposal drafts.
    4. Open one Captain approval packet for review/execution.
    """
    result = RevenueRunResult(blockers=[])

    if await get_credential(db, "APOLLO_API_KEY"):
        try:
            from app.services.contacts.sync import sync_from_apollo, validate_apollo_access

            apollo_ok, apollo_message = await validate_apollo_access(db)
            if apollo_ok:
                result.synced_contacts = await sync_from_apollo(db, limit=limit)
            else:
                result.blockers.append(f"{apollo_message} Public local discovery fallback was used.")
                result.fallback_leads = await _run_public_discovery_fallback(db, limit=limit)
        except Exception as exc:
            logger.warning("Apollo revenue sync failed: %s", exc)
            result.blockers.append("Apollo sync failed; public local discovery fallback was used.")
            result.fallback_leads = await _run_public_discovery_fallback(db, limit=limit)
    else:
        result.blockers.append("APOLLO_API_KEY missing; public local discovery fallback was used.")
        result.fallback_leads = await _run_public_discovery_fallback(db, limit=limit)

    sequence = await _get_or_create_sequence(db)
    lead_contacts = await _promote_qualified_leads_to_contacts(db, limit=limit)
    candidates = await _load_candidate_contacts(db, limit=limit)
    if lead_contacts:
        result.synced_contacts += lead_contacts

    email_ids: list[int] = []
    proposal_ids: list[int] = []
    deal_ids: list[int] = []

    for contact in candidates:
        score, reasons, service_type = _score_contact(contact)
        result.scored_contacts += 1
        contact.score = max(contact.score or 0, score)
        contact.next_action = "Review generated outreach draft for Captain approval"
        contact.tags = _merge_tags(contact.tags, ["revenue-engine", f"score-{score}"])

        if score < 45:
            contact.status = contact.status or "lead"
            continue

        result.qualified_contacts += 1
        if score >= 60 or contact.status == "qualified":
            contact.status = "qualified"
        else:
            contact.status = "prospect"

        deal = await _ensure_deal(db, contact, service_type, score, reasons)
        if deal:
            deal_ids.append(deal.id)
            result.deals_created += 1

        draft = await _ensure_outreach_draft(db, sequence, contact, service_type, reasons)
        if draft:
            email_ids.append(draft.id)
            result.drafts_created += 1

        if create_proposals and score >= 75:
            proposal = await _ensure_proposal_draft(db, contact, service_type, score, reasons)
            if proposal:
                proposal_ids.append(proposal.id)
                result.proposals_created += 1

    if email_ids or proposal_ids or deal_ids or result.blockers:
        approval = await _create_approval_packet(
            db,
            email_ids=email_ids,
            proposal_ids=proposal_ids,
            deal_ids=deal_ids,
            result=result,
        )
        result.approval_id = approval.id
        await _notify_run(db, result, approval.id)

    await db.flush()
    return result.as_dict()


async def execute_approved_outreach_batch(db: AsyncSession, approval_id: int) -> dict:
    """Send the email drafts attached to an approved revenue approval packet."""
    approval = (
        await db.execute(select(ApprovalRequest).where(ApprovalRequest.id == approval_id))
    ).scalar_one_or_none()
    if not approval:
        return {"sent": 0, "failed": 0, "error": "Approval not found."}
    if approval.status != "approved":
        return {"sent": 0, "failed": 0, "error": "Approval must be approved first."}
    if approval.action_type != "revenue_outreach_batch":
        return {"sent": 0, "failed": 0, "error": "Approval is not a revenue outreach batch."}

    email_ids = (approval.payload or {}).get("email_ids") or []
    if not email_ids:
        return {"sent": 0, "failed": 0, "error": "No email drafts attached."}

    from app.services.outreach.gmail import send_outreach_email

    sent = 0
    failed = 0
    for email_id in email_ids:
        email = (
            await db.execute(select(OutreachEmail).where(OutreachEmail.id == int(email_id)))
        ).scalar_one_or_none()
        if not email or email.status not in ("draft", "queued", "scheduled", "failed"):
            continue
        email.status = "queued"
        ok = await send_outreach_email(db, email.id)
        if ok:
            sent += 1
        else:
            failed += 1

    db.add(
        AuditLog(
            action="Executed approved revenue outreach batch",
            approval_id=approval_id,
            details={"email_ids": email_ids, "sent": sent, "failed": failed},
        )
    )
    await db.flush()
    return {"sent": sent, "failed": failed, "approval_id": approval_id}


async def _get_or_create_sequence(db: AsyncSession) -> OutreachSequence:
    sequence = (
        await db.execute(
            select(OutreachSequence).where(OutreachSequence.name == REVENUE_SEQUENCE_NAME)
        )
    ).scalar_one_or_none()
    if sequence:
        return sequence

    sequence = OutreachSequence(
        name=REVENUE_SEQUENCE_NAME,
        target_industry="saas",
        target_country="global",
        target_company_size="1-200",
        service_offered="AI automation and cloud operations",
        status="active",
        total_steps=1,
        steps=[
            {
                "step": 1,
                "delay_days": 0,
                "subject": "Quick idea for {company}",
                "body": "Hi {name},\n\nI noticed {company} may be a fit for a lean automation and cloud operations review. Aliyar Solutions helps teams reduce manual work, improve response time, and make their operations easier to scale without adding headcount.\n\nIf useful, we can send a short audit with the highest-impact automation opportunities for your team.\n\nWarm regards,\nDarren Mitchell\nClient Acquisition Specialist\nAliyar Solutions",
            }
        ],
    )
    db.add(sequence)
    await db.flush()
    return sequence


async def _run_public_discovery_fallback(db: AsyncSession, limit: int) -> int:
    """Keep revenue discovery alive when Apollo search is blocked by plan/API access."""
    try:
        from app.api.v1.routes.discovery import LocalMarketRequest, local_market_discovery

        request = LocalMarketRequest(
            industry="clinics",
            location="New York",
            service_angle="AI receptionist and appointment booking",
            limit=min(max(limit, 5), 20),
        )
        result = await local_market_discovery(request, db)
        return int(result.get("created", 0) or 0) + int(result.get("updated", 0) or 0)
    except Exception as exc:
        logger.warning("Public discovery fallback failed: %s", exc)
        return 0


async def _load_candidate_contacts(db: AsyncSession, limit: int) -> list[Contact]:
    rows = (
        await db.execute(
            select(Contact)
            .options(selectinload(Contact.company))
            .where(Contact.email.is_not(None))
            .where(Contact.status.in_(["lead", "prospect", "qualified"]))
            .order_by(Contact.score.desc(), Contact.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return list(rows)


async def _promote_qualified_leads_to_contacts(db: AsyncSession, limit: int) -> int:
    """Turn existing lead records into CRM contacts so the revenue loop can act."""
    from app.models.lead import Lead

    leads = (
        await db.execute(
            select(Lead)
            .where(Lead.email.is_not(None))
            .where(Lead.status.in_(["new", "qualified"]))
            .order_by(Lead.score.desc(), Lead.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()

    promoted = 0
    for lead in leads:
        email = (lead.email or lead.contact_email or "").strip().lower()
        if not email:
            continue
        existing = (
            await db.execute(select(Contact).where(Contact.email == email))
        ).scalar_one_or_none()
        if existing:
            continue

        company_name = lead.company or lead.company_name
        company_id = None
        if company_name:
            company = (
                await db.execute(select(Company).where(Company.name == company_name))
            ).scalar_one_or_none()
            if not company:
                company = Company(
                    name=company_name,
                    domain=lead.website or lead.company_website,
                    industry=lead.industry,
                    country=lead.country,
                    status="prospect",
                    score=lead.score or 0,
                    pain_points=lead.pain_points or [],
                    notes="Promoted from JARVIS lead record for revenue execution.",
                )
                db.add(company)
                await db.flush()
            company_id = company.id

        contact = Contact(
            name=lead.contact_name or company_name or "Unknown",
            email=email,
            company_id=company_id,
            country=lead.country,
            source=lead.source or "lead",
            status="qualified" if (lead.score or 0) >= 60 or lead.status == "qualified" else "lead",
            score=lead.score or 0,
            tags=_merge_tags(["promoted-from-lead"], [lead.source or "manual"]),
            notes=lead.notes,
            next_action="Review generated outreach draft for Captain approval",
        )
        db.add(contact)
        lead.status = "qualified" if contact.status == "qualified" else lead.status
        promoted += 1
    if promoted:
        await db.flush()
    return promoted


def _score_contact(contact: Contact) -> tuple[int, list[str], str]:
    company = contact.company
    title = (contact.title or "").lower()
    industry = ((company.industry if company else "") or "").lower()
    size = ((company.size if company else "") or "").lower()
    country = (contact.country or (company.country if company else "") or "").lower()

    score = max(45, int(contact.score or 0))
    reasons: list[str] = []
    service_type = "AI automation and cloud operations"

    if any(role in title for role in ("ceo", "founder", "cto", "owner", "operations")):
        score += 20
        reasons.append("Decision-maker title")
    if any(word in industry for word in ("software", "saas", "technology", "staffing", "health", "hotel", "hospitality")):
        score += 18
        reasons.append("ICP industry")
    if any(word in country for word in ("us", "usa", "united states", "gb", "uk", "canada", "australia", "germany", "singapore")):
        score += 8
        reasons.append("Target market")
    if size in ("10-50", "50-200", "51-200", "200-1000"):
        score += 7
        reasons.append("Budget-friendly company size")
    if contact.status == "qualified":
        score += 20
        reasons.append("Already qualified by JARVIS")

    if "hotel" in industry or "hospitality" in industry:
        service_type = "Hotel operations automation"
    elif "staff" in industry or "recruit" in industry:
        service_type = "Recruitment workflow automation"
    elif "software" in industry or "saas" in industry:
        service_type = "SaaS operations automation"

    return min(score, 100), reasons or ["Matches Aliyar Solutions outreach criteria"], service_type


async def _ensure_deal(
    db: AsyncSession,
    contact: Contact,
    service_type: str,
    score: int,
    reasons: Iterable[str],
) -> Deal | None:
    existing = (
        await db.execute(
            select(Deal)
            .where(Deal.contact_id == contact.id)
            .where(Deal.stage.in_(["discovery", "proposal", "negotiation"]))
        )
    ).scalar_one_or_none()
    if existing:
        return None

    company_name = contact.company.name if contact.company else contact.name
    value = _estimate_value(contact, score)
    deal = Deal(
        title=f"{service_type} - {company_name}",
        contact_id=contact.id,
        company_id=contact.company_id,
        value=value,
        currency="USD",
        stage="discovery",
        probability=min(20 + int(score / 3), 60),
        service_type=service_type,
        notes="Auto-created by JARVIS revenue engine. Fit signals: " + ", ".join(reasons),
    )
    db.add(deal)
    await db.flush()
    return deal


async def _ensure_outreach_draft(
    db: AsyncSession,
    sequence: OutreachSequence,
    contact: Contact,
    service_type: str,
    reasons: Iterable[str],
) -> OutreachEmail | None:
    existing = (
        await db.execute(
            select(OutreachEmail)
            .where(OutreachEmail.contact_id == contact.id)
            .where(OutreachEmail.step_number == 1)
            .where(OutreachEmail.status.in_(["draft", "queued", "scheduled", "sent"]))
        )
    ).scalar_one_or_none()
    if existing:
        return None

    company = contact.company
    company_name = company.name if company else "your team"
    industry = company.industry if company else "your industry"
    first_name = (contact.name or "there").split()[0]
    reason_text = ", ".join(reasons)

    subject = f"Quick idea for {company_name}"
    body = (
        f"Hi {first_name},\n\n"
        f"I noticed {company_name} looks like a strong fit for {service_type}. "
        f"The main signals were: {reason_text}.\n\n"
        "Aliyar Solutions helps teams remove manual work, tighten follow-up, and run leaner cloud/AI operations without adding headcount. "
        "If useful, I can send a short audit with the 3 highest-impact automation opportunities for your team.\n\n"
        "Warm regards,\n"
        "Darren Mitchell\n"
        "Client Acquisition Specialist\n"
        "Aliyar Solutions"
    )
    draft = OutreachEmail(
        sequence_id=sequence.id,
        contact_id=contact.id,
        to_email=contact.email or "",
        to_name=contact.name or "",
        subject=subject,
        body=body.replace("{industry}", industry or ""),
        step_number=1,
        status="draft",
        scheduled_at=None,
    )
    db.add(draft)
    await db.flush()
    return draft


async def _ensure_proposal_draft(
    db: AsyncSession,
    contact: Contact,
    service_type: str,
    score: int,
    reasons: Iterable[str],
) -> Proposal | None:
    company_name = contact.company.name if contact.company else contact.name
    existing = (
        await db.execute(
            select(Proposal)
            .where(Proposal.client_email == contact.email)
            .where(Proposal.status == "draft")
        )
    ).scalar_one_or_none()
    if existing:
        return None

    pricing = _pricing_for(contact, score)
    content = (
        f"{contact.name or 'Hello'},\n\n"
        f"Based on our review of {company_name}, we see a strong opportunity to improve operations through {service_type}. "
        f"The strongest fit signals are: {', '.join(reasons)}.\n\n"
        "Recommended scope:\n"
        "1. Map the current workflow and identify manual bottlenecks.\n"
        "2. Build a focused automation layer for lead handling, reporting, and follow-up.\n"
        "3. Deploy a monitored cloud workflow with clear handover and support.\n\n"
        f"Investment: setup ${pricing['setup_fee']} with optional monthly support from ${pricing['monthly_retainer']}.\n"
        "The goal is to recover the investment through saved hours, faster response time, and better sales follow-up.\n\n"
        "Warm regards,\n"
        "Aliyar Solutions Team"
    )
    proposal = Proposal(
        title=f"{service_type} - {company_name}",
        client_name=contact.name,
        client_email=contact.email,
        client_company=company_name,
        service_type=service_type,
        proposal_style="short_urgent",
        pricing=pricing,
        content=content,
        ai_generated=False,
        status="draft",
    )
    db.add(proposal)
    await db.flush()
    return proposal


async def _create_approval_packet(
    db: AsyncSession,
    *,
    email_ids: list[int],
    proposal_ids: list[int],
    deal_ids: list[int],
    result: RevenueRunResult,
) -> ApprovalRequest:
    blockers = result.blockers or []
    summary = (
        f"JARVIS prepared {result.drafts_created} outreach drafts, "
        f"{result.proposals_created} proposal drafts, and {result.deals_created} pipeline deals. "
        "Approve this packet only after reviewing the drafts."
    )
    if blockers:
        summary += " Blockers: " + "; ".join(blockers)

    if not email_ids and not proposal_ids and not deal_ids:
        existing_packets = (
            await db.execute(
                select(ApprovalRequest)
                .where(ApprovalRequest.title == APPROVAL_TITLE)
                .where(ApprovalRequest.action_type == "revenue_outreach_batch")
                .where(ApprovalRequest.status == "pending")
                .order_by(ApprovalRequest.created_at.desc())
            )
        ).scalars().all()
        existing = existing_packets[0] if existing_packets else None
        for stale in existing_packets[1:]:
            stale.status = "rejected"
            stale.captain_note = "Superseded by a newer JARVIS revenue approval packet."
            stale.approved_at = datetime.now(timezone.utc)
        if existing:
            existing.summary = summary
            existing.payload = {
                **(existing.payload or {}),
                "result": result.as_dict(),
                "requires_manual_review": True,
            }
            await db.flush()
            return existing

    approval = ApprovalRequest(
        title=APPROVAL_TITLE,
        action_type="revenue_outreach_batch",
        summary=summary,
        risk_level="medium",
        benefits="Starts the revenue loop while keeping all client-facing sends under Captain approval.",
        risks="Cold outreach can harm trust if sent without review; Gmail credentials must be valid before execution.",
        rollback_plan="Reject the approval packet, edit/delete drafts, or pause the revenue scheduler job.",
        payload={
            "email_ids": email_ids,
            "proposal_ids": proposal_ids,
            "deal_ids": deal_ids,
            "result": result.as_dict(),
            "requires_manual_review": True,
        },
        status="pending",
    )
    db.add(approval)
    await db.flush()
    return approval


async def _notify_run(db: AsyncSession, result: RevenueRunResult, approval_id: int) -> None:
    body = (
        f"Scored {result.scored_contacts} contacts, qualified {result.qualified_contacts}, "
        f"created {result.drafts_created} drafts and {result.proposals_created} proposals. "
        f"Approval #{approval_id} is waiting."
    )
    if result.blockers:
        body += " Blockers: " + "; ".join(result.blockers)
    db.add(
        NotificationLog(
            channel="dashboard",
            title="JARVIS revenue engine completed a safe run",
            body=body,
            level="success" if result.drafts_created else "warning",
            category="outreach",
            reference=f"approval:{approval_id}",
            delivered=True,
            metadata_=result.as_dict(),
        )
    )


def _merge_tags(existing: list | None, new_tags: list[str]) -> list[str]:
    merged = list(existing or [])
    for tag in new_tags:
        if tag not in merged:
            merged.append(tag)
    return merged


def _estimate_value(contact: Contact, score: int) -> float:
    company = contact.company
    size = ((company.size if company else "") or "").lower()
    if "200" in size or "1000" in size:
        return 12000.0
    if score >= 85:
        return 8000.0
    if score >= 75:
        return 5000.0
    return 2500.0


def _pricing_for(contact: Contact, score: int) -> dict:
    value = _estimate_value(contact, score)
    return {
        "setup_fee": int(value),
        "monthly_retainer": int(max(750, value * 0.2)),
        "currency": "USD",
        "notes": "Draft pricing generated by JARVIS. Captain must approve final quote before sending.",
    }
