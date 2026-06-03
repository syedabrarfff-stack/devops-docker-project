# JARVIS CODEX BATCH 2 — INTELLIGENCE ENGINES
## Build after Batch 1 is confirmed live

---

## CONTEXT

Working directory: `/home/ubuntu/jarvis_sales_pipeline/`
Prerequisites: Batch 1 complete and all tables from migration 0009 exist.
Deploy: `docker-compose up -d --build jarvis_app`

This batch covers:
- Prospect Psychology Engine (scrape pain signals before Email 1)
- Intent-Aware Lead Scoring — 6 signals, 0-100 with reason codes
- Memory Synthesis Engine (weekly synthesis cycle → operating beliefs)
- Revenue Forecasting Engine (Monte Carlo, P10/P50/P90, leakage detection)
- Autonomous Governance Engine (Tier 1/2/3 decision framework)
- Proposal Intelligence Engine (pre-send scoring + engagement tracking)
- Client Onboarding Orchestration (zero-touch from deal-won)
- Operational Self-Assessment Engine (weekly self-rating A-F)
- Client Health & Churn Prediction (0-100 score)
- Dynamic Pricing Engine (market-aware recommendations)
- Adaptive AI Model Router (performance-based routing weights)

---

## STEP 1 — DATABASE MIGRATION

Create: `alembic/versions/0010_intelligence_engines.py`

```python
"""intelligence engines tables

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

revision = '0010'
down_revision = '0009'


def upgrade():
    op.create_table('prospect_psychology',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('contact_id', sa.Integer()),
        sa.Column('pain_indicators', JSONB, default=list),
        sa.Column('primary_pain', sa.Text()),
        sa.Column('confidence_score', sa.Float(), default=0.0),
        sa.Column('linkedin_headline', sa.Text()),
        sa.Column('company_job_signals', JSONB),
        sa.Column('scraped_at', sa.DateTime(timezone=True)),
        sa.Column('applied_to_email', sa.Boolean(), default=False),
    )

    op.create_table('lead_score_history',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('lead_id', sa.Integer()),
        sa.Column('score', sa.Integer()),
        sa.Column('signal_breakdown', JSONB),
        sa.Column('scored_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('operating_beliefs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('belief_text', sa.Text(), nullable=False),
        sa.Column('category', sa.String(100)),
        sa.Column('confidence', sa.Float(), default=0.5),
        sa.Column('source_memory_count', sa.Integer(), default=1),
        sa.Column('validated_by_captain', sa.Boolean(), default=False),
        sa.Column('synthesis_date', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('times_applied', sa.Integer(), default=0),
    )

    op.create_table('revenue_forecasts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('forecast_date', sa.Date()),
        sa.Column('horizon_days', sa.Integer()),
        sa.Column('p10_revenue', sa.Float()),
        sa.Column('p50_revenue', sa.Float()),
        sa.Column('p90_revenue', sa.Float()),
        sa.Column('simulation_runs', sa.Integer(), default=1000),
        sa.Column('pipeline_value', sa.Float()),
        sa.Column('active_deals', sa.Integer()),
        sa.Column('leakage_deals', JSONB),
        sa.Column('assumptions', JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('autonomous_decisions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('decision_type', sa.String(100)),
        sa.Column('tier', sa.Integer()),  # 1=auto, 2=propose, 3=captain-only
        sa.Column('description', sa.Text()),
        sa.Column('rationale', sa.Text()),
        sa.Column('outcome', sa.String(100)),
        sa.Column('captain_override', sa.Boolean(), default=False),
        sa.Column('override_outcome', sa.String(255)),
        sa.Column('decided_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('onboarding_checkpoints',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.Integer()),
        sa.Column('proposal_id', sa.Integer()),
        sa.Column('contract_sent', sa.Boolean(), default=False),
        sa.Column('contract_signed', sa.Boolean(), default=False),
        sa.Column('payment_received', sa.Boolean(), default=False),
        sa.Column('access_granted', sa.Boolean(), default=False),
        sa.Column('kickoff_scheduled', sa.Boolean(), default=False),
        sa.Column('kickoff_done', sa.Boolean(), default=False),
        sa.Column('first_deliverable_scheduled', sa.Boolean(), default=False),
        sa.Column('onboarding_complete', sa.Boolean(), default=False),
        sa.Column('sla_deadline', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('self_assessments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('assessment_date', sa.Date()),
        sa.Column('jobs_grade', sa.String(2)),
        sa.Column('lead_quality_grade', sa.String(2)),
        sa.Column('outreach_grade', sa.String(2)),
        sa.Column('proposal_grade', sa.String(2)),
        sa.Column('response_time_grade', sa.String(2)),
        sa.Column('overall_grade', sa.String(2)),
        sa.Column('top_improvements', JSONB),
        sa.Column('metrics_snapshot', JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('client_health_scores',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.Integer()),
        sa.Column('score', sa.Integer()),
        sa.Column('status', sa.String(20)),  # healthy/watch/at_risk
        sa.Column('signal_breakdown', JSONB),
        sa.Column('last_contact_days', sa.Integer()),
        sa.Column('action_triggered', sa.Boolean(), default=False),
        sa.Column('action_note', sa.Text()),
        sa.Column('scored_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('ai_routing_performance',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('provider', sa.String(100)),
        sa.Column('task_type', sa.String(100)),
        sa.Column('latency_ms', sa.Float()),
        sa.Column('quality_score', sa.Float()),
        sa.Column('cost_usd', sa.Float()),
        sa.Column('success', sa.Boolean()),
        sa.Column('error_type', sa.String(100)),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Add columns to proposals if not exist
    try:
        op.add_column('proposals', sa.Column('pre_send_score', sa.Integer()))
        op.add_column('proposals', sa.Column('win_probability', sa.Float()))
        op.add_column('proposals', sa.Column('engagement_score', sa.Integer(), default=0))
        op.add_column('proposals', sa.Column('times_opened', sa.Integer(), default=0))
        op.add_column('proposals', sa.Column('last_opened_at', sa.DateTime(timezone=True)))
        op.add_column('proposals', sa.Column('tracking_token', sa.String(64)))
    except Exception:
        pass

    # Add score history to leads
    try:
        op.add_column('leads', sa.Column('score_reason', JSONB))
        op.add_column('leads', sa.Column('signal_breakdown', JSONB))
    except Exception:
        pass


def downgrade():
    for t in ['ai_routing_performance', 'client_health_scores', 'self_assessments',
              'onboarding_checkpoints', 'autonomous_decisions', 'revenue_forecasts',
              'operating_beliefs', 'lead_score_history', 'prospect_psychology']:
        op.drop_table(t)
```

---

## STEP 2 — PROSPECT PSYCHOLOGY ENGINE

Create: `app/services/intelligence/prospect_psychology.py`

```python
"""Scrape prospect signals before Email 1 fires."""
import logging
import re
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Keywords that indicate pain/urgency
PAIN_KEYWORDS = [
    "inefficient", "manual process", "time-consuming", "struggling", "bottleneck",
    "reduce costs", "automate", "scale", "overwhelmed", "behind schedule",
    "outdated", "legacy", "technical debt", "slow growth", "losing customers",
    "hiring challenges", "understaffed", "disconnected systems", "siloed",
]

BUYING_SIGNALS = [
    "looking for", "seeking", "need help with", "interested in",
    "evaluating", "considering", "solution for", "replacing",
]


async def build_prospect_psychology(db: AsyncSession, contact_id: int,
                                     company_name: str, contact_email: str,
                                     industry: str = "") -> dict:
    """Analyze prospect and extract pain indicators. Called before Email 1."""
    pain_indicators = []
    confidence = 0.3  # base confidence

    # Signal 1: Email domain analysis
    domain = contact_email.split("@")[-1] if "@" in contact_email else ""
    if domain and domain not in ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]:
        pain_indicators.append({
            "type": "business_email",
            "signal": f"Professional domain: {domain}",
            "weight": 0.1
        })
        confidence += 0.1

    # Signal 2: Industry-specific pain points
    industry_pains = {
        "hotel": "operational costs, guest experience, staff scheduling",
        "saas": "user churn, scaling infrastructure, automation gaps",
        "ecommerce": "order management, inventory, customer service load",
        "healthcare": "compliance, patient data, manual paperwork",
        "real_estate": "lead follow-up, property management, CRM gaps",
        "finance": "compliance, reporting automation, data accuracy",
        "logistics": "route optimization, tracking, communication gaps",
    }
    for key, pain in industry_pains.items():
        if key in (industry or "").lower():
            pain_indicators.append({
                "type": "industry_pain",
                "signal": pain,
                "weight": 0.3
            })
            confidence += 0.2
            break

    # Signal 3: Company name signals
    company_lower = company_name.lower()
    growth_signals = ["solutions", "tech", "digital", "cloud", "systems", "services", "group", "global"]
    for sig in growth_signals:
        if sig in company_lower:
            pain_indicators.append({
                "type": "company_type",
                "signal": f"Company type suggests: growth-stage technology buyer",
                "weight": 0.1
            })
            confidence += 0.05
            break

    # Store psychology profile
    primary_pain = pain_indicators[0]["signal"] if pain_indicators else f"Operational efficiency in {industry or 'your sector'}"

    await db.execute(text("""
        INSERT INTO prospect_psychology
            (contact_id, pain_indicators, primary_pain, confidence_score, scraped_at)
        VALUES (:cid, :pain::jsonb, :primary, :conf, :now)
        ON CONFLICT DO NOTHING
    """), {
        "cid": contact_id,
        "pain": str(pain_indicators).replace("'", '"'),
        "primary": primary_pain,
        "conf": min(confidence, 0.95),
        "now": datetime.now(timezone.utc)
    })

    return {
        "pain_indicators": pain_indicators,
        "primary_pain": primary_pain,
        "confidence": confidence
    }


async def inject_pain_into_email(email_body: str, contact_id: int, db: AsyncSession) -> str:
    """Personalize email body with prospect's primary pain signal."""
    row = (await db.execute(text(
        "SELECT primary_pain, confidence_score FROM prospect_psychology WHERE contact_id=:id ORDER BY scraped_at DESC LIMIT 1"
    ), {"id": contact_id})).fetchone()

    if row and row[1] > 0.4:  # Only inject if confident enough
        pain = row[0]
        # Replace generic industry placeholder if present
        email_body = email_body.replace(
            "{industry}", f"companies dealing with {pain}"
        )
    return email_body
```

---

## STEP 3 — UPGRADED LEAD SCORING (6 SIGNALS)

Update your lead scoring function:

```python
"""6-signal lead scoring — 0 to 100 with reason codes."""

SIGNAL_WEIGHTS = {
    "industry_fit":      25,  # Matches ICP
    "company_size":      20,  # 10-200 employees = max
    "tech_stack":        15,  # SaaS/cloud tools
    "engagement":        15,  # Replied/opened recently
    "behavioral_intent": 15,  # Pricing page, demo request
    "contact_quality":   10,  # Decision maker, valid email
}


def score_lead_v2(lead: dict) -> tuple[int, dict]:
    """Returns (total_score, signal_breakdown)."""
    signals = {}
    total = 0

    # 1. Industry fit
    icp_industries = ["saas", "technology", "cloud", "fintech", "ecommerce", 
                       "logistics", "healthcare", "hotel", "hospitality", "real estate"]
    industry = (lead.get("industry") or "").lower()
    fit = sum(1 for i in icp_industries if i in industry)
    signals["industry_fit"] = {"score": min(fit * 12, 25), "reason": f"Industry: {industry}"}
    total += signals["industry_fit"]["score"]

    # 2. Company size
    size = lead.get("company_size") or lead.get("employee_count") or 0
    if isinstance(size, str):
        size_map = {"1-10": 5, "11-50": 15, "51-200": 20, "201-500": 15, "500+": 8, "1000+": 5}
        size_score = size_map.get(size, 10)
    elif 10 <= size <= 200:
        size_score = 20
    elif 5 <= size < 10:
        size_score = 12
    elif 200 < size <= 500:
        size_score = 14
    else:
        size_score = 6
    signals["company_size"] = {"score": size_score, "reason": f"Size: {size}"}
    total += size_score

    # 3. Tech stack signals
    tech = (lead.get("technologies") or lead.get("tech_stack") or "").lower()
    cloud_tools = ["aws", "azure", "gcp", "hubspot", "salesforce", "zapier", 
                    "slack", "notion", "stripe", "shopify", "intercom"]
    tech_score = min(sum(1 for t in cloud_tools if t in tech) * 3, 15)
    signals["tech_stack"] = {"score": tech_score, "reason": f"Tech signals: {tech[:50]}"}
    total += tech_score

    # 4. Engagement recency
    last_interaction = lead.get("last_interaction_days") or 999
    if last_interaction < 7:
        eng_score = 15
    elif last_interaction < 30:
        eng_score = 10
    elif last_interaction < 90:
        eng_score = 5
    else:
        eng_score = 0
    signals["engagement"] = {"score": eng_score, "reason": f"Last contact: {last_interaction}d ago"}
    total += eng_score

    # 5. Behavioral intent
    intent_score = 0
    if lead.get("requested_demo"):
        intent_score += 15
    elif lead.get("visited_pricing"):
        intent_score += 10
    elif lead.get("replied_to_email"):
        intent_score += 8
    elif lead.get("opened_email"):
        intent_score += 4
    signals["behavioral_intent"] = {"score": intent_score, "reason": "Behavioral signals"}
    total += intent_score

    # 6. Contact quality
    cq_score = 0
    if lead.get("email") and "@" in (lead.get("email") or ""):
        cq_score += 4
    title = (lead.get("title") or lead.get("job_title") or "").lower()
    decision_titles = ["ceo", "cto", "coo", "founder", "owner", "director", "vp", "head of", "manager"]
    if any(t in title for t in decision_titles):
        cq_score += 6
    signals["contact_quality"] = {"score": cq_score, "reason": f"Title: {title[:50]}"}
    total += cq_score

    return min(total, 100), signals
```

Replace old scoring logic with this. Store `signal_breakdown` in leads table.

---

## STEP 4 — MEMORY SYNTHESIS ENGINE

Create: `app/services/memory/synthesis.py`

```python
"""Weekly synthesis: operational memories → operating beliefs."""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def run_weekly_synthesis(db: AsyncSession):
    """Run Sunday 03:00 UTC. Synthesize past week's memories into beliefs."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    # Pull recent high-value memories
    memories = (await db.execute(text("""
        SELECT content, category, importance_score
        FROM memory_records
        WHERE created_at > :cutoff
        AND importance_score > 0.5
        ORDER BY importance_score DESC
        LIMIT 100
    """), {"cutoff": cutoff})).fetchall()

    if not memories:
        logger.info("Memory synthesis: no memories to process")
        return []

    # Group by category
    by_category = {}
    for mem in memories:
        cat = mem[1] or "general"
        by_category.setdefault(cat, []).append(mem[0])

    beliefs = []
    for category, mem_list in by_category.items():
        # Simple synthesis: extract key patterns (AI synthesis if provider available)
        belief_text = await _synthesize_beliefs(mem_list, category)
        if belief_text:
            await db.execute(text("""
                INSERT INTO operating_beliefs
                    (belief_text, category, confidence, source_memory_count)
                VALUES (:text, :cat, :conf, :count)
            """), {
                "text": belief_text,
                "cat": category,
                "conf": min(0.5 + len(mem_list) * 0.05, 0.95),
                "count": len(mem_list)
            })
            beliefs.append({"category": category, "belief": belief_text, "sources": len(mem_list)})

    await db.commit()
    logger.info(f"Memory synthesis complete: {len(beliefs)} beliefs generated")
    return beliefs


async def _synthesize_beliefs(memories: list, category: str) -> str:
    """Use AI to synthesize memories into a single actionable belief."""
    if not memories:
        return ""

    # Try AI synthesis
    try:
        from app.services.ai_router import get_ai_response
        combined = "\n".join(memories[:20])
        prompt = (
            f"Based on these {category} observations from the past week:\n\n{combined}\n\n"
            f"Write ONE concise operating belief (max 30 words) that JARVIS should apply going forward. "
            f"Start with 'When...' or 'Always...' or 'Prospects who...'"
        )
        response = await get_ai_response(prompt, task_type="fast")
        return response.strip()[:300]
    except Exception as e:
        logger.warning(f"AI synthesis failed, using heuristic: {e}")
        # Fallback: return most common theme
        return f"Pattern observed in {len(memories)} {category} events — review recommended"
```

Register as job (Sunday 03:00 UTC).

---

## STEP 5 — REVENUE FORECASTING ENGINE

Create: `app/services/intelligence/revenue_forecaster.py`

```python
"""Monte Carlo revenue forecasting — P10/P50/P90 scenarios."""
import random
import logging
from datetime import datetime, timezone, date, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def run_revenue_forecast(db: AsyncSession, horizon_days: int = 90) -> dict:
    """Monte Carlo simulation: 1000 runs, 90-day horizon."""

    # Get current pipeline data
    deals = (await db.execute(text("""
        SELECT value, status, created_at, last_activity_at
        FROM proposals
        WHERE status IN ('sent', 'viewed', 'negotiating', 'demo_scheduled')
        AND value > 0
        ORDER BY value DESC
    """))).fetchall()

    # Historical close rate (from won/lost proposals)
    stats = (await db.execute(text("""
        SELECT 
            COUNT(*) FILTER (WHERE status='accepted') as won,
            COUNT(*) FILTER (WHERE status IN ('accepted','rejected','archived')) as total,
            AVG(value) FILTER (WHERE status='accepted') as avg_deal
        FROM proposals
        WHERE created_at > NOW() - INTERVAL '180 days'
    """))).fetchone()

    won_count = stats[0] or 0
    total_count = stats[1] or 1
    avg_deal = float(stats[2] or 5000)
    historical_close_rate = won_count / total_count if total_count > 0 else 0.15

    # Stage-based close probabilities
    stage_probs = {
        "sent": max(historical_close_rate * 0.5, 0.05),
        "viewed": max(historical_close_rate * 0.7, 0.08),
        "negotiating": max(historical_close_rate * 1.2, 0.25),
        "demo_scheduled": max(historical_close_rate * 1.5, 0.35),
    }

    pipeline_value = sum(float(d[0] or 0) for d in deals)
    N_SIMULATIONS = 1000
    results = []

    for _ in range(N_SIMULATIONS):
        sim_revenue = 0
        for deal in deals:
            value = float(deal[0] or 0)
            status = deal[1]
            close_prob = stage_probs.get(status, historical_close_rate)
            # Add noise: ±20%
            noisy_prob = max(0.01, min(0.99, close_prob + random.gauss(0, 0.05)))
            if random.random() < noisy_prob:
                # Deal closes — value may vary ±15%
                sim_revenue += value * (1 + random.gauss(0, 0.075))
        results.append(sim_revenue)

    results.sort()
    p10 = results[int(N_SIMULATIONS * 0.10)]
    p50 = results[int(N_SIMULATIONS * 0.50)]
    p90 = results[int(N_SIMULATIONS * 0.90)]

    # Leakage detection: deals stuck > 14 days in same stage
    leakage = []
    for deal in deals:
        last_activity = deal[3]
        if last_activity:
            days_stagnant = (datetime.now(timezone.utc) - last_activity).days
            if days_stagnant > 14:
                leakage.append({
                    "value": float(deal[0] or 0),
                    "status": deal[1],
                    "days_stagnant": days_stagnant
                })

    forecast = {
        "forecast_date": date.today().isoformat(),
        "horizon_days": horizon_days,
        "p10": round(p10, 2),
        "p50": round(p50, 2),
        "p90": round(p90, 2),
        "pipeline_value": round(pipeline_value, 2),
        "active_deals": len(deals),
        "historical_close_rate": round(historical_close_rate * 100, 1),
        "leakage_deals": leakage,
        "leakage_at_risk": round(sum(d["value"] for d in leakage), 2),
    }

    # Store snapshot
    await db.execute(text("""
        INSERT INTO revenue_forecasts
            (forecast_date, horizon_days, p10_revenue, p50_revenue, p90_revenue,
             simulation_runs, pipeline_value, active_deals, leakage_deals, assumptions)
        VALUES (:fd, :hd, :p10, :p50, :p90, 1000, :pv, :ad, :ld::jsonb, :ass::jsonb)
    """), {
        "fd": date.today(), "hd": horizon_days,
        "p10": p10, "p50": p50, "p90": p90,
        "pv": pipeline_value, "ad": len(deals),
        "ld": str(leakage).replace("'", '"'),
        "ass": f'{{"close_rate": {historical_close_rate}, "avg_deal": {avg_deal}}}'
    })
    await db.commit()

    if leakage:
        try:
            from app.services.notifications import send_telegram
            msg = (f"📊 *Revenue Forecast Update*\n\n"
                   f"P50 (Expected): £{p50:,.0f}\n"
                   f"P10 (Pessimistic): £{p10:,.0f}\n"
                   f"P90 (Optimistic): £{p90:,.0f}\n"
                   f"⚠️ {len(leakage)} deals stagnant (£{sum(d['value'] for d in leakage):,.0f} at risk)")
            await send_telegram(msg)
        except Exception:
            pass

    return forecast
```

Add API endpoint:
```python
@app.get("/api/v1/intelligence/revenue-forecast")
async def revenue_forecast(horizon: int = 90, db=Depends(get_db)):
    from app.services.intelligence.revenue_forecaster import run_revenue_forecast
    return await run_revenue_forecast(db, horizon)
```

Register as job (Sunday 20:00 UTC, alongside pipeline health check).

---

## STEP 6 — AUTONOMOUS GOVERNANCE ENGINE

Create: `app/services/governance/autonomous_engine.py`

```python
"""Tier-based decision framework: auto / propose / captain-only."""
import logging
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Tier 1: JARVIS decides autonomously
TIER_1_ACTIONS = {
    "outreach_scheduling", "lead_scoring", "sequence_selection",
    "report_generation", "job_execution", "sequence_pause",
    "contact_categorization", "backup_execution", "health_check",
}

# Tier 2: JARVIS proposes → Captain approves
TIER_2_ACTIONS = {
    "new_client_onboarding", "proposal_send", "service_catalog_change",
    "new_outreach_campaign", "price_change", "contract_send",
}

# Tier 3: Captain must initiate
TIER_3_ACTIONS = {
    "payment_processing", "contract_signature", "public_announcement",
    "infrastructure_change", "team_change", "legal_action",
}


def get_decision_tier(action_type: str) -> int:
    action_type = action_type.lower()
    if action_type in TIER_1_ACTIONS:
        return 1
    if action_type in TIER_2_ACTIONS:
        return 2
    if action_type in TIER_3_ACTIONS:
        return 3
    return 2  # Default to propose


async def log_autonomous_decision(db: AsyncSession, decision_type: str,
                                   description: str, rationale: str,
                                   outcome: str = "executed"):
    """Log a Tier 1 autonomous decision."""
    tier = get_decision_tier(decision_type)
    await db.execute(text("""
        INSERT INTO autonomous_decisions
            (decision_type, tier, description, rationale, outcome, decided_at)
        VALUES (:dt, :t, :desc, :rat, :out, :now)
    """), {
        "dt": decision_type, "t": tier,
        "desc": description, "rat": rationale,
        "out": outcome, "now": datetime.now(timezone.utc)
    })


async def propose_to_captain(db: AsyncSession, action_type: str,
                              title: str, description: str,
                              metadata: dict = None) -> int:
    """Create Tier 2 proposal in Captain's approval queue."""
    result = await db.execute(text("""
        INSERT INTO jarvis_captain_queue
            (item_type, priority, title, description, status, metadata)
        VALUES (:type, 'high', :title, :desc, 'pending', :meta::jsonb)
        RETURNING id
    """), {
        "type": action_type,
        "title": title,
        "desc": description,
        "meta": str(metadata or {}).replace("'", '"')
    })
    queue_id = result.scalar()
    logger.info(f"Tier 2 proposal created: {title} (queue_id={queue_id})")
    return queue_id


async def weekly_governance_audit(db: AsyncSession) -> dict:
    """Weekly: report all autonomous decisions to Captain."""
    from datetime import timedelta
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    decisions = (await db.execute(text("""
        SELECT decision_type, tier, COUNT(*), 
               COUNT(*) FILTER (WHERE captain_override=true)
        FROM autonomous_decisions
        WHERE decided_at > :cutoff
        GROUP BY decision_type, tier
        ORDER BY tier, COUNT(*) DESC
    """), {"cutoff": week_ago})).fetchall()

    summary = {
        "tier1_count": sum(d[2] for d in decisions if d[1] == 1),
        "tier2_count": sum(d[2] for d in decisions if d[1] == 2),
        "override_count": sum(d[3] for d in decisions),
        "by_type": [{"type": d[0], "tier": d[1], "count": d[2], "overrides": d[3]}
                    for d in decisions]
    }
    return summary
```

---

## STEP 7 — CLIENT ONBOARDING ORCHESTRATION

Create: `app/services/clients/onboarding.py`

```python
"""Zero-touch client onboarding triggered when proposal is accepted."""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def trigger_onboarding(db: AsyncSession, proposal_id: int):
    """Called when proposal.status changes to 'accepted'."""
    proposal = (await db.execute(text(
        "SELECT id, client_name, client_email, value, service_type FROM proposals WHERE id=:id"
    ), {"id": proposal_id})).fetchone()

    if not proposal:
        return

    client_name = proposal[1]
    client_email = proposal[2]
    now = datetime.now(timezone.utc)
    sla_deadline = now + timedelta(hours=72)  # Onboard within 72 hours

    # Create onboarding checkpoint record
    result = await db.execute(text("""
        INSERT INTO onboarding_checkpoints
            (proposal_id, sla_deadline, created_at)
        VALUES (:pid, :sla, :now)
        RETURNING id
    """), {"pid": proposal_id, "sla": sla_deadline, "now": now})
    checkpoint_id = result.scalar()

    # Create onboarding task sequence
    tasks = [
        ("Send contract", "Send service agreement to client for signature", 0),
        ("Confirm payment", "Verify 50% upfront payment received", 2),
        ("Grant access", "Provide client portal / system access", 4),
        ("Schedule kickoff", "Book 45-min kickoff call with Olivia Bennett", 8),
        ("First deliverable", "Schedule first project deliverable", 24),
    ]

    for title, desc, hours_offset in tasks:
        await db.execute(text("""
            INSERT INTO jarvis_tasks
                (title, description, task_type, priority, status, 
                 scheduled_at, assigned_to, metadata)
            VALUES (:t, :d, 'onboarding', 'high', 'pending',
                    :at, 'Olivia Bennett', :meta::jsonb)
        """), {
            "t": f"[{client_name}] {title}",
            "d": desc,
            "at": now + timedelta(hours=hours_offset),
            "meta": f'{{"checkpoint_id": {checkpoint_id}, "client_email": "{client_email}"}}'
        })

    await db.commit()

    # Telegram notification
    try:
        from app.services.notifications import send_telegram
        await send_telegram(
            f"🎉 *New Client Won!*\n\n"
            f"Client: {client_name}\n"
            f"Value: £{proposal[3]:,.0f}\n"
            f"SLA: Onboard by {sla_deadline.strftime('%d %b %Y %H:%M UTC')}\n"
            f"Tasks created. Olivia Bennett assigned."
        )
    except Exception:
        pass

    logger.info(f"Onboarding triggered for proposal {proposal_id}: {client_name}")
    return checkpoint_id
```

Hook into proposal update: when `status` changes to `accepted`, call `trigger_onboarding(db, proposal_id)`.

---

## STEP 8 — OPERATIONAL SELF-ASSESSMENT ENGINE

Create: `app/services/intelligence/self_assessment.py`

```python
"""Weekly JARVIS self-assessment — grades own performance."""
import logging
from datetime import datetime, timezone, timedelta, date
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

GRADE_THRESHOLDS = {
    "A": 90, "B": 75, "C": 60, "D": 45, "F": 0
}


def _score_to_grade(score: float) -> str:
    for grade, threshold in GRADE_THRESHOLDS.items():
        if score >= threshold:
            return grade
    return "F"


async def run_self_assessment(db: AsyncSession) -> dict:
    """Run Sunday 22:00 UTC."""
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    # Jobs performance
    jobs_result = (await db.execute(text("""
        SELECT 
            COUNT(*) FILTER (WHERE resolved=false) as failed,
            COUNT(*) as total
        FROM dead_letter_jobs WHERE failed_at > :cutoff
    """), {"cutoff": week_ago})).fetchone()
    failed_jobs = jobs_result[0] or 0
    total_jobs = max(jobs_result[1] or 0, 10)
    jobs_score = max(0, 100 - (failed_jobs / total_jobs) * 100)

    # Lead quality
    lead_result = (await db.execute(text("""
        SELECT AVG(score), COUNT(*) FROM leads WHERE created_at > :cutoff
    """), {"cutoff": week_ago})).fetchone()
    avg_lead_score = float(lead_result[0] or 50)
    lead_quality_score = avg_lead_score

    # Outreach performance
    outreach_result = (await db.execute(text("""
        SELECT 
            COUNT(*) FILTER (WHERE status='sent') as sent,
            COUNT(*) FILTER (WHERE status='replied') as replied
        FROM outreach_log WHERE created_at > :cutoff
    """), {"cutoff": week_ago})).fetchone()
    sent = outreach_result[0] or 0
    replied = outreach_result[1] or 0
    reply_rate = (replied / max(sent, 1)) * 100
    outreach_score = min(reply_rate * 10, 100)  # 10% reply rate = 100 score

    # Proposal conversion
    prop_result = (await db.execute(text("""
        SELECT 
            COUNT(*) FILTER (WHERE status='accepted') as won,
            COUNT(*) FILTER (WHERE status IN ('sent','viewed','accepted','rejected')) as total
        FROM proposals WHERE created_at > :cutoff
    """), {"cutoff": week_ago})).fetchone()
    won = prop_result[0] or 0
    prop_total = prop_result[1] or 1
    prop_score = (won / prop_total) * 100 if prop_total > 0 else 50

    overall = (jobs_score * 0.3 + lead_quality_score * 0.2 +
               outreach_score * 0.25 + prop_score * 0.25)

    improvements = []
    if jobs_score < 80:
        improvements.append(f"Fix {failed_jobs} failed jobs in dead letter queue")
    if outreach_score < 50:
        improvements.append("Outreach reply rate below target — review sequences and targeting")
    if avg_lead_score < 55:
        improvements.append("Lead quality low — tighten ICP filter or improve source quality")
    if prop_score < 30:
        improvements.append("Proposal conversion low — review pricing and value proposition")

    assessment = {
        "date": date.today().isoformat(),
        "jobs_grade": _score_to_grade(jobs_score),
        "lead_quality_grade": _score_to_grade(lead_quality_score),
        "outreach_grade": _score_to_grade(outreach_score),
        "proposal_grade": _score_to_grade(prop_score),
        "overall_grade": _score_to_grade(overall),
        "improvements": improvements[:3],
        "scores": {
            "jobs": round(jobs_score, 1),
            "lead_quality": round(lead_quality_score, 1),
            "outreach": round(outreach_score, 1),
            "proposals": round(prop_score, 1),
            "overall": round(overall, 1),
        }
    }

    await db.execute(text("""
        INSERT INTO self_assessments
            (assessment_date, jobs_grade, lead_quality_grade, outreach_grade,
             proposal_grade, overall_grade, top_improvements, metrics_snapshot)
        VALUES (:d, :j, :lq, :o, :p, :ov, :imp::jsonb, :snap::jsonb)
    """), {
        "d": date.today(),
        "j": assessment["jobs_grade"],
        "lq": assessment["lead_quality_grade"],
        "o": assessment["outreach_grade"],
        "p": assessment["proposal_grade"],
        "ov": assessment["overall_grade"],
        "imp": str(improvements).replace("'", '"'),
        "snap": str(assessment["scores"]).replace("'", '"')
    })
    await db.commit()

    logger.info(f"Self-assessment complete: Overall {assessment['overall_grade']} ({overall:.1f})")
    return assessment
```

Register as job (Sunday 22:00 UTC).

---

## STEP 9 — CLIENT HEALTH SCORING

Create: `app/services/clients/health_monitor.py`

```python
"""Daily client health scoring and churn prediction."""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def score_all_clients(db: AsyncSession):
    """Run daily at 09:00 UTC. Score all active clients."""
    clients = (await db.execute(text("""
        SELECT id, name, email, created_at FROM clients WHERE status='active'
    """))).fetchall()

    alerts = []
    for client in clients:
        client_id = client[0]
        score, breakdown = await _score_client(db, client_id)

        status = "healthy" if score >= 75 else ("watch" if score >= 50 else "at_risk")

        await db.execute(text("""
            INSERT INTO client_health_scores
                (client_id, score, status, signal_breakdown, scored_at)
            VALUES (:cid, :s, :st, :bd::jsonb, NOW())
        """), {
            "cid": client_id, "s": score, "st": status,
            "bd": str(breakdown).replace("'", '"')
        })

        if status == "at_risk":
            alerts.append({"client_id": client_id, "name": client[1], "score": score})
            # Create task for Olivia Bennett
            await db.execute(text("""
                INSERT INTO jarvis_tasks (title, description, task_type, priority, status, scheduled_at)
                VALUES (:t, :d, 'client_retention', 'high', 'pending', NOW() + INTERVAL '4 hours')
            """), {
                "t": f"[AT RISK] Check in with {client[1]}",
                "d": f"Client health score: {score}/100. Schedule check-in call within 48h."
            })

    await db.commit()

    if alerts:
        try:
            from app.services.notifications import send_telegram
            msg = f"⚠️ *Client Health Alert*\n\n{len(alerts)} clients at risk:\n"
            for a in alerts:
                msg += f"• {a['name']}: {a['score']}/100\n"
            await send_telegram(msg)
        except Exception:
            pass

    return {"scored": len(clients), "at_risk": len(alerts)}


async def _score_client(db: AsyncSession, client_id: int) -> tuple[int, dict]:
    """Score a single client 0-100."""
    breakdown = {}
    score = 60  # Base score

    # Payment history (+/-)
    payments = (await db.execute(text("""
        SELECT COUNT(*) FILTER (WHERE status='paid') as paid,
               COUNT(*) as total
        FROM invoices WHERE client_id=:id AND created_at > NOW() - INTERVAL '90 days'
    """), {"id": client_id})).fetchone()
    if payments[1] > 0:
        payment_rate = payments[0] / payments[1]
        payment_score = (payment_rate - 0.5) * 40
        score += payment_score
        breakdown["payments"] = round(payment_score, 1)

    # Last contact recency (+/-)
    last_contact = (await db.execute(text("""
        SELECT MAX(created_at) FROM jarvis_tasks
        WHERE metadata::text LIKE '%' || :id::text || '%'
        AND task_type IN ('client_meeting', 'client_call', 'client_email')
    """), {"id": client_id})).scalar_one_or_none()

    if last_contact:
        days_since = (datetime.now(timezone.utc) - last_contact).days
        if days_since < 14:
            score += 10
        elif days_since > 45:
            score -= 15
        breakdown["last_contact_days"] = days_since

    return max(0, min(100, int(score))), breakdown


async def get_client_health(db: AsyncSession, client_id: int) -> dict:
    row = (await db.execute(text("""
        SELECT score, status, signal_breakdown, scored_at
        FROM client_health_scores
        WHERE client_id=:id ORDER BY scored_at DESC LIMIT 1
    """), {"id": client_id})).fetchone()
    if not row:
        return {"error": "No health score available"}
    return {"score": row[0], "status": row[1], "breakdown": row[2], "as_of": str(row[3])}
```

Add endpoint:
```python
@app.get("/api/v1/clients/{client_id}/health")
async def client_health(client_id: int, db=Depends(get_db)):
    from app.services.clients.health_monitor import get_client_health
    return await get_client_health(db, client_id)
```

Register scoring as daily job (09:00 UTC).

---

## STEP 10 — DYNAMIC PRICING ENGINE

Create: `app/services/intelligence/pricing_engine.py`

```python
"""Market-aware pricing recommendations."""
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Base pricing matrix (£/month)
BASE_PRICING = {
    "ai_automation": {"min": 2500, "max": 8000, "anchor": 5000},
    "cloud_devops": {"min": 3000, "max": 12000, "anchor": 6000},
    "saas_platform": {"min": 5000, "max": 25000, "anchor": 10000},
    "crm_automation": {"min": 2000, "max": 6000, "anchor": 3500},
    "outreach_system": {"min": 1500, "max": 5000, "anchor": 2500},
    "security": {"min": 2000, "max": 8000, "anchor": 4000},
    "content_media": {"min": 1500, "max": 5000, "anchor": 2500},
    "default": {"min": 2000, "max": 8000, "anchor": 4000},
}

SIZE_MULTIPLIERS = {
    "1-10": 0.7, "11-50": 1.0, "51-200": 1.3,
    "201-500": 1.6, "500+": 2.0,
}


async def get_pricing_recommendation(
    db: AsyncSession,
    service_type: str,
    company_size: str = "11-50",
    urgency: str = "normal"
) -> dict:
    """Recommend optimal price range for a proposal."""
    base = BASE_PRICING.get(service_type.lower().replace(" ", "_"),
                             BASE_PRICING["default"])
    size_mult = SIZE_MULTIPLIERS.get(company_size, 1.0)
    urgency_mult = 1.15 if urgency == "high" else 1.0

    recommended = base["anchor"] * size_mult * urgency_mult

    # Adjust based on historical win rate at different price points
    win_data = (await db.execute(text("""
        SELECT value, status
        FROM proposals
        WHERE service_type ILIKE :stype
        AND status IN ('accepted', 'rejected')
        AND created_at > NOW() - INTERVAL '180 days'
        ORDER BY value
    """), {"stype": f"%{service_type}%"})).fetchall()

    sweet_spot = None
    if len(win_data) >= 5:
        won_values = [float(w[0]) for w in win_data if w[1] == 'accepted' and w[0]]
        if won_values:
            sweet_spot = sum(won_values) / len(won_values)
            # Blend with market-based anchor
            recommended = (recommended * 0.4 + sweet_spot * 0.6)

    return {
        "service_type": service_type,
        "company_size": company_size,
        "recommended_monthly": round(recommended, -2),  # Round to nearest 100
        "range_min": round(base["min"] * size_mult, -2),
        "range_max": round(base["max"] * size_mult, -2),
        "anchor_price": round(base["anchor"] * size_mult, -2),
        "historical_sweet_spot": round(sweet_spot, -2) if sweet_spot else None,
        "confidence": "high" if sweet_spot else "medium",
        "note": "Based on ICP win data" if sweet_spot else "Based on market positioning"
    }
```

Add endpoint:
```python
@app.get("/api/v1/intelligence/pricing-recommendation")
async def pricing_recommendation(service: str, company_size: str = "11-50",
                                  urgency: str = "normal", db=Depends(get_db)):
    from app.services.intelligence.pricing_engine import get_pricing_recommendation
    return await get_pricing_recommendation(db, service, company_size, urgency)
```

---

## STEP 11 — ADAPTIVE AI MODEL ROUTER

In your AI router, add performance tracking:

```python
async def track_routing_performance(db: AsyncSession, provider: str, task_type: str,
                                     latency_ms: float, quality_score: float,
                                     cost_usd: float, success: bool, error_type: str = None):
    await db.execute(text("""
        INSERT INTO ai_routing_performance
            (provider, task_type, latency_ms, quality_score, cost_usd, success, error_type)
        VALUES (:prov, :tt, :lat, :q, :c, :s, :e)
    """), {
        "prov": provider, "tt": task_type,
        "lat": latency_ms, "q": quality_score,
        "c": cost_usd, "s": success, "e": error_type
    })


async def get_optimal_provider(db: AsyncSession, task_type: str) -> str:
    """Returns the best-performing provider for this task type based on recent data."""
    rows = (await db.execute(text("""
        SELECT provider,
               AVG(quality_score) as avg_quality,
               AVG(latency_ms) as avg_latency,
               COUNT(*) FILTER (WHERE success=true)::float / NULLIF(COUNT(*), 0) as success_rate
        FROM ai_routing_performance
        WHERE task_type = :tt
        AND recorded_at > NOW() - INTERVAL '30 days'
        GROUP BY provider
        HAVING COUNT(*) >= 5
        ORDER BY (AVG(quality_score) * 0.5 + 
                  (1 - COUNT(*) FILTER (WHERE success=false)::float / NULLIF(COUNT(*), 0)) * 0.3 +
                  (1 / NULLIF(AVG(latency_ms), 0)) * 1000 * 0.2) DESC
        LIMIT 1
    """), {"tt": task_type})).fetchone()

    if rows:
        return rows[0]
    return None  # Fall back to default routing
```

Wrap every AI call with timing + track_routing_performance.

---

## STEP 12 — DEPLOY AND VERIFY

```bash
cd /home/ubuntu/jarvis_sales_pipeline

# Run migration
docker-compose exec jarvis_app alembic upgrade head

# Rebuild
docker-compose up -d --build jarvis_app
sleep 15

# Verify
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/v1/intelligence/revenue-forecast | python3 -m json.tool
curl -s "http://localhost:8000/api/v1/intelligence/pricing-recommendation?service=ai_automation" | python3 -m json.tool

# Verify new tables
docker-compose exec jarvis_postgres psql -U jarvis -d jarvis -c "\dt" | grep -E "prospect_psychology|revenue_forecasts|operating_beliefs|self_assessments|client_health"

# Commit
git add -A
git commit -m "feat(batch2): intelligence engines — scoring, forecasting, synthesis, health"
git push origin main
```

---

## VERIFICATION CHECKLIST

- [ ] Migration 0010 applied — all 9 new tables exist
- [ ] `/api/v1/intelligence/revenue-forecast` returns P10/P50/P90
- [ ] `/api/v1/intelligence/pricing-recommendation?service=ai_automation` returns pricing
- [ ] `/api/v1/clients/{id}/health` returns health score
- [ ] Lead scoring v2 (6 signals) active
- [ ] Self-assessment job registered (Sunday 22:00)
- [ ] Memory synthesis job registered (Sunday 03:00)
- [ ] Revenue forecast job registered (Sunday 20:00)
- [ ] Client health scoring job registered (daily 09:00)
- [ ] Onboarding triggers when proposal status → accepted

**Batch 2 complete. Proceed to Batch 3.**
