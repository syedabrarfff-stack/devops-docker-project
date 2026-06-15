"""
Demo data seeder — populates JARVIS with realistic Aliyar Solutions data.
Creates clients, invoices, leads, and revenue snapshots for live dashboards.
Run once per tenant; safe to re-run (upserts by company name / invoice number).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lead import Lead, LeadStatus
from app.models.revenue import Client, ClientStatus, Invoice, InvoiceStatus, RevenueSnapshot

_CLIENTS: list[dict[str, Any]] = [
    {"company_name": "OmniShift Corp",        "contact_name": "Marcus Webb",    "email": "marcus.webb@omnishift.com",      "package_tier": "A", "mrr_usd": 6000.0, "months_ago": 7, "industry": "Logistics"},
    {"company_name": "MediPulse Health",       "contact_name": "Priya Nair",     "email": "priya.nair@medipulse.io",        "package_tier": "A", "mrr_usd": 5000.0, "months_ago": 6, "industry": "Healthcare"},
    {"company_name": "Apex Financial Group",   "contact_name": "Daniel Torres",  "email": "d.torres@apexfg.com",            "package_tier": "A", "mrr_usd": 4500.0, "months_ago": 2, "industry": "Finance"},
    {"company_name": "NovaTech Solutions",     "contact_name": "Sarah Kim",      "email": "sarah.kim@novatech.io",          "package_tier": "B", "mrr_usd": 3500.0, "months_ago": 5, "industry": "Technology"},
    {"company_name": "DataVault Analytics",    "contact_name": "James Okafor",   "email": "j.okafor@datavault.ai",          "package_tier": "B", "mrr_usd": 3000.0, "months_ago": 1, "industry": "Analytics"},
    {"company_name": "BlueCrest Retail",       "contact_name": "Emily Zhao",     "email": "emily.zhao@bluecrest.com",       "package_tier": "B", "mrr_usd": 2500.0, "months_ago": 4, "industry": "E-commerce"},
    {"company_name": "SwiftLogix Ltd",         "contact_name": "Ravi Patel",     "email": "ravi@swiftlogix.com",            "package_tier": "C", "mrr_usd": 2000.0, "months_ago": 3, "industry": "Supply Chain"},
    {"company_name": "GreenPath Consulting",   "contact_name": "Amelia Foster",  "email": "afoster@greenpath.co",           "package_tier": "C", "mrr_usd": 1500.0, "months_ago": 4, "industry": "Consulting", "paused": True},
]

_LEADS: list[dict[str, Any]] = [
    {"company_name": "Horizon Ventures",    "contact_name": "Tyler Grant",    "email": "tyler@horizonvc.com",     "status": LeadStatus.PROPOSAL,  "score": 88, "industry": "Venture Capital",   "country": "USA"},
    {"company_name": "Nexgen Pharma",       "contact_name": "Dr. Lena Müller","email": "l.mueller@nexgenpharma.de","status": LeadStatus.DEMO,      "score": 82, "industry": "Pharma",           "country": "Germany"},
    {"company_name": "TrustBank Digital",   "contact_name": "Omar Hassan",    "email": "o.hassan@trustbank.ae",   "status": LeadStatus.DEMO,      "score": 79, "industry": "Fintech",          "country": "UAE"},
    {"company_name": "SkyBridge Logistics", "contact_name": "Chen Wei",       "email": "chenwei@skybridge.sg",    "status": LeadStatus.REPLIED,   "score": 74, "industry": "Logistics",        "country": "Singapore"},
    {"company_name": "PeakSales Academy",   "contact_name": "Natalie Brooks", "email": "n.brooks@peaksales.com",  "status": LeadStatus.REPLIED,   "score": 71, "industry": "SaaS",             "country": "UK"},
    {"company_name": "UrbanNest PropTech",  "contact_name": "Arjun Reddy",    "email": "arjun@urbannest.in",      "status": LeadStatus.REPLIED,   "score": 68, "industry": "Real Estate",      "country": "India"},
    {"company_name": "ClearView Analytics", "contact_name": "Sofia Martinez", "email": "sofia@clearview.mx",      "status": LeadStatus.CONTACTED, "score": 63, "industry": "Analytics",        "country": "Mexico"},
    {"company_name": "IronPeak Manufacturing","contact_name": "Greg Sullivan", "email": "g.sullivan@ironpeak.ca",  "status": LeadStatus.CONTACTED, "score": 58, "industry": "Manufacturing",    "country": "Canada"},
    {"company_name": "FlowState Media",     "contact_name": "Zoe Park",       "email": "zoe@flowstatemedia.com",  "status": LeadStatus.CONTACTED, "score": 55, "industry": "Media",            "country": "Australia"},
    {"company_name": "Radi Health AI",      "contact_name": "Fatima Al-Sayed","email": "f.alsayed@radihealth.sa", "status": LeadStatus.CONTACTED, "score": 52, "industry": "HealthTech",       "country": "Saudi Arabia"},
    {"company_name": "QuadCore Systems",    "contact_name": "Ivan Petrov",    "email": "i.petrov@quadcore.ru",    "status": LeadStatus.NEW,       "score": 47, "industry": "Technology",       "country": "Russia"},
    {"company_name": "GlobaTrade Ltd",      "contact_name": "Yuki Tanaka",    "email": "y.tanaka@globatrade.jp",  "status": LeadStatus.NEW,       "score": 44, "industry": "Import/Export",    "country": "Japan"},
    {"company_name": "BrightMind EdTech",   "contact_name": "Amara Diallo",   "email": "amara@brightmind.ng",     "status": LeadStatus.NEW,       "score": 41, "industry": "Education",        "country": "Nigeria"},
    {"company_name": "CypherNet Security",  "contact_name": "Lars Hansen",    "email": "l.hansen@cyphernet.dk",   "status": LeadStatus.NEW,       "score": 38, "industry": "Cybersecurity",    "country": "Denmark"},
    {"company_name": "VerdantFarm AgriTech","contact_name": "Carlos Nunes",   "email": "c.nunes@verdantfarm.br",  "status": LeadStatus.NEW,       "score": 35, "industry": "AgriTech",         "country": "Brazil"},
    {"company_name": "ArcticPrime Energy",  "contact_name": "Ingrid Larsson", "email": "i.larsson@arcticprime.no","status": LeadStatus.NURTURE,   "score": 60, "industry": "Energy",           "country": "Norway"},
    {"company_name": "Stratos Aviation",    "contact_name": "Ben Adeyemi",    "email": "b.adeyemi@stratos.com",   "status": LeadStatus.NURTURE,   "score": 57, "industry": "Aviation",         "country": "USA"},
    {"company_name": "PulsePay Fintech",    "contact_name": "Mei Lin",        "email": "mei.lin@pulsepay.cn",     "status": LeadStatus.WON,       "score": 92, "industry": "Fintech",          "country": "China"},
    {"company_name": "CoreStack DevOps",    "contact_name": "Raj Mehta",      "email": "raj.mehta@corestack.in",  "status": LeadStatus.WON,       "score": 90, "industry": "DevOps",           "country": "India"},
    {"company_name": "LuxeTravel Group",    "contact_name": "Claire Dubois",  "email": "claire@luxetravel.fr",    "status": LeadStatus.LOST,      "score": 45, "industry": "Travel",           "country": "France"},
    {"company_name": "RoboVision AI",       "contact_name": "Dmitri Volkov",  "email": "d.volkov@robovision.ru",  "status": LeadStatus.LOST,      "score": 39, "industry": "Robotics",         "country": "Russia"},
    {"company_name": "PrimeShelf Retail",   "contact_name": "Hannah Schmidt", "email": "h.schmidt@primeshelf.de", "status": LeadStatus.PROPOSAL,  "score": 85, "industry": "Retail",           "country": "Germany"},
    {"company_name": "Zenith Insurance",    "contact_name": "Frank O'Brien",  "email": "fobrien@zenithins.ie",    "status": LeadStatus.DEMO,      "score": 77, "industry": "Insurance",        "country": "Ireland"},
    {"company_name": "TerraCore Mining",    "contact_name": "Alberto Vega",   "email": "a.vega@terracore.pe",     "status": LeadStatus.NEW,       "score": 30, "industry": "Mining",           "country": "Peru"},
    {"company_name": "Sparkline SaaS",      "contact_name": "Tanya Rivers",   "email": "tanya@sparkline.io",      "status": LeadStatus.REPLIED,   "score": 66, "industry": "SaaS",             "country": "USA"},
]


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _months_back(n: int) -> datetime:
    return _now() - timedelta(days=n * 30)


async def seed_demo_data(tenant_id: uuid.UUID, session: AsyncSession) -> dict:
    """
    Idempotent demo seeder. Skips records that already exist by name/number.
    Returns counts of created records.
    """
    created: dict[str, int] = {"clients": 0, "invoices": 0, "leads": 0, "snapshots": 0}

    # ── 1. Clients ───────────────────────────────────────────────────────────
    client_ids: dict[str, uuid.UUID] = {}
    for c in _CLIENTS:
        existing = (await session.execute(
            select(Client).where(Client.tenant_id == tenant_id, Client.company_name == c["company_name"])
        )).scalar_one_or_none()

        if existing:
            client_ids[c["company_name"]] = existing.id
            continue

        client = Client(
            tenant_id=tenant_id,
            company_name=c["company_name"],
            contact_name=c["contact_name"],
            email=c["email"],
            package_tier=c["package_tier"],
            mrr_usd=c["mrr_usd"],
            status=ClientStatus.PAUSED if c.get("paused") else ClientStatus.ACTIVE,
            started_at=_months_back(c["months_ago"]),
        )
        session.add(client)
        await session.flush()
        client_ids[c["company_name"]] = client.id
        created["clients"] += 1

    # ── 2. Invoices (3 per client — paid, sent, one overdue for select) ──────
    inv_counter = 1
    for c in _CLIENTS:
        cid = client_ids[c["company_name"]]
        months = c["months_ago"]
        mrr = c["mrr_usd"]
        paused = c.get("paused", False)

        invoices_to_create = [
            {
                "invoice_number": f"ALY-{(_now() - timedelta(days=months*30)).strftime('%Y%m')}-{inv_counter:04d}",
                "amount_usd": mrr,
                "status": InvoiceStatus.PAID,
                "due_date": _months_back(months) + timedelta(days=14),
                "paid_at": _months_back(months) + timedelta(days=10),
                "paid_amount_usd": mrr,
                "description": f"Monthly retainer — {c['industry']} AI operations package",
                "items": [{"description": "AI Operations Retainer", "qty": 1, "unit_price": mrr, "total": mrr}],
            },
            {
                "invoice_number": f"ALY-{(_now() - timedelta(days=30)).strftime('%Y%m')}-{inv_counter+1:04d}",
                "amount_usd": mrr,
                "status": InvoiceStatus.PAID if months >= 2 else InvoiceStatus.SENT,
                "due_date": _now() - timedelta(days=16) if months >= 2 else _now() + timedelta(days=14),
                "paid_at": _now() - timedelta(days=20) if months >= 2 else None,
                "paid_amount_usd": mrr if months >= 2 else 0.0,
                "description": f"Monthly retainer — {c['industry']} AI operations package",
                "items": [{"description": "AI Operations Retainer", "qty": 1, "unit_price": mrr, "total": mrr}],
            },
        ]
        if not paused:
            invoices_to_create.append({
                "invoice_number": f"ALY-{_now().strftime('%Y%m')}-{inv_counter+2:04d}",
                "amount_usd": mrr,
                "status": InvoiceStatus.SENT,
                "due_date": _now() + timedelta(days=14),
                "paid_at": None,
                "paid_amount_usd": 0.0,
                "description": f"Monthly retainer — {c['industry']} AI operations package",
                "items": [{"description": "AI Operations Retainer", "qty": 1, "unit_price": mrr, "total": mrr}],
            })

        for inv_data in invoices_to_create:
            inv_counter += 1
            existing_inv = (await session.execute(
                select(Invoice).where(Invoice.tenant_id == tenant_id, Invoice.invoice_number == inv_data["invoice_number"])
            )).scalar_one_or_none()
            if existing_inv:
                continue

            inv = Invoice(
                tenant_id=tenant_id,
                client_id=cid,
                client_name=c["contact_name"],
                client_email=c["email"],
                client_company=c["company_name"],
                invoice_number=inv_data["invoice_number"],
                description=inv_data["description"],
                amount_usd=inv_data["amount_usd"],
                paid_amount_usd=inv_data["paid_amount_usd"],
                status=inv_data["status"],
                due_date=inv_data["due_date"],
                paid_at=inv_data["paid_at"],
                items=inv_data["items"],
                subtotal=inv_data["amount_usd"],
                tax_rate=0.0,
                tax_amount=0.0,
                total=inv_data["amount_usd"],
                currency="USD",
                sent_at=inv_data["due_date"] - timedelta(days=14) if inv_data["status"] != InvoiceStatus.DRAFT else None,
            )
            session.add(inv)
            created["invoices"] += 1

    # ── 3. Revenue snapshots (90 days of MRR history) ────────────────────────
    active_clients = [c for c in _CLIENTS if not c.get("paused")]
    total_mrr = sum(c["mrr_usd"] for c in active_clients)

    for days_back in range(89, -1, -1):
        snap_date = date.today() - timedelta(days=days_back)

        existing_snap = (await session.execute(
            select(RevenueSnapshot).where(
                RevenueSnapshot.tenant_id == tenant_id,
                RevenueSnapshot.snapshot_date == snap_date,
            )
        )).scalar_one_or_none()
        if existing_snap:
            continue

        # Gradually ramp MRR: older dates have proportionally less
        ramp_factor = max(0.45, 1.0 - (days_back / 89) * 0.55)
        day_mrr = round(total_mrr * ramp_factor, 2)
        day_clients = max(2, round(len(active_clients) * ramp_factor))
        day_paid = round(day_mrr * 0.85, 2)
        day_invoiced = round(day_mrr * 1.0, 2)
        day_outstanding = round(day_mrr * 0.15, 2)

        snap = RevenueSnapshot(
            tenant_id=tenant_id,
            snapshot_date=snap_date,
            mrr_usd=day_mrr,
            invoiced_revenue_usd=day_invoiced,
            paid_revenue_usd=day_paid,
            outstanding_revenue_usd=day_outstanding,
            active_clients=day_clients,
            paid_invoices=day_clients * 2,
            overdue_invoices=1 if days_back % 30 < 5 else 0,
        )
        session.add(snap)
        created["snapshots"] += 1

    # ── 4. Leads ─────────────────────────────────────────────────────────────
    for lead_data in _LEADS:
        existing_lead = (await session.execute(
            select(Lead).where(Lead.tenant_id == tenant_id, Lead.email == lead_data["email"])
        )).scalar_one_or_none()
        if existing_lead:
            continue

        days_since_contact = {
            LeadStatus.NEW: None, LeadStatus.CONTACTED: 3, LeadStatus.REPLIED: 6,
            LeadStatus.DEMO: 10, LeadStatus.PROPOSAL: 14, LeadStatus.NURTURE: 20,
            LeadStatus.WON: 30, LeadStatus.LOST: 25,
        }.get(lead_data["status"])

        lead = Lead(
            tenant_id=tenant_id,
            company_name=lead_data["company_name"],
            contact_name=lead_data["contact_name"],
            email=lead_data["email"],
            country=lead_data["country"],
            industry=lead_data["industry"],
            score=lead_data["score"],
            status=lead_data["status"],
            source="multi_path_discovery",
            outreach_eligible=lead_data["status"] not in (LeadStatus.WON, LeadStatus.LOST),
            last_contact=_now() - timedelta(days=days_since_contact) if days_since_contact else None,
            pain_points=["manual processes", "scaling bottlenecks", "AI adoption lag"],
            enrichment_data={"source": "jarvis_seeder", "industry": lead_data["industry"]},
            signal_breakdown={"score": lead_data["score"], "recency": 0.8, "fit": 0.9},
        )
        session.add(lead)
        created["leads"] += 1

    await session.commit()
    return created
