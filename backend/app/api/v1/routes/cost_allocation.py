"""
Multi-Tenant Cost Allocation & Billing API
Tracks per-tenant costs, ROI, and billing-ready summaries.
"""
from datetime import datetime, date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.core.tenant_context import get_current_tenant_id
from app.models.ai_audit import AIRequestLog
from app.models.revenue import Client, ClientStatus
from app.models.approval import ApprovalRequest, ApprovalStatus

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/costs/tenant/{tenant_id}")
async def get_tenant_costs(
    tenant_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get total costs for a specific tenant over a date range."""
    try:
        import uuid
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")

    try:
        # Parse dates
        if start_date:
            start = datetime.fromisoformat(start_date)
        else:
            start = datetime.combine(date.today() - timedelta(days=30), datetime.min.time())

        if end_date:
            end = datetime.fromisoformat(end_date)
        else:
            end = datetime.combine(date.today(), datetime.max.time())

        # Query costs
        result = await db.execute(
            select(
                AIRequestLog.provider,
                func.sum(AIRequestLog.cost_estimate_usd).label("total_cost"),
                func.sum(AIRequestLog.tokens_used).label("total_tokens"),
                func.count().label("total_requests"),
                func.avg(AIRequestLog.latency_ms).label("avg_latency"),
            )
            .where(AIRequestLog.tenant_id == tid)
            .where(AIRequestLog.created_at.between(start, end))
            .group_by(AIRequestLog.provider)
        )
        rows = result.fetchall()

        by_provider = {}
        total_cost = 0
        for row in rows:
            cost = round(row.total_cost or 0, 4)
            by_provider[row.provider] = {
                "cost_usd": cost,
                "tokens": int(row.total_tokens or 0),
                "requests": int(row.total_requests or 0),
                "avg_latency_ms": int(row.avg_latency or 0),
            }
            total_cost += cost

        return {
            "tenant_id": tenant_id,
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "total_cost_usd": round(total_cost, 4),
            "by_provider": by_provider,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/costs/summary/{tenant_id}")
async def get_tenant_cost_summary(
    tenant_id: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed cost summary for a tenant with daily breakdown."""
    try:
        import uuid
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")

    try:
        from sqlalchemy import cast, Date as SADate

        today = date.today()
        window_start = datetime.combine(today - timedelta(days=days - 1), datetime.min.time())

        # Daily costs
        result = await db.execute(
            select(
                cast(AIRequestLog.created_at, SADate).label("day"),
                AIRequestLog.provider,
                func.sum(AIRequestLog.cost_estimate_usd).label("cost"),
                func.sum(AIRequestLog.tokens_used).label("tokens"),
                func.count().label("requests"),
            )
            .where(AIRequestLog.tenant_id == tid)
            .where(AIRequestLog.created_at >= window_start)
            .group_by(cast(AIRequestLog.created_at, SADate), AIRequestLog.provider)
            .order_by(cast(AIRequestLog.created_at, SADate).desc())
        )
        rows = result.fetchall()

        daily_breakdown = {}
        for row in rows:
            day_str = str(row.day)
            if day_str not in daily_breakdown:
                daily_breakdown[day_str] = {
                    "date": row.day.isoformat(),
                    "total_cost_usd": 0,
                    "total_tokens": 0,
                    "total_requests": 0,
                    "by_provider": {},
                }

            cost = round(row.cost or 0, 4)
            daily_breakdown[day_str]["total_cost_usd"] += cost
            daily_breakdown[day_str]["total_tokens"] += int(row.tokens or 0)
            daily_breakdown[day_str]["total_requests"] += int(row.requests or 0)
            daily_breakdown[day_str]["by_provider"][row.provider] = {
                "cost_usd": cost,
                "tokens": int(row.tokens or 0),
                "requests": int(row.requests or 0),
            }

        daily_breakdown[day_str]["total_cost_usd"] = round(daily_breakdown[day_str]["total_cost_usd"], 4)

        days_list = sorted(daily_breakdown.values(), key=lambda x: x["date"], reverse=True)
        total = sum(d["total_cost_usd"] for d in days_list)

        return {
            "tenant_id": tenant_id,
            "period_days": days,
            "total_cost_usd": round(total, 4),
            "avg_daily_usd": round(total / days if days > 0 else 0, 4),
            "daily_breakdown": days_list,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/roi/{tenant_id}")
async def get_tenant_roi(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Calculate ROI for a tenant based on revenue vs. API costs."""
    try:
        import uuid
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")

    try:
        # Get client data
        client_result = await db.execute(
            select(Client).where(Client.tenant_id == tid).limit(1)
        )
        client = client_result.scalar_one_or_none()

        if not client:
            return {
                "tenant_id": tenant_id,
                "error": "No client found for tenant",
                "status": "no_client",
            }

        # Get 30-day costs
        today = date.today()
        start = datetime.combine(today - timedelta(days=30), datetime.min.time())
        end = datetime.combine(today, datetime.max.time())

        cost_result = await db.execute(
            select(func.sum(AIRequestLog.cost_estimate_usd).label("total"))
            .where(AIRequestLog.tenant_id == tid)
            .where(AIRequestLog.created_at.between(start, end))
        )
        total_cost = round(cost_result.scalar() or 0, 4)

        # Calculate ROI
        mrr = float(client.mrr_usd or 0)
        roi = ((mrr - total_cost) / max(mrr, 0.01)) * 100 if mrr > 0 else 0

        return {
            "tenant_id": tenant_id,
            "period": "30_days",
            "revenue_mrr": round(mrr, 2),
            "ai_costs_30d": total_cost,
            "monthly_net": round(mrr - total_cost, 2),
            "roi_percentage": round(roi, 1),
            "roi_status": "positive" if roi > 0 else "negative",
            "cost_efficiency": round((total_cost / max(mrr, 0.01)) * 100, 1),  # % of MRR spent on AI
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/invoice-ready/{tenant_id}")
async def get_invoice_ready_data(
    tenant_id: str,
    month: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get invoice-ready data for a tenant (for billing automation)."""
    try:
        import uuid
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")

    try:
        # Parse month (YYYY-MM format)
        if month:
            invoice_month = datetime.strptime(month, "%Y-%m").date()
        else:
            today = date.today()
            invoice_month = today.replace(day=1)

        month_start = datetime.combine(invoice_month, datetime.min.time())
        next_month = invoice_month + timedelta(days=32)
        month_end = datetime.combine(next_month.replace(day=1) - timedelta(days=1), datetime.max.time())

        # Get client
        client_result = await db.execute(
            select(Client).where(Client.tenant_id == tid)
        )
        client = client_result.scalar_one_or_none()

        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Get costs for the month
        cost_result = await db.execute(
            select(
                AIRequestLog.provider,
                func.sum(AIRequestLog.cost_estimate_usd).label("cost"),
                func.sum(AIRequestLog.tokens_used).label("tokens"),
                func.count().label("requests"),
            )
            .where(AIRequestLog.tenant_id == tid)
            .where(AIRequestLog.created_at.between(month_start, month_end))
            .group_by(AIRequestLog.provider)
        )
        cost_rows = cost_result.fetchall()

        ai_costs = {}
        total_ai_cost = 0
        for row in cost_rows:
            cost = round(row.cost or 0, 4)
            ai_costs[row.provider] = {
                "cost_usd": cost,
                "tokens": int(row.tokens or 0),
                "requests": int(row.requests or 0),
            }
            total_ai_cost += cost

        # Prepare invoice data
        return {
            "invoice_period": {
                "month": invoice_month.isoformat(),
                "start_date": month_start.isoformat(),
                "end_date": month_end.isoformat(),
            },
            "client": {
                "id": str(client.id),
                "name": client.name,
                "email": client.email,
                "status": client.status,
            },
            "charges": {
                "ai_api_costs": {
                    "description": "Artificial Intelligence API Usage",
                    "total_usd": round(total_ai_cost, 2),
                    "breakdown": ai_costs,
                },
            },
            "summary": {
                "subtotal_usd": round(total_ai_cost, 2),
                "tax_usd": round(total_ai_cost * 0.1, 2),  # Placeholder: 10% tax
                "total_usd": round(total_ai_cost * 1.1, 2),
                "due_date": (month_end + timedelta(days=15)).isoformat(),
            },
            "ready_for_billing": total_ai_cost > 0,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/billing-report")
async def get_billing_report(
    month: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get billing report across all active clients (admin only)."""
    try:
        # Parse month
        if month:
            report_month = datetime.strptime(month, "%Y-%m").date()
        else:
            today = date.today()
            report_month = today.replace(day=1)

        month_start = datetime.combine(report_month, datetime.min.time())
        next_month = report_month + timedelta(days=32)
        month_end = datetime.combine(next_month.replace(day=1) - timedelta(days=1), datetime.max.time())

        # Get all active clients
        clients_result = await db.execute(
            select(Client).where(Client.status == ClientStatus.ACTIVE)
        )
        clients = clients_result.scalars().all()

        invoices = []
        total_revenue = 0
        total_ai_costs = 0

        for client in clients:
            # Get costs for this client
            cost_result = await db.execute(
                select(func.sum(AIRequestLog.cost_estimate_usd).label("cost"))
                .where(AIRequestLog.tenant_id == client.tenant_id)
                .where(AIRequestLog.created_at.between(month_start, month_end))
            )
            ai_cost = round(cost_result.scalar() or 0, 4)

            mrr = float(client.mrr_usd or 0)
            total_revenue += mrr
            total_ai_costs += ai_cost

            invoices.append({
                "client_id": str(client.id),
                "client_name": client.name,
                "mrr_usd": round(mrr, 2),
                "ai_costs_usd": ai_cost,
                "net_profit_usd": round(mrr - ai_cost, 2),
                "profit_margin_percent": round(((mrr - ai_cost) / max(mrr, 0.01)) * 100, 1),
            })

        return {
            "period": report_month.isoformat(),
            "total_clients": len(clients),
            "total_mrr_usd": round(total_revenue, 2),
            "total_ai_costs_usd": round(total_ai_costs, 2),
            "total_net_profit_usd": round(total_revenue - total_ai_costs, 2),
            "overall_margin_percent": round(
                ((total_revenue - total_ai_costs) / max(total_revenue, 0.01)) * 100, 1
            ),
            "invoices": sorted(invoices, key=lambda x: x["ai_costs_usd"], reverse=True),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
