"""
AI-Powered Optimization Recommendations Engine
Analyzes usage patterns and suggests ROI improvements, cost optimization, and upsells.
"""
from datetime import datetime, date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.ai_audit import AIRequestLog
from app.models.revenue import Client, ClientStatus

router = APIRouter(prefix="/api/v1/optimization", tags=["optimization"])


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/recommendations/{tenant_id}")
async def get_optimization_recommendations(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get AI-generated optimization recommendations for a tenant."""
    try:
        import uuid
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")

    try:
        # Get client data
        client_result = await db.execute(
            select(Client).where(Client.tenant_id == tid)
        )
        client = client_result.scalar_one_or_none()

        if not client:
            return {"tenant_id": tenant_id, "error": "Client not found", "recommendations": []}

        # Get 30-day usage data
        today = date.today()
        start = datetime.combine(today - timedelta(days=30), datetime.min.time())
        end = datetime.combine(today, datetime.max.time())

        # Costs by provider
        cost_result = await db.execute(
            select(
                AIRequestLog.provider,
                func.sum(AIRequestLog.cost_estimate_usd).label("cost"),
                func.count().label("requests"),
            )
            .where(AIRequestLog.tenant_id == tid)
            .where(AIRequestLog.created_at.between(start, end))
            .group_by(AIRequestLog.provider)
        )
        provider_costs = {row.provider: {"cost": round(row.cost or 0, 4), "requests": row.requests} for row in cost_result.fetchall()}

        # Total metrics
        total_result = await db.execute(
            select(
                func.sum(AIRequestLog.cost_estimate_usd).label("total_cost"),
                func.count().label("total_requests"),
                func.avg(AIRequestLog.latency_ms).label("avg_latency"),
            )
            .where(AIRequestLog.tenant_id == tid)
            .where(AIRequestLog.created_at.between(start, end))
        )
        total_row = total_result.fetchone()

        total_cost = round(total_row.total_cost or 0, 4)
        total_requests = total_row.total_requests or 0
        avg_latency = int(total_row.avg_latency or 0)
        mrr = float(client.mrr_usd or 0)

        recommendations = []

        # 1. Cost Optimization - Multiple expensive providers
        expensive_providers = [(p, c["cost"]) for p, c in provider_costs.items() if c["cost"] > 10]
        if len(expensive_providers) > 1:
            recommendations.append({
                "id": "cost_consolidation",
                "category": "Cost Optimization",
                "severity": "medium",
                "title": "Consolidate AI Provider Usage",
                "description": f"You're using {len(expensive_providers)} expensive providers. Consider consolidating to the most cost-effective option for your use cases.",
                "current_state": f"Using {', '.join([p for p, _ in expensive_providers])}",
                "potential_savings_usd": round(total_cost * 0.15, 2),  # 15% potential savings
                "implementation_effort": "Low — Configuration change only",
                "roi_months": 1,
            })

        # 2. Usage Efficiency - High latency
        if avg_latency > 2000:  # >2s average
            recommendations.append({
                "id": "latency_optimization",
                "category": "Performance",
                "severity": "high",
                "title": "Reduce API Latency",
                "description": "Your average API latency is above optimal. This may indicate provider issues or excessive payload sizes.",
                "current_state": f"Average latency: {avg_latency}ms",
                "expected_improvement": "50-75% latency reduction",
                "implementation_effort": "Medium — May require batch size tuning",
                "roi_impact": "Faster processing, better user experience",
            })

        # 3. Upsell - High volume low cost
        if total_requests > 10000 and total_cost < 100:
            recommendations.append({
                "id": "advanced_features",
                "category": "Service Upsell",
                "severity": "low",
                "title": "Enable Advanced AI Features",
                "description": f"With {total_requests:,} requests/month, you qualify for advanced features including:\n- Semantic search & vector embeddings\n- Long-context analysis (200k+ tokens)\n- Fine-tuned models for your domain",
                "current_state": f"{total_requests:,} requests on basic tier",
                "upgrade_path": "Advanced AI Tier (+$500/month)",
                "expected_roi": "2-3x productivity improvement",
                "implementation_effort": "Minimal — Configuration only",
            })

        # 4. ROI Optimization - Low margin
        roi = ((mrr - total_cost) / max(mrr, 0.01)) * 100 if mrr > 0 else 0
        if roi < 50:  # Less than 50% margin
            recommendations.append({
                "id": "margin_improvement",
                "category": "Revenue Operations",
                "severity": "high" if roi < 20 else "medium",
                "title": "Improve Service Margin",
                "description": f"Your current margin is {roi:.0f}%. Industry benchmark is 70-80%. Consider price optimization or service tiering.",
                "current_state": f"MRR: ${mrr:.2f}, AI Costs: ${total_cost:.2f}/30d, Margin: {roi:.1f}%",
                "action_items": [
                    "Review pricing against competitor offerings",
                    "Implement service-level tiering (Basic/Pro/Enterprise)",
                    "Consider volume discounts for long-term commitments",
                ],
                "potential_improvement": f"${((mrr * 0.75) - total_cost) - (mrr - total_cost):.2f} additional profit",
            })

        # 5. Automation Opportunity
        if total_requests > 5000 and avg_latency < 1000:
            recommendations.append({
                "id": "workflow_automation",
                "category": "Automation",
                "severity": "low",
                "title": "Automate Repetitive Workflows",
                "description": "Your system is reliable and fast. Consider automating recurring tasks like lead scoring, email categorization, or report generation.",
                "estimated_time_saved": "20-40 hours/month",
                "cost_of_automation": "Included in plan",
                "roi_calculation": "40h × $50/h average = $2,000/month value",
            })

        # 6. Batch Processing Opportunity
        if total_requests > 1000 and total_cost > 50:
            avg_cost_per_request = total_cost / max(total_requests, 1)
            recommendations.append({
                "id": "batch_processing",
                "category": "Cost Optimization",
                "severity": "low",
                "title": "Use Batch Processing for Non-Real-time Tasks",
                "description": "Batch API calls can reduce costs by 30-40% for non-real-time operations while maintaining accuracy.",
                "current_avg_cost_per_request": f"${avg_cost_per_request:.6f}",
                "potential_savings": f"${round(total_cost * 0.30, 2)}/month",
                "suitable_for": "Lead scoring, batch email analysis, report generation, data enrichment",
            })

        # Sort by severity (high > medium > low)
        severity_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 3))

        return {
            "tenant_id": tenant_id,
            "analysis_period": "30_days",
            "current_metrics": {
                "total_requests": total_requests,
                "total_cost_usd": total_cost,
                "avg_latency_ms": avg_latency,
                "mrr_usd": round(mrr, 2),
                "margin_percent": round(roi, 1),
            },
            "recommendations": recommendations,
            "next_review_date": (today + timedelta(days=7)).isoformat(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/savings-calculator/{tenant_id}")
async def calculate_potential_savings(
    tenant_id: str,
    scenario: str = Query("conservative", regex="^(conservative|moderate|aggressive)$"),
    db: AsyncSession = Depends(get_db),
):
    """Calculate potential cost savings under different optimization scenarios."""
    try:
        import uuid
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")

    try:
        today = date.today()
        start = datetime.combine(today - timedelta(days=30), datetime.min.time())
        end = datetime.combine(today, datetime.max.time())

        # Get current costs
        cost_result = await db.execute(
            select(func.sum(AIRequestLog.cost_estimate_usd).label("cost"))
            .where(AIRequestLog.tenant_id == tid)
            .where(AIRequestLog.created_at.between(start, end))
        )
        current_monthly_cost = round(cost_result.scalar() or 0, 4)

        # Define scenarios
        scenarios_config = {
            "conservative": {
                "cost_reduction": 0.10,  # 10% reduction
                "description": "Provider consolidation + minor optimizations",
            },
            "moderate": {
                "cost_reduction": 0.25,  # 25% reduction
                "description": "Smart routing + batch processing + provider selection",
            },
            "aggressive": {
                "cost_reduction": 0.40,  # 40% reduction
                "description": "Full optimization + caching + fine-tuned models",
            },
        }

        config = scenarios_config.get(scenario, scenarios_config["conservative"])
        current_annual = current_monthly_cost * 12
        reduction_amount = current_monthly_cost * config["cost_reduction"]
        optimized_monthly = current_monthly_cost - reduction_amount
        optimized_annual = optimized_monthly * 12
        total_annual_savings = reduction_amount * 12

        return {
            "tenant_id": tenant_id,
            "scenario": scenario,
            "description": config["description"],
            "current_state": {
                "monthly_cost_usd": round(current_monthly_cost, 2),
                "annual_cost_usd": round(current_annual, 2),
            },
            "optimized_state": {
                "monthly_cost_usd": round(optimized_monthly, 2),
                "annual_cost_usd": round(optimized_annual, 2),
            },
            "savings": {
                "monthly_usd": round(reduction_amount, 2),
                "annual_usd": round(total_annual_savings, 2),
                "percentage": f"{config['cost_reduction'] * 100:.0f}%",
            },
            "implementation_timeline": {
                "conservative": "1-2 weeks",
                "moderate": "2-4 weeks",
                "aggressive": "4-8 weeks",
            }[scenario],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/acknowledge-recommendation/{tenant_id}/{recommendation_id}")
async def acknowledge_recommendation(
    tenant_id: str,
    recommendation_id: str,
    action: str = Query("noted", regex="^(noted|implementing|dismissed)$"),
    db: AsyncSession = Depends(get_db),
):
    """Track recommendation acknowledgment for follow-up."""
    try:
        # TODO: Implement recommendation acknowledgment tracking
        return {
            "tenant_id": tenant_id,
            "recommendation_id": recommendation_id,
            "action": action,
            "acknowledged_at": datetime.now().isoformat(),
            "status": "tracked",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
