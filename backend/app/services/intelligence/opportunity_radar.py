"""Opportunity Radar — nightly scan for hot leads ready to contact.

Runs at 06:00 UTC daily. Finds leads with score >= 40 that have not been
contacted in 7+ days and are not already in an active outreach sequence.
Generates a structured radar report and delivers via Telegram + WebSocket.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.lead import Lead, LeadStatus
from app.models.outreach import OutreachEmail
from app.services.notifications import notify_telegram

# Leads above this score are flagged as "opportunity"
OPPORTUNITY_SCORE_THRESHOLD = 40
# Leads above this score are flagged as "hot" (ready for proposal)
HOT_SCORE_THRESHOLD = 60
# Days since last contact before a lead is considered "idle"
IDLE_DAYS = 7
# Max leads to surface per radar report
MAX_RADAR_LEADS = 10


async def run_opportunity_radar(tenant_id: uuid.UUID) -> dict[str, Any]:
    """Execute the full opportunity radar for one tenant. Returns the report dict."""
    async with AsyncSessionLocal() as db:
        await set_tenant_context(db, str(tenant_id))
        return await _scan(db, tenant_id)


async def _scan(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    idle_cutoff = now - timedelta(days=IDLE_DAYS)

    # Leads with score >= threshold, not won/lost, idle for IDLE_DAYS+
    opportunity_leads = (
        await db.execute(
            select(Lead)
            .where(
                Lead.tenant_id == tenant_id,
                Lead.score >= OPPORTUNITY_SCORE_THRESHOLD,
                Lead.status.notin_([LeadStatus.WON, LeadStatus.LOST, LeadStatus.PROPOSAL]),
                Lead.outreach_eligible.is_(True),
            )
            .order_by(Lead.score.desc())
            .limit(MAX_RADAR_LEADS * 2)
        )
    ).scalars().all()

    # Filter: last contacted more than IDLE_DAYS ago (or never)
    idle_leads = [
        lead for lead in opportunity_leads
        if _is_idle(lead, idle_cutoff)
    ][:MAX_RADAR_LEADS]

    # Check which of these are currently in active outreach (have a scheduled email)
    if idle_leads:
        lead_ids = [lead.id for lead in idle_leads]
        active_outreach_ids = set(
            (
                await db.execute(
                    select(OutreachEmail.lead_id)
                    .where(
                        OutreachEmail.lead_id.in_(lead_ids),
                        OutreachEmail.status == "scheduled",
                    )
                    .distinct()
                )
            ).scalars().all()
        )
    else:
        active_outreach_ids = set()

    # Build radar entries — leads not already in active outreach
    radar_entries = []
    for lead in idle_leads:
        if lead.id in active_outreach_ids:
            continue
        days_since_contact = _days_since_contact(lead, now)
        entry = {
            "id": str(lead.id),
            "company": _lead_display_name(lead),
            "industry": lead.industry or "Unknown",
            "country": lead.country or "Unknown",
            "score": float(lead.score),
            "status": lead.status.value if lead.status else "NEW",
            "days_silent": days_since_contact,
            "priority": "HOT" if lead.score >= HOT_SCORE_THRESHOLD else "WARM",
            "recommended_action": _recommend_action(lead),
            "contact_email": lead.email or lead.contact_email or "",
            "contact_name": lead.contact_name or "",
        }
        radar_entries.append(entry)
        if len(radar_entries) >= MAX_RADAR_LEADS:
            break

    hot_count = sum(1 for e in radar_entries if e["priority"] == "HOT")
    warm_count = len(radar_entries) - hot_count

    report = {
        "generated_at": now.isoformat(),
        "tenant_id": str(tenant_id),
        "scan_config": {
            "score_threshold": OPPORTUNITY_SCORE_THRESHOLD,
            "hot_threshold": HOT_SCORE_THRESHOLD,
            "idle_days": IDLE_DAYS,
        },
        "summary": {
            "total_opportunities": len(radar_entries),
            "hot": hot_count,
            "warm": warm_count,
        },
        "leads": radar_entries,
    }

    # Deliver via Telegram
    if radar_entries:
        await _deliver_telegram(report)

    return report


def _is_idle(lead: Lead, idle_cutoff: datetime) -> bool:
    last = lead.last_contact or lead.last_contacted
    if last is None:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return last <= idle_cutoff


def _days_since_contact(lead: Lead, now: datetime) -> int:
    last = lead.last_contact or lead.last_contacted
    if last is None:
        return 999
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (now - last).days


def _lead_display_name(lead: Lead) -> str:
    return lead.company_name or lead.company or lead.contact_name or lead.email or "Unknown"


def _recommend_action(lead: Lead) -> str:
    if lead.score >= HOT_SCORE_THRESHOLD:
        return "Generate executive brief → send proposal"
    if lead.score >= 50:
        return "Send personalised outreach → schedule discovery call"
    return "Re-engage with value-add content"


async def _deliver_telegram(report: dict[str, Any]) -> None:
    lines = [
        f"🎯 JARVIS OPPORTUNITY RADAR — {report['generated_at'][:10]}",
        f"",
        f"📊 {report['summary']['total_opportunities']} opportunities identified",
        f"🔥 HOT ({report['summary']['hot']}) | WARM ({report['summary']['warm']})",
        f"",
        "TOP OPPORTUNITIES:",
    ]
    for i, lead in enumerate(report["leads"][:5], 1):
        priority_emoji = "🔥" if lead["priority"] == "HOT" else "⚡"
        lines.append(
            f"{i}. {priority_emoji} {lead['company']} "
            f"({lead['score']:.0f}/100 | {lead['days_silent']}d silent)"
        )
        lines.append(f"   → {lead['recommended_action']}")

    if report["summary"]["total_opportunities"] > 5:
        lines.append(f"   ... and {report['summary']['total_opportunities'] - 5} more")

    lines.extend(["", "Ready for your commands, Captain."])
    await notify_telegram("\n".join(lines))
