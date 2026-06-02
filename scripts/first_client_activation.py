#!/usr/bin/env python3
"""JARVIS vNEXT first-client activation protocol.

This is the honest activation path for the current vNEXT branch. It uses the
real backend services already present in the repo instead of calling placeholder
endpoints. It does not send anything to a client automatically; the send package
is queued for Captain approval.

Usage:
    python scripts/first_client_activation.py
    python scripts/first_client_activation.py --skip-preflight
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import secrets
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Awaitable, Callable


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("JARVIS_PROPOSAL_DIR", str(ROOT / "data" / "first_client_proposals"))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, init_db, set_tenant_context
from app.models import register_models
from app.models.approval import AuditLog
from app.models.crm import Company, Contact
from app.models.lead import Lead, LeadStatus
from app.models.memory import CivilizationMemory
from app.models.revenue import Client, ClientStatus
from app.models.tasks import AgentTask
from app.services.crm import service as crm_service
from app.services.governance.captain_queue import captain_queue
from app.services.governance.invoice_engine import invoice_engine
from app.services.governance.proposal_generator import proposal_generator
from app.services.notifications.slack import notify_slack
from app.services.notifications.telegram import notify_telegram
from app.services.tenancy.tenant_manager import TenantManager


TIERS: dict[str, dict[str, Any]] = {
    "1": {"name": "STARTER", "proposal_tier": "STARTER", "monthly_value": 2500.0},
    "2": {"name": "GROWTH", "proposal_tier": "GROWTH", "monthly_value": 5500.0},
    "3": {"name": "ENTERPRISE", "proposal_tier": "ENTERPRISE", "monthly_value": 12000.0},
    "4": {"name": "INDUSTRY_OS", "proposal_tier": "ENTERPRISE", "monthly_value": 8000.0},
}


@dataclass
class ActivationState:
    company_name: str = ""
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    domain: str = ""
    country: str = ""
    industry: str = ""
    primary_service: str = ""
    pain_points: list[str] = field(default_factory=list)
    tier: str = "STARTER"
    proposal_tier: str = "STARTER"
    monthly_value: float = 2500.0
    contract_months: int = 3
    signed_or_paid: bool = False
    tenant_id: str = ""
    lead_id: str = ""
    proposal_id: int | None = None
    proposal_pdf: str = ""
    approval_id: str = ""
    client_id: str = ""
    invoice_id: str = ""
    invoice_number: str = ""
    company_id: int | None = None
    contact_id: int | None = None
    deal_id: int | None = None
    onboarding_task_ids: list[int] = field(default_factory=list)
    civilization_memory_id: str = ""
    report_path: str = ""


StepFn = Callable[[], Awaitable[None]]


async def step(n: int, name: str, fn: StepFn) -> None:
    while True:
        try:
            print(f"\n[Step {n}] {name}")
            await fn()
            return
        except Exception as exc:
            print(f"Step {n} failed: {exc}")
            answer = input("Press ENTER to retry, type SKIP to continue, or type STOP: ").strip().upper()
            if answer == "STOP":
                raise
            if answer == "SKIP":
                return


async def main() -> int:
    parser = argparse.ArgumentParser(description="Activate the first JARVIS client workspace.")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip the 17-system pre-launch check.")
    args = parser.parse_args()

    print("=" * 72)
    print("  JARVIS vNEXT - Captain's First Client Activation Protocol")
    print("=" * 72)

    register_models()
    await init_db()
    state = ActivationState()

    if not args.skip_preflight:
        await step(1, "Pre-flight checks", lambda: run_preflight())
    else:
        print("\n[Step 1] Pre-flight checks")
        print("  Skipped by --skip-preflight.")

    await step(2, "Client identity", lambda: collect_client_identity(state))
    await step(3, "Tenant workspace provision", lambda: provision_tenant(state))
    await step(4, "Lead and opportunity record", lambda: create_lead_record(state))
    await step(5, "Proposal PDF and Captain approval", lambda: generate_proposal_package(state))
    await step(6, "Client record and invoice", lambda: create_client_and_invoice(state))
    await step(7, "CRM company, contact, and deal", lambda: create_crm_records(state))
    await step(8, "Onboarding task plan", lambda: create_onboarding_tasks(state))
    await step(9, "Send package approval hold", lambda: queue_send_package_approval(state))
    await step(10, "Civilization memory", lambda: preserve_memory(state))
    await step(11, "Captain notification", lambda: notify_captain(state))
    await step(12, "Activation report", lambda: write_activation_report(state))

    print_summary(state)
    return 0


async def run_preflight() -> None:
    import importlib.util

    path = ROOT / "scripts" / "pre_launch_check.py"
    spec = importlib.util.spec_from_file_location("pre_launch_check", path)
    if not spec or not spec.loader:
        raise RuntimeError("Could not load scripts/pre_launch_check.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    results = await module.run_all_checks()
    failed = [detail for passed, detail in results if not passed]
    if failed:
        print(f"  {len(failed)} of {len(results)} checks failed.")
        for detail in failed:
            print(f"    FAIL {detail}")
        answer = input("Continue anyway? Type CONTINUE to proceed, anything else to retry: ").strip().upper()
        if answer != "CONTINUE":
            raise RuntimeError("Pre-flight checks did not pass")
        print("  Continuing with Captain override.")
    else:
        print("  All 17 pre-launch checks passed.")


async def collect_client_identity(state: ActivationState) -> None:
    state.company_name = _required_input("  Company name: ")
    state.contact_name = _required_input("  Contact name: ")
    state.contact_email = _email_input("  Contact email: ")
    state.contact_phone = input("  Contact phone (optional): ").strip()
    state.domain = _normalize_domain(input("  Website/domain (optional): ").strip())
    state.country = input("  Country/region: ").strip() or "Unknown"
    state.industry = input("  Industry: ").strip() or "Business operations"
    state.primary_service = _required_input("  Primary service Aliyar Solutions will deliver: ")
    pain_text = input("  Visible pain points, comma separated: ").strip()
    state.pain_points = [item.strip() for item in pain_text.split(",") if item.strip()]
    if not state.pain_points:
        state.pain_points = ["manual follow-up", "limited operational visibility", "slow customer response"]

    print("  Tiers: [1] STARTER $2,500/mo  [2] GROWTH $5,500/mo  [3] ENTERPRISE $12,000/mo  [4] INDUSTRY OS $8,000/mo")
    tier_key = input("  Select tier [1-4]: ").strip() or "1"
    tier = TIERS.get(tier_key, TIERS["1"])
    state.tier = tier["name"]
    state.proposal_tier = tier["proposal_tier"]
    state.monthly_value = float(tier["monthly_value"])

    months = input("  Contract months [3]: ").strip()
    state.contract_months = int(months) if months else 3
    signed = input("  Has the client already signed or paid? [y/N]: ").strip().lower()
    state.signed_or_paid = signed == "y"
    print(f"  Client captured: {state.company_name} | {state.tier} | ${state.monthly_value:,.0f}/mo")


async def provision_tenant(state: ActivationState) -> None:
    suffix = secrets.token_hex(4)
    tenant, _ = await TenantManager().create_tenant(
        name=f"{state.company_name} Workspace",
        plan_tier="GROWTH" if state.tier in {"GROWTH", "STARTER"} else "ENTERPRISE",
        admin_email=state.contact_email,
        admin_password=f"JarvisClient-{suffix}-{secrets.token_hex(6)}!",
    )
    state.tenant_id = str(tenant.id)
    print(f"  Tenant provisioned: {state.tenant_id}")
    print("  Client admin password and API key were generated internally and not printed.")


async def create_lead_record(state: ActivationState) -> None:
    tenant_id = uuid.UUID(state.tenant_id)
    async with AsyncSessionLocal() as db:
        async with db.begin():
            await _tenant_context(db, tenant_id)
            lead = Lead(
                tenant_id=tenant_id,
                company_name=state.company_name,
                company=state.company_name,
                contact_name=state.contact_name,
                email=state.contact_email,
                contact_email=state.contact_email,
                phone=state.contact_phone or None,
                country=state.country,
                industry=state.industry,
                website=state.domain or None,
                company_website=state.domain or None,
                score=80 if state.signed_or_paid else 70,
                status=LeadStatus.WON if state.signed_or_paid else LeadStatus.PROPOSAL,
                source="first_client_activation",
                pain_points=state.pain_points,
                opportunity_type=state.primary_service,
                notes="Created by first client activation protocol.",
                enrichment_data={
                    "activation_protocol": True,
                    "tier": state.tier,
                    "monthly_value": state.monthly_value,
                    "contract_months": state.contract_months,
                },
            )
            db.add(lead)
            await db.flush()
            await _audit(
                db,
                tenant_id,
                "first_client_lead_created",
                "lead",
                lead.id,
                {"company_name": state.company_name, "source": lead.source, "score": lead.score},
            )
            state.lead_id = str(lead.id)
    print(f"  Lead/opportunity created: {state.lead_id}")


async def generate_proposal_package(state: ActivationState) -> None:
    tenant_id = uuid.UUID(state.tenant_id)
    lead_id = uuid.UUID(state.lead_id)
    async with AsyncSessionLocal() as db:
        async with db.begin():
            await _tenant_context(db, tenant_id)
            lead = await db.scalar(select(Lead).where(Lead.tenant_id == tenant_id, Lead.id == lead_id))
            if not lead:
                raise RuntimeError("Lead was not found for proposal generation")

    state.proposal_pdf = await proposal_generator.generate(lead, state.proposal_tier, tenant_id)

    async with AsyncSessionLocal() as db:
        async with db.begin():
            await _tenant_context(db, tenant_id)
            from app.models.governance import Proposal

            proposal = await db.scalar(
                select(Proposal)
                .where(Proposal.tenant_id == tenant_id, Proposal.lead_id == lead_id)
                .order_by(Proposal.created_at.desc())
                .limit(1)
            )
            if not proposal:
                raise RuntimeError("Proposal record was not created")
            state.proposal_id = int(proposal.id)

    approval = await proposal_generator.submit_for_approval(state.proposal_id, tenant_id)
    state.approval_id = str(approval.get("id") or approval.get("approval_id") or "")
    print(f"  Proposal PDF: {state.proposal_pdf}")
    print(f"  Proposal queued for Captain approval: {state.approval_id or 'created'}")


async def create_client_and_invoice(state: ActivationState) -> None:
    tenant_id = uuid.UUID(state.tenant_id)
    async with AsyncSessionLocal() as db:
        async with db.begin():
            await _tenant_context(db, tenant_id)
            client = Client(
                tenant_id=tenant_id,
                company_name=state.company_name,
                contact_name=state.contact_name,
                email=state.contact_email,
                package_tier=state.tier,
                mrr_usd=state.monthly_value if state.signed_or_paid else 0.0,
                status=ClientStatus.ACTIVE if state.signed_or_paid else ClientStatus.PAUSED,
                started_at=datetime.now(UTC) if state.signed_or_paid else None,
            )
            db.add(client)
            await db.flush()
            await _audit(
                db,
                tenant_id,
                "first_client_record_created",
                "client",
                client.id,
                {
                    "company_name": state.company_name,
                    "package_tier": state.tier,
                    "mrr_usd": client.mrr_usd,
                    "status": client.status.value,
                },
            )
            state.client_id = str(client.id)

    invoice = await invoice_engine.generate(
        client_id=uuid.UUID(state.client_id),
        amount_usd=state.monthly_value,
        description=f"{state.primary_service} - {state.tier} monthly activation",
        due_days=7,
        tenant_id=tenant_id,
    )
    state.invoice_id = str(invoice.id)
    state.invoice_number = invoice.invoice_number
    print(f"  Client record: {state.client_id}")
    print(f"  Invoice generated: {state.invoice_number} (${state.monthly_value:,.0f})")


async def create_crm_records(state: ActivationState) -> None:
    tenant_id = uuid.UUID(state.tenant_id)
    async with AsyncSessionLocal() as db:
        async with db.begin():
            company = await _get_or_create_company(db, state, tenant_id)
            contact = await _get_or_create_contact(db, state, tenant_id, company.id)
            deal = await crm_service.create_deal(
                db,
                {
                    "tenant_id": tenant_id,
                    "title": f"{state.company_name} - {state.primary_service}",
                    "contact_id": contact.id,
                    "company_id": company.id,
                    "value": state.monthly_value * state.contract_months,
                    "currency": "USD",
                    "stage": "closed_won" if state.signed_or_paid else "proposal",
                    "probability": 100 if state.signed_or_paid else 70,
                    "service_type": state.primary_service,
                    "notes": f"Created by first client activation protocol. Tenant: {state.tenant_id}",
                },
            )
            await _audit(
                db,
                tenant_id,
                "first_client_crm_records_created",
                "crm",
                None,
                {"company_id": company.id, "contact_id": contact.id, "deal_id": deal.id},
            )
            state.company_id = int(company.id)
            state.contact_id = int(contact.id)
            state.deal_id = int(deal.id)
    print(f"  CRM company/contact/deal: {state.company_id}/{state.contact_id}/{state.deal_id}")


async def create_onboarding_tasks(state: ActivationState) -> None:
    tenant_id = uuid.UUID(state.tenant_id)
    today = datetime.now(UTC).date()
    tasks = [
        ("Schedule kickoff call", today + timedelta(days=2), "client_success_manager"),
        ("Send requirements questionnaire", today + timedelta(days=3), "delivery_operator"),
        ("Collect technical access", today + timedelta(days=5), "devops_manager"),
        ("Draft service agreement or contract", today + timedelta(days=5), "governance_operator"),
        ("Prepare first deliverable milestone", today + timedelta(days=14), "delivery_operator"),
        ("Schedule 30-day check-in", today + timedelta(days=30), "client_success_manager"),
    ]
    async with AsyncSessionLocal() as db:
        async with db.begin():
            for title, due_date, assignee in tasks:
                task = AgentTask(
                    tenant_id=tenant_id,
                    title=f"{state.company_name}: {title}",
                    description=f"First-client onboarding task for {state.company_name}. Due {due_date}.",
                    task_type="onboarding",
                    assigned_to=assignee,
                    created_by="first_client_activation",
                    priority=2,
                    status="queued",
                    payload={
                        "tenant_id": state.tenant_id,
                        "client_id": state.client_id,
                        "company_name": state.company_name,
                        "due_date": str(due_date),
                        "service": state.primary_service,
                    },
                )
                db.add(task)
                await db.flush()
                state.onboarding_task_ids.append(int(task.id))
            await _audit(
                db,
                tenant_id,
                "first_client_onboarding_tasks_created",
                "task_plan",
                None,
                {"task_ids": state.onboarding_task_ids},
            )
    print(f"  Onboarding tasks created: {len(state.onboarding_task_ids)}")


async def queue_send_package_approval(state: ActivationState) -> None:
    tenant_id = uuid.UUID(state.tenant_id)
    approval = await captain_queue.add_item(
        action_type="first_client_package_send",
        title=f"Approve first-client package: {state.company_name}",
        summary=(
            "Proposal PDF and invoice are prepared. Contract/service agreement drafting is queued as an onboarding task. "
            "Approve only after Captain confirms scope, pricing, and client readiness."
        ),
        payload={
            "tenant_id": state.tenant_id,
            "lead_id": state.lead_id,
            "client_id": state.client_id,
            "proposal_id": state.proposal_id,
            "proposal_pdf": state.proposal_pdf,
            "invoice_id": state.invoice_id,
            "invoice_number": state.invoice_number,
            "contact_email": state.contact_email,
            "send_allowed": False,
            "reason": "Package send requires Captain review and approval.",
        },
        risk_level="HIGH",
        tenant_id=tenant_id,
    )
    print(f"  Send package held for Captain approval: {approval.id}")


async def preserve_memory(state: ActivationState) -> None:
    tenant_id = uuid.UUID(state.tenant_id)
    content = (
        f"First-client activation prepared for {state.company_name}. "
        f"Tier: {state.tier}. Service: {state.primary_service}. "
        f"Monthly value: ${state.monthly_value:,.0f}. "
        f"Status: {'signed_or_paid' if state.signed_or_paid else 'package_prepared_not_yet_paid'}."
    )
    async with AsyncSessionLocal() as db:
        async with db.begin():
            await _tenant_context(db, tenant_id)
            previous_hash = await db.scalar(
                select(CivilizationMemory.record_hash)
                .where(CivilizationMemory.tenant_id == tenant_id)
                .order_by(CivilizationMemory.created_at.desc())
                .limit(1)
            )
            record_hash = hashlib.sha256(f"{previous_hash or ''}|{tenant_id}|{content}".encode("utf-8")).hexdigest()
            memory = CivilizationMemory(
                tenant_id=tenant_id,
                event_type="first_client_activation",
                content=content,
                record_hash=record_hash,
                previous_hash=previous_hash,
                metadata_json={
                    "company_name": state.company_name,
                    "client_id": state.client_id,
                    "proposal_id": state.proposal_id,
                    "invoice_number": state.invoice_number,
                    "monthly_value": state.monthly_value,
                },
            )
            db.add(memory)
            await db.flush()
            await _audit(
                db,
                tenant_id,
                "first_client_civilization_memory_created",
                "civilization_memory",
                memory.id,
                {"record_hash": record_hash, "event_type": memory.event_type},
            )
            state.civilization_memory_id = str(memory.id)
    print(f"  Civilization memory preserved: {state.civilization_memory_id}")


async def notify_captain(state: ActivationState) -> None:
    status = "SIGNED/PAID" if state.signed_or_paid else "PACKAGE READY"
    message = (
        f"JARVIS first-client activation {status}: {state.company_name} | "
        f"{state.tier} | ${state.monthly_value:,.0f}/mo | "
        f"Proposal: {state.proposal_id} | Invoice: {state.invoice_number}"
    )
    slack_ok = await notify_slack(message)
    telegram_ok = await notify_telegram(message)
    print(f"  Slack notification: {'sent' if slack_ok else 'not configured or failed'}")
    print(f"  Telegram notification: {'sent' if telegram_ok else 'not configured or failed'}")


async def write_activation_report(state: ActivationState) -> None:
    report_dir = Path.home() / "Desktop"
    if not report_dir.exists():
        report_dir = ROOT / "data" / "activation_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"jarvis_first_client_activation_{_slug(state.company_name)}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
    payload = asdict(state)
    payload["generated_at"] = datetime.now(UTC).isoformat()
    payload["secrets_included"] = False
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    state.report_path = str(report_path)
    print(f"  Activation report written: {state.report_path}")


async def _get_or_create_company(db, state: ActivationState, tenant_id: uuid.UUID) -> Company:
    if state.domain:
        existing = await db.scalar(select(Company).where(Company.tenant_id == tenant_id, Company.domain == state.domain))
        if existing:
            return existing
    existing = await db.scalar(select(Company).where(Company.tenant_id == tenant_id, Company.name == state.company_name))
    if existing:
        return existing
    return await crm_service.create_company(
        db,
        {
            "tenant_id": tenant_id,
            "name": state.company_name,
            "domain": state.domain or None,
            "industry": state.industry,
            "country": state.country,
            "pain_points": state.pain_points,
            "status": "client" if state.signed_or_paid else "prospect",
            "score": 90 if state.signed_or_paid else 75,
            "notes": "Created by first client activation protocol.",
        },
    )


async def _get_or_create_contact(db, state: ActivationState, tenant_id: uuid.UUID, company_id: int) -> Contact:
    existing = await db.scalar(select(Contact).where(Contact.tenant_id == tenant_id, Contact.email == state.contact_email))
    if existing:
        return existing
    return await crm_service.create_contact(
        db,
        {
            "tenant_id": tenant_id,
            "name": state.contact_name,
            "email": state.contact_email,
            "phone": state.contact_phone or None,
            "company_id": company_id,
            "country": state.country,
            "source": "first_client_activation",
            "status": "client" if state.signed_or_paid else "qualified",
            "score": 90 if state.signed_or_paid else 75,
            "tags": ["first-client", state.tier.lower()],
            "notes": f"Service interest: {state.primary_service}",
        },
    )


async def _tenant_context(db, tenant_id: uuid.UUID) -> None:
    from app.core.config import settings

    if settings.DATABASE_URL.startswith("sqlite"):
        return
    await set_tenant_context(db, str(tenant_id))


async def _audit(
    db,
    tenant_id: uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    payload: dict[str, Any],
) -> None:
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor="first_client_activation",
            after_json=payload,
            details=payload,
        )
    )


def print_summary(state: ActivationState) -> None:
    ten_client_target = state.monthly_value * 10
    print("\n" + "=" * 72)
    print("  JARVIS FIRST CLIENT ACTIVATION - COMPLETE")
    print("=" * 72)
    print(f"  Client:        {state.company_name}")
    print(f"  Contact:       {state.contact_name} ({state.contact_email})")
    print(f"  Service Tier:  {state.tier}")
    print(f"  Monthly Value: ${state.monthly_value:,.0f}")
    print(f"  Tenant ID:     {state.tenant_id}")
    print(f"  Lead ID:       {state.lead_id}")
    print(f"  Proposal ID:   {state.proposal_id}")
    print(f"  Proposal PDF:  {state.proposal_pdf}")
    print(f"  Invoice:       {state.invoice_number}")
    print(f"  Client Status: {'active revenue' if state.signed_or_paid else 'package ready, not paid yet'}")
    print(f"  Report:        {state.report_path}")
    print("")
    if state.signed_or_paid:
        print("  Aliyar Solutions has recorded the first paying client.")
    else:
        print("  Activation package is prepared. Revenue starts when Captain confirms signature/payment.")
    print(f"  Next milestone: 10 clients = ${ten_client_target:,.0f}/month")
    print("=" * 72)


def _required_input(prompt: str) -> str:
    value = input(prompt).strip()
    if not value:
        raise ValueError("Required value missing")
    return value


def _email_input(prompt: str) -> str:
    value = _required_input(prompt).lower()
    if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
        raise ValueError("Invalid email address")
    return value


def _normalize_domain(value: str) -> str:
    value = value.strip().lower()
    if not value:
        return ""
    value = re.sub(r"^https?://", "", value)
    value = value.split("/", 1)[0]
    return value


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "client"


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
