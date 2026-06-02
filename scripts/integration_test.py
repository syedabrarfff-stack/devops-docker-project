#!/usr/bin/env python
"""End-to-end JARVIS vNEXT integration test.

This script exercises the first-client revenue path against the real backend
services. It is strict by default: discovery must return at least one lead.
For isolated CI environments only, set JARVIS_INTEGRATION_ALLOW_SEEDED_LEAD=1
to seed one deterministic test lead after proving discovery returned zero.
"""
from __future__ import annotations

import asyncio
import os
import secrets
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("JARVIS_PROPOSAL_DIR", str(ROOT / "data" / "integration_proposals"))

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, init_db, set_tenant_context
from app.models import register_models
from app.models.approval import ApprovalStatus
from app.models.governance import Proposal
from app.models.lead import Lead, LeadStatus
from app.models.outreach import FollowUpQueue
from app.services.governance.captain_queue import captain_queue
from app.services.governance.proposal_generator import proposal_generator
from app.services.intelligence.morning_briefing import MorningBriefingEngine
from app.services.leads.discovery import lead_discovery_engine
from app.services.leads.scoring import lead_scoring_engine
from app.services.outreach.engine import outreach_engine
from app.services.outreach.reply_handler import reply_handler
from app.services.tenancy.tenant_manager import TenantManager


@dataclass
class IntegrationState:
    tenant_id: uuid.UUID | None = None
    lead: Lead | None = None
    leads: list[Lead] = field(default_factory=list)
    score: float = 0.0
    pdf_path: str | None = None
    proposal_id: int | None = None
    approval_id: uuid.UUID | None = None
    briefing: str | None = None


class IntegrationFailure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise IntegrationFailure(message)


def status_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


async def apply_tenant_context(session, tenant_id: uuid.UUID | str) -> None:
    if settings.DATABASE_URL.startswith("sqlite"):
        return
    await set_tenant_context(session, str(tenant_id))


async def step(name: str, fn: Callable[[], Awaitable[str]]) -> None:
    try:
        detail = await fn()
        print(f"PASS {name}: {detail}")
    except Exception as exc:
        print(f"FAIL {name}: {exc}")
        raise


async def create_test_tenant(state: IntegrationState) -> str:
    suffix = secrets.token_hex(4)
    tenant, user = await TenantManager().create_tenant(
        name=f"Test Agency {suffix}",
        plan_tier="GROWTH",
        admin_email=f"integration-{suffix}@example.com",
        admin_password=f"JarvisTest-{suffix}-2026!",
    )
    state.tenant_id = tenant.id
    require(user.tenant_id == tenant.id, "created admin user is not attached to the test tenant")
    return f"tenant_id={state.tenant_id}"


async def run_lead_discovery(state: IntegrationState) -> str:
    require(state.tenant_id is not None, "tenant_id missing")
    inserted = await lead_discovery_engine.run_daily_discovery(
        state.tenant_id,
        [
            {
                "query": "SaaS operations automation",
                "industry": "SaaS",
                "country": "UK",
                "location": "London, UK",
                "limit": 5,
            }
        ],
    )

    leads = await load_leads(state.tenant_id)
    if not leads and os.getenv("JARVIS_INTEGRATION_ALLOW_SEEDED_LEAD") == "1":
        await seed_test_lead(state.tenant_id)
        leads = await load_leads(state.tenant_id)

    require(inserted > 0 or leads, "lead discovery returned zero leads; configure Apollo or Google Maps before launch")
    require(all((lead.score or 0) > 0 for lead in leads), "one or more discovered leads has score <= 0")
    state.leads = leads
    state.lead = leads[0]
    return f"inserted={inserted}, loaded={len(leads)}, top_score={state.lead.score:.1f}"


async def score_top_lead(state: IntegrationState) -> str:
    require(state.lead is not None, "lead missing")
    score, reasoning = await lead_scoring_engine.score_against_icp(lead_to_dict(state.lead))
    require(score > 0, "scored lead returned score <= 0")
    state.score = score
    return f"lead_id={state.lead.id}, score={score:.1f}, decision={reasoning.get('decision')}"


async def queue_outreach_sequence(state: IntegrationState) -> str:
    require(state.tenant_id is not None and state.lead is not None, "tenant or lead missing")
    await outreach_engine.queue_sequence(state.lead.id, state.tenant_id)
    count = await count_followups(state.tenant_id, state.lead.id)
    require(count == 3, f"expected 3 follow-up records, found {count}")
    return f"follow_up_queue={count}"


async def execute_outreach_dry_run(state: IntegrationState) -> str:
    require(state.tenant_id is not None, "tenant_id missing")

    from app.services.notifications.gmail_sender import gmail_sender

    original_send_email = gmail_sender.send_email

    async def fake_send_email(*args, **kwargs) -> bool:
        return True

    gmail_sender.send_email = fake_send_email
    try:
        sent = await outreach_engine.execute_due_outreach(state.tenant_id, limit=3)
    finally:
        gmail_sender.send_email = original_send_email

    require(sent >= 1, "dry-run outreach did not execute any due email")
    return f"dry_run_sent={sent}, real_email_sent=false"


async def simulate_interested_reply(state: IntegrationState) -> str:
    require(state.tenant_id is not None and state.lead is not None, "tenant or lead missing")
    result = await reply_handler.process_reply(
        state.lead.id,
        "Yes, this sounds interesting. Can we schedule a demo this week?",
        state.tenant_id,
    )
    live_lead = await load_lead(state.tenant_id, state.lead.id)
    require(live_lead is not None, "lead disappeared after reply processing")
    require(status_value(live_lead.status) == LeadStatus.DEMO.value, f"expected DEMO status, found {live_lead.status}")
    state.lead = live_lead
    return f"classification={result.get('classification')}, action={result.get('action_taken')}, status={status_value(live_lead.status)}"


async def generate_proposal_pdf(state: IntegrationState) -> str:
    require(state.tenant_id is not None and state.lead is not None, "tenant or lead missing")
    state.pdf_path = await proposal_generator.generate(state.lead, "GROWTH", state.tenant_id)
    proposal = await latest_proposal(state.tenant_id, state.lead.id)
    require(proposal is not None, "proposal record was not created")
    require(proposal.pdf_path and Path(proposal.pdf_path).exists(), f"proposal PDF missing: {proposal.pdf_path}")
    state.proposal_id = int(proposal.id)
    return f"proposal_id={state.proposal_id}, pdf={proposal.pdf_path}"


async def submit_to_captain_queue(state: IntegrationState) -> str:
    require(state.tenant_id is not None and state.proposal_id is not None, "tenant or proposal missing")
    approval = await captain_queue.add_item(
        action_type="proposal_send",
        title=f"Approve integration test proposal #{state.proposal_id}",
        summary="End-to-end integration test proposal is ready for Captain review.",
        payload={
            "proposal_id": state.proposal_id,
            "raised_by": "integration_test",
            "tenant_id": str(state.tenant_id),
        },
        risk_level="MEDIUM",
        tenant_id=state.tenant_id,
    )
    require(status_value(approval.status) == ApprovalStatus.PENDING.value, f"expected PENDING approval, found {approval.status}")
    state.approval_id = approval.id
    return f"approval_id={state.approval_id}, status={status_value(approval.status)}"


async def run_morning_briefing(state: IntegrationState) -> str:
    require(state.tenant_id is not None, "tenant_id missing")
    state.briefing = await MorningBriefingEngine().generate_and_send(state.tenant_id)
    lowered = state.briefing.lower()
    require("leads" in lowered, "briefing does not contain lead context")
    require("revenue" in lowered, "briefing does not contain revenue context")
    return f"briefing_chars={len(state.briefing)}"


async def load_leads(tenant_id: uuid.UUID | str) -> list[Lead]:
    async with AsyncSessionLocal() as session:
        await apply_tenant_context(session, tenant_id)
        rows = await session.execute(
            select(Lead)
            .where(Lead.tenant_id == tenant_id)
            .order_by(Lead.score.desc(), Lead.created_at.desc())
            .limit(10)
        )
        return list(rows.scalars().all())


async def load_lead(tenant_id: uuid.UUID | str, lead_id) -> Lead | None:
    async with AsyncSessionLocal() as session:
        await apply_tenant_context(session, tenant_id)
        return await session.scalar(select(Lead).where(Lead.tenant_id == tenant_id, Lead.id == lead_id))


async def count_followups(tenant_id: uuid.UUID | str, lead_id) -> int:
    async with AsyncSessionLocal() as session:
        await apply_tenant_context(session, tenant_id)
        count = await session.scalar(
            select(func.count()).select_from(FollowUpQueue).where(
                FollowUpQueue.tenant_id == tenant_id,
                FollowUpQueue.lead_id == lead_id,
            )
        )
        return int(count or 0)


async def latest_proposal(tenant_id: uuid.UUID | str, lead_id) -> Proposal | None:
    async with AsyncSessionLocal() as session:
        await apply_tenant_context(session, tenant_id)
        return await session.scalar(
            select(Proposal)
            .where(Proposal.tenant_id == tenant_id, Proposal.lead_id == lead_id)
            .order_by(Proposal.created_at.desc())
            .limit(1)
        )


async def seed_test_lead(tenant_id: uuid.UUID | str) -> None:
    lead_data = {
        "company_name": "Integration SaaS Ltd",
        "contact_name": "Avery Morgan",
        "email": "avery.integration@example.com",
        "country": "UK",
        "industry": "SaaS",
        "employee_count": 42,
        "estimated_revenue": "$2M",
        "pain_points": ["manual processes", "poor lead generation", "no automation"],
        "website": "https://example.com",
        "opportunity_type": "sales operations and customer workflow automation",
        "source": "integration_seed",
    }
    score, reasoning = await lead_scoring_engine.score_against_icp(lead_data)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await apply_tenant_context(session, tenant_id)
            session.add(
                Lead(
                    tenant_id=tenant_id,
                    company_name=lead_data["company_name"],
                    company=lead_data["company_name"],
                    contact_name=lead_data["contact_name"],
                    email=lead_data["email"],
                    contact_email=lead_data["email"],
                    country=lead_data["country"],
                    industry=lead_data["industry"],
                    score=score,
                    status=LeadStatus.NEW,
                    source=lead_data["source"],
                    pain_points=lead_data["pain_points"],
                    enrichment_data={**lead_data, "icp_scoring": reasoning},
                    website=lead_data["website"],
                    company_website=lead_data["website"],
                    opportunity_type=lead_data["opportunity_type"],
                )
            )


def lead_to_dict(lead: Lead) -> dict:
    return {
        "company_name": lead.company_name or lead.company,
        "contact_name": lead.contact_name,
        "email": lead.email or lead.contact_email,
        "country": lead.country,
        "industry": lead.industry,
        "employee_count": (lead.enrichment_data or {}).get("employee_count"),
        "estimated_revenue": (lead.enrichment_data or {}).get("estimated_revenue"),
        "pain_points": lead.pain_points or [],
        "website": lead.website or lead.company_website,
        "opportunity_type": lead.opportunity_type,
        "notes": lead.notes,
    }


async def main() -> int:
    register_models()
    await init_db()

    state = IntegrationState()
    tests: list[tuple[str, Callable[[], Awaitable[str]]]] = [
        ("1 create test tenant", lambda: create_test_tenant(state)),
        ("2 run lead discovery", lambda: run_lead_discovery(state)),
        ("3 assert discovered lead scores", lambda: assert_discovered_scores(state)),
        ("4 score top lead", lambda: score_top_lead(state)),
        ("5 queue outreach sequence", lambda: queue_outreach_sequence(state)),
        ("6 assert follow-up records", lambda: assert_followup_records(state)),
        ("7 execute outreach dry run", lambda: execute_outreach_dry_run(state)),
        ("8 simulate interested reply", lambda: simulate_interested_reply(state)),
        ("9 assert lead demo status", lambda: assert_lead_demo_status(state)),
        ("10 generate proposal PDF", lambda: generate_proposal_pdf(state)),
        ("11 assert PDF exists", lambda: assert_pdf_exists(state)),
        ("12 submit to Captain queue", lambda: submit_to_captain_queue(state)),
        ("13 assert approval pending", lambda: assert_approval_pending(state)),
        ("14 run morning briefing", lambda: run_morning_briefing(state)),
        ("15 assert briefing contains leads and revenue", lambda: assert_briefing_content(state)),
    ]

    try:
        for name, fn in tests:
            await step(name, fn)
    except Exception:
        print("\nJARVIS vNEXT INTEGRATION: FAILED")
        return 1

    print("\nJARVIS vNEXT INTEGRATION: ALL SYSTEMS GO")
    return 0


async def assert_discovered_scores(state: IntegrationState) -> str:
    require(state.leads, "no discovered leads loaded")
    require(all((lead.score or 0) > 0 for lead in state.leads), "not all leads have score > 0")
    return f"checked={len(state.leads)}"


async def assert_followup_records(state: IntegrationState) -> str:
    require(state.tenant_id is not None and state.lead is not None, "tenant or lead missing")
    count = await count_followups(state.tenant_id, state.lead.id)
    require(count == 3, f"expected 3 follow-up records, found {count}")
    return f"followups={count}"


async def assert_lead_demo_status(state: IntegrationState) -> str:
    require(state.tenant_id is not None and state.lead is not None, "tenant or lead missing")
    lead = await load_lead(state.tenant_id, state.lead.id)
    require(lead is not None, "lead not found")
    require(status_value(lead.status) == LeadStatus.DEMO.value, f"expected DEMO, found {lead.status}")
    return f"status={status_value(lead.status)}"


async def assert_pdf_exists(state: IntegrationState) -> str:
    require(state.tenant_id is not None and state.lead is not None, "tenant or lead missing")
    proposal = await latest_proposal(state.tenant_id, state.lead.id)
    require(proposal is not None, "proposal record missing")
    require(proposal.pdf_path and Path(proposal.pdf_path).exists(), f"PDF missing: {proposal.pdf_path}")
    return str(proposal.pdf_path)


async def assert_approval_pending(state: IntegrationState) -> str:
    require(state.tenant_id is not None and state.approval_id is not None, "tenant or approval missing")
    async with AsyncSessionLocal() as session:
        await apply_tenant_context(session, state.tenant_id)
        from app.models.approval import ApprovalRequest

        row = await session.scalar(
            select(ApprovalRequest).where(
                ApprovalRequest.tenant_id == state.tenant_id,
                ApprovalRequest.id == state.approval_id,
            )
        )
    require(row is not None, "approval request missing")
    require(status_value(row.status) == ApprovalStatus.PENDING.value, f"expected PENDING, found {row.status}")
    return f"approval_id={state.approval_id}"


async def assert_briefing_content(state: IntegrationState) -> str:
    require(state.briefing, "briefing was not generated")
    lowered = state.briefing.lower()
    require("leads" in lowered, "briefing missing leads")
    require("revenue" in lowered, "briefing missing revenue")
    return "contains leads and revenue"


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
