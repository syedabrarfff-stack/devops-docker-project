import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import case, func, select

from app.api.v1.routes.auth import get_current_captain
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.core.rate_limit import limiter
from app.models.lead import Lead, LeadStatus
from app.models.revenue import Client, ClientStatus, Invoice, InvoiceStatus, RevenueSnapshot
from app.services.governance.invoice_engine import invoice_engine

router = APIRouter(prefix="/revenue", tags=["revenue"], dependencies=[Depends(get_current_captain)])

# ── Tier / pipeline value estimates ───────────────────────────────────────────
_TIER_ACV = {"A": 8000.0, "B": 4000.0, "C": 2000.0}
_STATUS_PROBABILITY = {
    LeadStatus.PROPOSAL: 0.70,
    LeadStatus.DEMO: 0.40,
    LeadStatus.REPLIED: 0.20,
    LeadStatus.CONTACTED: 0.10,
    LeadStatus.NURTURE: 0.10,
    LeadStatus.NEW: 0.05,
    LeadStatus.WON: 1.0,
    LeadStatus.LOST: 0.0,
}


# ── Existing endpoints (preserved) ────────────────────────────────────────────

@router.get("/snapshot")
@limiter.limit("30/minute")
async def revenue_snapshot(request: Request, tenant_id: Optional[uuid.UUID] = None):
    tid = _resolve_tenant(request, tenant_id)
    return await invoice_engine.revenue_snapshot(tid)


@router.get("/mrr-chart")
@limiter.limit("20/minute")
async def revenue_mrr_chart(
    request: Request,
    tenant_id: Optional[uuid.UUID] = None,
    days: int = Query(default=90, ge=1, le=365),
):
    tid = _resolve_tenant(request, tenant_id)
    return {"points": await invoice_engine.mrr_chart(tid, days=days)}


# ── ARR ───────────────────────────────────────────────────────────────────────

@router.get("/arr")
@limiter.limit("30/minute")
async def revenue_arr(request: Request, tenant_id: Optional[uuid.UUID] = None):
    """Annual Recurring Revenue = MRR × 12, plus derived projections."""
    tid = _resolve_tenant(request, tenant_id)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tid))
            # Single GROUP BY replaces 3 sequential scalar queries
            client_rows = (await session.execute(
                select(
                    Client.status,
                    func.coalesce(func.sum(Client.mrr_usd), 0.0).label("mrr"),
                    func.count(Client.id).label("cnt"),
                )
                .where(Client.tenant_id == tid)
                .group_by(Client.status)
            )).all()

    c_agg: dict = {}
    for row in client_rows:
        key = row.status.value if hasattr(row.status, "value") else str(row.status)
        c_agg[key] = {"mrr": float(row.mrr or 0), "cnt": int(row.cnt or 0)}

    mrr = c_agg.get("ACTIVE", {}).get("mrr", 0.0)
    active = c_agg.get("ACTIVE", {}).get("cnt", 0)
    churned = c_agg.get("CHURNED", {}).get("cnt", 0)
    total_clients = active + churned
    churn_rate = (churned / total_clients * 100) if total_clients else 0.0
    avg_mrr_per_client = (mrr / active) if active else 0.0

    arr = mrr * 12
    return {
        "mrr_usd": round(mrr, 2),
        "arr_usd": round(arr, 2),
        "active_clients": active,
        "avg_mrr_per_client": round(avg_mrr_per_client, 2),
        "churn_rate_pct": round(churn_rate, 1),
        "arr_target_usd": 1_000_000.0,
        "arr_progress_pct": round(min(arr / 1_000_000.0 * 100, 100), 2),
    }


# ── Pipeline ──────────────────────────────────────────────────────────────────

@router.get("/pipeline")
@limiter.limit("20/minute")
async def revenue_pipeline(request: Request, tenant_id: Optional[uuid.UUID] = None):
    """Lead pipeline value weighted by conversion probability and tier ACV."""
    tid = _resolve_tenant(request, tenant_id)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tid))
            rows = (await session.execute(
                select(Lead.status, Lead.tier, Lead.score, Lead.industry, Lead.country)
                .where(Lead.tenant_id == tid)
                .limit(2000)
            )).all()

    stages: dict[str, dict] = {}
    total_weighted = 0.0
    for row in rows:
        status = row.status or LeadStatus.NEW
        tier = row.tier or "C"
        acv = _TIER_ACV.get(tier, 2000.0)
        prob = _STATUS_PROBABILITY.get(status, 0.05)
        weighted = acv * prob

        key = status.value if hasattr(status, "value") else str(status)
        if key not in stages:
            stages[key] = {"count": 0, "raw_value_usd": 0.0, "weighted_value_usd": 0.0, "probability": prob}
        stages[key]["count"] += 1
        stages[key]["raw_value_usd"] += acv
        stages[key]["weighted_value_usd"] += weighted
        total_weighted += weighted

    stage_order = ["NEW", "CONTACTED", "REPLIED", "DEMO", "NURTURE", "PROPOSAL", "WON", "LOST"]
    sorted_stages = [{"stage": s, **stages[s]} for s in stage_order if s in stages]

    return {
        "total_leads": len(rows),
        "weighted_pipeline_usd": round(total_weighted, 2),
        "stages": sorted_stages,
    }


# ── Forecast ──────────────────────────────────────────────────────────────────

@router.get("/forecast")
@limiter.limit("10/minute")
async def revenue_forecast(
    request: Request,
    tenant_id: Optional[uuid.UUID] = None,
    days: int = Query(default=90, ge=30, le=365),
):
    """90-day revenue forecast using MRR trend + pipeline conversion estimate."""
    tid = _resolve_tenant(request, tenant_id)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tid))

            # Last 90 days of MRR snapshots for growth rate
            cutoff = date.today() - timedelta(days=90)
            snapshots = (await session.execute(
                select(RevenueSnapshot.snapshot_date, RevenueSnapshot.mrr_usd)
                .where(RevenueSnapshot.tenant_id == tid, RevenueSnapshot.snapshot_date >= cutoff)
                .order_by(RevenueSnapshot.snapshot_date.asc())
            )).all()

            current_mrr = float(await session.scalar(
                select(func.coalesce(func.sum(Client.mrr_usd), 0.0)).where(
                    Client.tenant_id == tid, Client.status == ClientStatus.ACTIVE
                )
            ) or 0)

            pipeline_leads = (await session.execute(
                select(Lead.tier, Lead.status).where(
                    Lead.tenant_id == tid,
                    Lead.status.in_([LeadStatus.PROPOSAL, LeadStatus.DEMO, LeadStatus.REPLIED]),
                )
            )).all()

    # Calculate MoM growth rate from snapshots
    mom_growth = 0.0
    if len(snapshots) >= 2:
        first_mrr = float(snapshots[0].mrr_usd or 0)
        last_mrr = float(snapshots[-1].mrr_usd or 0)
        if first_mrr > 0:
            months_elapsed = max((snapshots[-1].snapshot_date - snapshots[0].snapshot_date).days / 30.0, 0.1)
            mom_growth = ((last_mrr / first_mrr) ** (1 / months_elapsed) - 1) if first_mrr > 0 else 0.0

    # Pipeline contribution estimate (30% of weighted value converts in 90 days)
    pipeline_30d = sum(
        _TIER_ACV.get(r.tier or "C", 2000.0) * _STATUS_PROBABILITY.get(r.status, 0.1) * 0.3
        for r in pipeline_leads
    )

    # Generate monthly forecast points
    points = []
    projected_mrr = current_mrr
    for month in range(1, (days // 30) + 2):
        projected_mrr = projected_mrr * (1 + mom_growth)
        month_date = (date.today().replace(day=1) + timedelta(days=30 * month)).isoformat()
        points.append({
            "month": month_date,
            "projected_mrr_usd": round(projected_mrr, 2),
            "projected_revenue_usd": round(projected_mrr * 1.0, 2),
        })

    forecast_revenue = sum(p["projected_revenue_usd"] for p in points)

    return {
        "current_mrr_usd": round(current_mrr, 2),
        "mom_growth_rate_pct": round(mom_growth * 100, 2),
        "pipeline_contribution_usd": round(pipeline_30d, 2),
        "forecast_days": days,
        "forecast_revenue_usd": round(forecast_revenue + pipeline_30d, 2),
        "points": points,
    }


# ── Cohorts ───────────────────────────────────────────────────────────────────

@router.get("/cohorts")
@limiter.limit("10/minute")
async def revenue_cohorts(request: Request, tenant_id: Optional[uuid.UUID] = None):
    """Client retention cohort analysis grouped by start month."""
    tid = _resolve_tenant(request, tenant_id)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tid))
            clients = (await session.execute(
                select(Client.id, Client.status, Client.started_at, Client.mrr_usd)
                .where(Client.tenant_id == tid)
            )).all()

    cohorts: dict[str, dict] = {}
    for c in clients:
        if not c.started_at:
            cohort_key = "unknown"
        else:
            dt = c.started_at if hasattr(c.started_at, "year") else datetime.fromisoformat(str(c.started_at))
            cohort_key = f"{dt.year}-{dt.month:02d}"

        if cohort_key not in cohorts:
            cohorts[cohort_key] = {"cohort_month": cohort_key, "started": 0, "active": 0, "churned": 0, "mrr_usd": 0.0}

        cohorts[cohort_key]["started"] += 1
        if c.status == ClientStatus.ACTIVE:
            cohorts[cohort_key]["active"] += 1
            cohorts[cohort_key]["mrr_usd"] += float(c.mrr_usd or 0)
        elif c.status == ClientStatus.CHURNED:
            cohorts[cohort_key]["churned"] += 1

    result = sorted(cohorts.values(), key=lambda x: x["cohort_month"])
    for c in result:
        c["retention_rate_pct"] = round(c["active"] / c["started"] * 100, 1) if c["started"] else 0.0
        c["mrr_usd"] = round(c["mrr_usd"], 2)

    total_started = sum(c["started"] for c in result)
    total_active = sum(c["active"] for c in result)

    return {
        "overall_retention_pct": round(total_active / total_started * 100, 1) if total_started else 0.0,
        "total_clients_ever": total_started,
        "cohorts": result,
    }


# ── Segments ──────────────────────────────────────────────────────────────────

@router.get("/segments")
@limiter.limit("20/minute")
async def revenue_segments(
    request: Request,
    tenant_id: Optional[uuid.UUID] = None,
    by: str = Query(default="industry", pattern="^(industry|country|tier|package)$"),
):
    """Revenue breakdown by segment: industry, country, tier, or package."""
    tid = _resolve_tenant(request, tenant_id)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tid))

            # Client MRR by segment
            clients = (await session.execute(
                select(Client.mrr_usd, Client.package_tier, Client.status)
                .where(Client.tenant_id == tid, Client.status == ClientStatus.ACTIVE)
            )).all()

            # Lead counts by segment
            leads = (await session.execute(
                select(Lead.industry, Lead.country, Lead.tier, Lead.status)
                .where(Lead.tenant_id == tid)
                .limit(2000)
            )).all()

    # Build client segment breakdown by package_tier
    client_segments: dict[str, dict] = {}
    for c in clients:
        key = (c.package_tier or "unspecified") if by == "package" else (c.package_tier or "unspecified")
        if key not in client_segments:
            client_segments[key] = {"segment": key, "client_count": 0, "mrr_usd": 0.0}
        client_segments[key]["client_count"] += 1
        client_segments[key]["mrr_usd"] += float(c.mrr_usd or 0)

    # Build lead segment breakdown
    lead_segments: dict[str, dict] = {}
    for lead in leads:
        if by == "industry":
            key = lead.industry or "unknown"
        elif by == "country":
            key = lead.country or "unknown"
        elif by == "tier":
            key = lead.tier or "C"
        else:
            key = "all"

        if key not in lead_segments:
            lead_segments[key] = {"segment": key, "lead_count": 0, "won": 0, "lost": 0, "pipeline": 0}
        lead_segments[key]["lead_count"] += 1
        status = lead.status
        if status == LeadStatus.WON:
            lead_segments[key]["won"] += 1
        elif status == LeadStatus.LOST:
            lead_segments[key]["lost"] += 1
        else:
            lead_segments[key]["pipeline"] += 1

    # Merge
    all_keys = set(client_segments.keys()) | set(lead_segments.keys())
    merged = []
    for key in sorted(all_keys):
        c = client_segments.get(key, {"client_count": 0, "mrr_usd": 0.0})
        l = lead_segments.get(key, {"lead_count": 0, "won": 0, "lost": 0, "pipeline": 0})
        win_rate = round(l["won"] / (l["won"] + l["lost"]) * 100, 1) if (l["won"] + l["lost"]) > 0 else None
        merged.append({
            "segment": key,
            "dimension": by,
            "active_clients": c["client_count"],
            "mrr_usd": round(c["mrr_usd"], 2),
            "arr_usd": round(c["mrr_usd"] * 12, 2),
            "total_leads": l["lead_count"],
            "won_leads": l["won"],
            "lost_leads": l["lost"],
            "pipeline_leads": l["pipeline"],
            "win_rate_pct": win_rate,
        })

    merged.sort(key=lambda x: x["mrr_usd"], reverse=True)
    return {"dimension": by, "segments": merged}


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health")
@limiter.limit("20/minute")
async def revenue_health(request: Request, tenant_id: Optional[uuid.UUID] = None):
    """Cash health: collected vs invoiced, outstanding, overdue amounts and counts."""
    tid = _resolve_tenant(request, tenant_id)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tid))

            # Single GROUP BY replaces 7 sequential scalar queries
            status_rows = (await session.execute(
                select(
                    Invoice.status,
                    func.coalesce(func.sum(Invoice.total), 0.0).label("total_amount"),
                    func.coalesce(func.sum(Invoice.paid_amount_usd), 0.0).label("paid_amount"),
                    func.count(Invoice.id).label("cnt"),
                )
                .where(Invoice.tenant_id == tid)
                .group_by(Invoice.status)
            )).all()

            agg: dict = {}
            for row in status_rows:
                key = row.status.value if hasattr(row.status, "value") else str(row.status)
                agg[key] = {"total": float(row.total_amount or 0), "paid": float(row.paid_amount or 0), "cnt": int(row.cnt or 0)}

            total_invoiced = sum(v["total"] for v in agg.values())
            total_paid = agg.get("PAID", {}).get("paid", 0.0)
            overdue_amount = agg.get("OVERDUE", {}).get("total", 0.0)
            overdue_count = agg.get("OVERDUE", {}).get("cnt", 0)
            sent_count = agg.get("SENT", {}).get("cnt", 0)
            sent_amount = agg.get("SENT", {}).get("total", 0.0)
            draft_count = agg.get("DRAFT", {}).get("cnt", 0)

            # 30-day collection (time-filtered — separate query required)
            cutoff_30d = datetime.now(UTC) - timedelta(days=30)
            collected_30d = float(await session.scalar(
                select(func.coalesce(func.sum(Invoice.paid_amount_usd), 0.0)).where(
                    Invoice.tenant_id == tid,
                    Invoice.status == InvoiceStatus.PAID,
                    Invoice.paid_at >= cutoff_30d,
                )
            ) or 0)

    collection_rate = round(total_paid / total_invoiced * 100, 1) if total_invoiced > 0 else 0.0

    return {
        "total_invoiced_usd": round(total_invoiced, 2),
        "total_collected_usd": round(total_paid, 2),
        "outstanding_usd": round(total_invoiced - total_paid, 2),
        "overdue_usd": round(overdue_amount, 2),
        "overdue_count": overdue_count,
        "awaiting_payment_usd": round(sent_amount, 2),
        "awaiting_payment_count": sent_count,
        "draft_count": draft_count,
        "collected_last_30d_usd": round(collected_30d, 2),
        "collection_rate_pct": collection_rate,
        "cash_score": _cash_score(collection_rate, overdue_count, overdue_amount, total_invoiced),
    }


# ── Clients ───────────────────────────────────────────────────────────────────

@router.get("/clients")
@limiter.limit("20/minute")
async def revenue_clients(
    request: Request,
    tenant_id: Optional[uuid.UUID] = None,
    status: str = Query(default="ACTIVE", pattern="^(ACTIVE|PAUSED|CHURNED|ALL)$"),
):
    """Active client breakdown with MRR, lifetime paid, and invoice counts."""
    tid = _resolve_tenant(request, tenant_id)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tid))
            q = select(Client).where(Client.tenant_id == tid)
            if status != "ALL":
                q = q.where(Client.status == ClientStatus(status))
            clients = (await session.execute(q.order_by(Client.mrr_usd.desc()).limit(500))).scalars().all()

            # Single aggregation query for all clients — eliminates N+1
            client_ids = [c.id for c in clients]
            inv_agg: dict[int, tuple[float, int]] = {}
            if client_ids:
                agg_rows = (await session.execute(
                    select(
                        Invoice.client_id,
                        func.coalesce(
                            func.sum(
                                case(
                                    (Invoice.status == InvoiceStatus.PAID, Invoice.paid_amount_usd),
                                    else_=None,
                                )
                            ),
                            0.0,
                        ).label("paid"),
                        func.count(Invoice.id).label("inv_count"),
                    )
                    .where(Invoice.tenant_id == tid, Invoice.client_id.in_(client_ids))
                    .group_by(Invoice.client_id)
                )).all()
                inv_agg = {row.client_id: (float(row.paid or 0), int(row.inv_count or 0)) for row in agg_rows}

            result = []
            for c in clients:
                paid, inv_count = inv_agg.get(c.id, (0.0, 0))
                months_active = None
                if c.started_at:
                    delta = datetime.now(UTC) - (c.started_at if c.started_at.tzinfo else c.started_at.replace(tzinfo=UTC))
                    months_active = max(1, round(delta.days / 30))
                result.append({
                    "id": str(c.id),
                    "company_name": c.company_name,
                    "contact_name": c.contact_name,
                    "package_tier": c.package_tier,
                    "mrr_usd": round(float(c.mrr_usd or 0), 2),
                    "arr_usd": round(float(c.mrr_usd or 0) * 12, 2),
                    "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                    "started_at": c.started_at.isoformat() if c.started_at else None,
                    "months_active": months_active,
                    "lifetime_paid_usd": round(paid, 2),
                    "ltv_estimate_usd": round(float(c.mrr_usd or 0) * 24, 2),
                    "invoice_count": inv_count,
                })

    return {
        "status_filter": status,
        "count": len(result),
        "total_mrr_usd": round(sum(c["mrr_usd"] for c in result), 2),
        "clients": result,
    }


# ── War Room (all-in-one) ─────────────────────────────────────────────────────

@router.get("/war-room")
@limiter.limit("10/minute")
async def revenue_war_room(request: Request, tenant_id: Optional[uuid.UUID] = None):
    """All 5 Revenue Command Center metrics in a single call."""
    tid = _resolve_tenant(request, tenant_id)

    arr_data, pipeline_data, health_data, cohort_data = await _gather_war_room(tid)

    # Compute an executive summary score (0–100)
    arr_progress = arr_data["arr_progress_pct"]
    pipeline_health = min(pipeline_data["weighted_pipeline_usd"] / 50_000 * 30, 30)
    cash_score = health_data["cash_score"] * 0.4
    retention = cohort_data["overall_retention_pct"] * 0.3
    exec_score = round(min(arr_progress * 0.3 + pipeline_health + cash_score + retention, 100), 1)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "executive_score": exec_score,
        "arr": arr_data,
        "pipeline": {
            "weighted_pipeline_usd": pipeline_data["weighted_pipeline_usd"],
            "total_leads": pipeline_data["total_leads"],
            "stages": pipeline_data["stages"],
        },
        "health": health_data,
        "retention": {
            "overall_retention_pct": cohort_data["overall_retention_pct"],
            "total_clients_ever": cohort_data["total_clients_ever"],
        },
        "alerts": _build_alerts(arr_data, health_data, cohort_data),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_tenant(request: Request, explicit_id: Optional[uuid.UUID]) -> uuid.UUID:
    from app.core.config import settings

    tid = (
        explicit_id
        or getattr(request.state, "tenant_id", None)
        or request.headers.get("X-Tenant-ID")
        or settings.JARVIS_DEFAULT_TENANT_ID
    )
    if not tid:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    try:
        return uuid.UUID(str(tid))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="tenant_id must be a valid UUID") from exc


async def _gather_war_room(tid: uuid.UUID):
    from asyncio import gather

    async def _arr():
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tid))
                # Single GROUP BY replaces 3 sequential scalar queries
                rows = (await session.execute(
                    select(
                        Client.status,
                        func.coalesce(func.sum(Client.mrr_usd), 0.0).label("mrr"),
                        func.count(Client.id).label("cnt"),
                    )
                    .where(Client.tenant_id == tid)
                    .group_by(Client.status)
                )).all()

        c: dict = {}
        for row in rows:
            key = row.status.value if hasattr(row.status, "value") else str(row.status)
            c[key] = {"mrr": float(row.mrr or 0), "cnt": int(row.cnt or 0)}

        mrr = c.get("ACTIVE", {}).get("mrr", 0.0)
        active = c.get("ACTIVE", {}).get("cnt", 0)
        churned = c.get("CHURNED", {}).get("cnt", 0)
        total = active + churned
        churn = (churned / total * 100) if total else 0.0
        arr = mrr * 12
        return {
            "mrr_usd": round(mrr, 2),
            "arr_usd": round(arr, 2),
            "active_clients": active,
            "churn_rate_pct": round(churn, 1),
            "arr_progress_pct": round(min(arr / 1_000_000.0 * 100, 100), 2),
        }

    async def _pipeline():
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tid))
                rows = (await session.execute(
                    select(Lead.status, Lead.tier).where(Lead.tenant_id == tid).limit(2000)
                )).all()
        stages: dict = {}
        total_w = 0.0
        for r in rows:
            status = r.status or LeadStatus.NEW
            key = status.value if hasattr(status, "value") else str(status)
            acv = _TIER_ACV.get(r.tier or "C", 2000.0)
            prob = _STATUS_PROBABILITY.get(status, 0.05)
            w = acv * prob
            stages.setdefault(key, {"stage": key, "count": 0, "weighted_value_usd": 0.0, "probability": prob})
            stages[key]["count"] += 1
            stages[key]["weighted_value_usd"] += w
            total_w += w
        return {
            "total_leads": len(rows),
            "weighted_pipeline_usd": round(total_w, 2),
            "stages": list(stages.values()),
        }

    async def _health():
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tid))
                # Single GROUP BY replaces 4 sequential scalar queries
                rows = (await session.execute(
                    select(
                        Invoice.status,
                        func.coalesce(func.sum(Invoice.total), 0.0).label("total_amount"),
                        func.coalesce(func.sum(Invoice.paid_amount_usd), 0.0).label("paid_amount"),
                        func.count(Invoice.id).label("cnt"),
                    )
                    .where(Invoice.tenant_id == tid)
                    .group_by(Invoice.status)
                )).all()

        agg: dict = {}
        for row in rows:
            key = row.status.value if hasattr(row.status, "value") else str(row.status)
            agg[key] = {"total": float(row.total_amount or 0), "paid": float(row.paid_amount or 0), "cnt": int(row.cnt or 0)}

        invoiced = sum(v["total"] for v in agg.values())
        paid = agg.get("PAID", {}).get("paid", 0.0)
        overdue_amt = agg.get("OVERDUE", {}).get("total", 0.0)
        overdue_cnt = agg.get("OVERDUE", {}).get("cnt", 0)
        rate = round(paid / invoiced * 100, 1) if invoiced > 0 else 0.0
        return {
            "total_invoiced_usd": round(invoiced, 2),
            "total_collected_usd": round(paid, 2),
            "outstanding_usd": round(invoiced - paid, 2),
            "overdue_usd": round(overdue_amt, 2),
            "overdue_count": overdue_cnt,
            "collection_rate_pct": rate,
            "cash_score": _cash_score(rate, overdue_cnt, overdue_amt, invoiced),
        }

    async def _cohorts():
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tid))
                clients = (await session.execute(
                    select(Client.status).where(Client.tenant_id == tid).limit(2000)
                )).all()
        total = len(clients)
        active = sum(1 for c in clients if c.status == ClientStatus.ACTIVE)
        return {
            "overall_retention_pct": round(active / total * 100, 1) if total else 0.0,
            "total_clients_ever": total,
        }

    return await gather(_arr(), _pipeline(), _health(), _cohorts())


def _cash_score(collection_rate: float, overdue_count: int, overdue_amount: float, total_invoiced: float) -> float:
    score = min(collection_rate, 100.0)
    if overdue_count > 0:
        score -= min(overdue_count * 5, 30)
    if total_invoiced > 0 and overdue_amount / total_invoiced > 0.2:
        score -= 10
    return round(max(score, 0.0), 1)


def _build_alerts(arr: dict, health: dict, cohort: dict) -> list[dict]:
    alerts = []
    if health["overdue_count"] > 0:
        alerts.append({
            "type": "overdue_invoices",
            "severity": "high" if health["overdue_count"] >= 3 else "medium",
            "message": f"{health['overdue_count']} invoice(s) overdue — ${health['overdue_usd']:,.0f} at risk",
        })
    if health["collection_rate_pct"] < 80:
        alerts.append({
            "type": "low_collection_rate",
            "severity": "high",
            "message": f"Collection rate {health['collection_rate_pct']}% — below 80% threshold",
        })
    if arr["churn_rate_pct"] > 20:
        alerts.append({
            "type": "high_churn",
            "severity": "high",
            "message": f"Churn rate {arr['churn_rate_pct']}% — review client health immediately",
        })
    if cohort["overall_retention_pct"] < 70:
        alerts.append({
            "type": "low_retention",
            "severity": "medium",
            "message": f"Retention at {cohort['overall_retention_pct']}% — investigate churned clients",
        })
    if not alerts:
        alerts.append({"type": "all_clear", "severity": "info", "message": "All revenue metrics within healthy range"})
    return alerts
