# JARVIS COMPLETE SYSTEM — PERMANENT DEPLOYMENT MASTER PROMPT
## For: All EC2 Instances | Aliyar Solutions | CEO: Syed Abrar

You are JARVIS Codex. This is the ONE complete, permanent prompt for the entire JARVIS system.
Execute every step in strict order. Do NOT stop. Do NOT ask questions.
Do NOT patch — every fix in this prompt is the permanent, correct implementation.
If a step fails, diagnose and fix the root cause. Never skip.
When done, every system is permanently operational. No further patching needed.

---

## WHAT YOU ARE DEPLOYING

The complete JARVIS autonomous business operating system for Aliyar Solutions:

| System | Description |
|---|---|
| **Phase 6 — 6-Layer AI Council** | 15 Department Intelligence Officers, Council Intelligence Loop, Tech Evolution Scanner, Call Intelligence, Strategy Oversight |
| **Batch 2 — Intelligence Engines** | Prospect Psychology, Monte Carlo Revenue Forecaster, Self-Assessment, Client Health Scorer, Dynamic Pricing, Memory Synthesis, Autonomous Governance |
| **Batch 3 — Captain Bridge** | Lead Intake, Brain Dump Parser, Email Thread Intelligence, Predictive Actions, Pushback Engine, Voice Commands |
| **Batch 4 — Frontier Systems** | Expert Council (5 agents), Red Team Engine, Conscience Layer, Flywheel Engine, Cialdini Persuasion, Relationship Graph |
| **9-Connector Daily Pipeline** | Apollo → HubSpot → Close CRM → Klaviyo → Gamma → Zoho Books → Notion → Google Calendar → Slack. Claude pushes daily data to GitHub. JARVIS pulls and processes automatically. |
| **Daily Lead Machine** | 20 leads/day from Claude's 9 connectors + 28 leads/day from JARVIS's internal discovery engine = **48 total leads processed daily** |
| **Email Safety Cap** | Hard limit of **48 outreach emails/day** — Google-safe, never banned |
| **Full Frontend** | 25 React views including Captain Bridge, War Room, Revenue Intelligence, Departments, Intelligence Hub, Relationships, System HUD |

---

## SYSTEM IDENTITY

```
GitHub repo:       syedabrarfff-stack/devops-docker-project
Branch:            claude/jarvis-cans-api-integration-ZThTD
EC2 working dir:   /opt/jarvis/
Backend path:      /opt/jarvis/backend/app/
Docker command:    docker compose up -d --build
Tenant UUID:       aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa
```

---

## STEP 1 — PULL COMPLETE CODEBASE FROM GITHUB

```bash
cd /opt/jarvis
git fetch origin
git pull origin claude/jarvis-cans-api-integration-ZThTD --rebase
```

If conflicts:
```bash
git rebase --abort
git stash
git pull origin claude/jarvis-cans-api-integration-ZThTD
git stash pop
```

Verify the latest commits are present:
```bash
git log --oneline -8
```

You must see commits including:
- `feat(limits): hard cap 48 outreach emails/day + 20 lead discoveries/day`
- `feat(codex): Phase 6 council deploy prompt + updated daily pull for both EC2 instances`
- `feat(connector-hub): 9-connector daily automation`
- `feat(phase-6): migration + department intelligence frontend dashboard`
- `feat(phase-6): 6-Layer Autonomous Intelligence System`
- `feat(batch4): frontier backend`
- `feat(batch3): captain bridge`
- `feat(batch2): intelligence engines`

If any are missing, the pull failed — retry before continuing.

---

## STEP 2 — INSTALL ALL DEPENDENCIES

```bash
cd /opt/jarvis
pip install -r requirements.txt --quiet
```

Verify these are installed:
```bash
python3 -c "import reportlab, httpx, apscheduler, sqlalchemy, fastapi, redis, anthropic; print('ALL OK')"
```

If any import fails, install it:
```bash
pip install reportlab httpx apscheduler sqlalchemy fastapi redis anthropic
```

---

## STEP 3 — RUN ALL DATABASE MIGRATIONS (PERMANENT SCHEMA)

```bash
cd /opt/jarvis
alembic upgrade head
```

This applies all 14 migrations (0001–0014) in the correct merge order:

```
0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007 → 0008 (Phase 6 tables)
  → 0009_intelligence_engines  ─────────────────────────────────────┐
  → 0009_master_prompt_gaps → 0010_captain → 0011_frontier ─────────┤
                                                          0012_merge ┤
                                          → 0013_bootstrap ──────────┤
                                          → 0013_connector_hub ──────┤
                                                          0014_merge (HEAD)
```

Tables created after this step:
- `department_intelligence_officers` — 15 AI department managers
- `department_milestones` — Council-reviewed milestones per DIO
- `technology_discoveries` — Tech evolution scan results
- `client_call_intelligence` — ElevenLabs call briefings
- `strategy_reports` — Daily + weekly strategy outputs
- `prospect_psychology_profiles` — ANALYTICAL/DRIVER/AMIABLE/EXPRESSIVE buyer profiles
- `revenue_forecasts` — Monte Carlo P10/P50/P90 projections
- `self_assessment_reports` — JARVIS A-F grade across 8 dimensions
- `client_health_scores` — CHAMPION/HEALTHY/AT_RISK/CRITICAL
- `dynamic_pricing_records` — STARTER $2,500 / GROWTH $5,500 / ENTERPRISE $12,000
- `autonomous_governance_log` — Tier 1/2/3 decision audit trail
- `captain_brain_dumps` — Captain voice/text brain dump processing
- `captain_email_intelligence` — Email thread intelligence extraction
- `predicted_actions` — Top 5 revenue-ranked next actions
- `captain_pushbacks` — APPROVE/CAUTION/PUSHBACK verdicts
- `expert_council_sessions` — 5-agent parallel council debates
- `red_team_analyses` — Adversarial strategy stress tests
- `relationship_nodes` / `relationship_edges` — CRM relationship graph
- `flywheel_snapshots` — Compound growth velocity snapshots
- `cialdini_sessions` — 6-principle persuasion sequences
- `connector_hub_ingestions` — Daily connector pipeline records
- `connector_hub_packages` — Individual package tracking with Council verdicts

Verify:
```bash
alembic current
# Must show: 0014_merge_0013_heads (head)
```

If you see multiple heads:
```bash
alembic merge heads -m "merge_all_heads"
alembic upgrade head
```

---

## STEP 4 — VERIFY ALL SERVICE FILES ARE IN PLACE

Run all these checks. If any directory is empty or missing, copy from backend/:

```bash
# Phase 6 — Council + Departments
ls /opt/jarvis/backend/app/services/departments/
# Must contain: department_agent_service.py, milestone_engine.py, tech_evolution_engine.py,
#               call_intelligence_service.py, strategy_report_service.py, __init__.py

# 9-Connector Pipeline
ls /opt/jarvis/backend/app/services/integrations/
# Must contain: connector_hub.py, github_bridge.py, hubspot_sync.py, market_intelligence_engine.py, __init__.py

# Intelligence Engines (Batch 2)
ls /opt/jarvis/backend/app/services/intelligence/
# Must contain: prospect_psychology.py, revenue_forecaster.py, self_assessment.py,
#               client_health.py, dynamic_pricing.py, memory_synthesis.py,
#               expert_council.py, red_team.py, conscience.py, flywheel.py, cialdini.py

# Captain Bridge (Batch 3)
ls /opt/jarvis/backend/app/services/captain/
# Must contain: bridge.py, predictive_action.py, pushback.py, voice_command.py, __init__.py

# CRM Relationship Graph (Batch 4)
ls /opt/jarvis/backend/app/services/crm/
# Must contain: relationship_graph.py

# Governance
ls /opt/jarvis/backend/app/services/governance/
# Must contain: autonomous_governance.py (+ existing invoice/proposal/contract files)
```

If any are missing, copy from backend to app:
```bash
APP=/opt/jarvis/app
BACKEND=/opt/jarvis/backend/app
cp -r $BACKEND/services/departments $APP/services/
cp -r $BACKEND/services/integrations $APP/services/
cp -r $BACKEND/services/intelligence $APP/services/
cp -r $BACKEND/services/captain $APP/services/
cp $BACKEND/services/crm/relationship_graph.py $APP/services/crm/
cp $BACKEND/services/governance/autonomous_governance.py $APP/services/governance/
```

---

## STEP 5 — VERIFY ALL MODELS ARE REGISTERED

Open `app/models/__init__.py`. It must contain ALL of these imports.
Add any that are missing:

```python
# Phase 6 — Department Intelligence
from app.models.department_intelligence import (
    DepartmentIntelligenceOfficer,
    DepartmentMilestone,
    TechnologyDiscovery,
    ClientCallIntelligence,
    StrategyReport,
)

# Batch 3 — Captain Bridge
from app.models.captain_intelligence import (
    CaptainBrainDump,
    CaptainEmailIntelligence,
    PredictedAction,
    CaptainPushback,
)

# 9-Connector Pipeline
from app.models.connector_hub import ConnectorHubIngestion, ConnectorHubPackage
```

---

## STEP 6 — VERIFY ALL ROUTES ARE REGISTERED

Open `app/api/v1/__init__.py`. It must contain ALL of these (add any missing):

```python
from app.api.v1.routes import departments        # Phase 6 — 22 endpoints
from app.api.v1.routes import captain            # Batch 3 — 10 endpoints
from app.api.v1.routes import intelligence       # Batch 2 — 8 endpoints
from app.api.v1.routes import connector_hub      # 9-Connector — 6 endpoints
from app.api.v1.routes import council            # Council endpoints
```

And the router includes:
```python
api_router.include_router(departments.router)
api_router.include_router(captain.router)
api_router.include_router(intelligence.router)
api_router.include_router(connector_hub.router)
api_router.include_router(council.router)
```

---

## STEP 7 — VERIFY SCHEDULER JOBS ARE REGISTERED

Open `app/services/scheduler/engine.py`. Verify ALL these jobs exist in `_register_default_jobs()`:

```python
# Core daily jobs
add_cron_job("morning_briefing", ..., hour=7, minute=0)
add_cron_job("daily_lead_score", ..., hour=2, minute=0)
add_cron_job("outreach_stats", ..., day_of_week="mon", hour=8, minute=0)
add_cron_job("overnight_pipeline_health", ..., hour=1, minute=0)

# 6-Layer Council System
add_cron_job("daily_strategy_report", ..., hour=23, minute=0)      # Layer 6
add_cron_job("milestone_bulk_review", ..., hour=10, minute=0)      # Layer 2
add_interval_job("tech_evolution_scan", ..., hours=6)              # Layer 4
add_interval_job("pre_call_briefing_trigger", ..., minutes=30)     # Layer 5
add_cron_job("weekly_strategy_review", ..., hour=7, day_of_week="sun")
add_cron_job("dio_health_check", ..., hour=6, minute=30)           # Layer 1

# 9-Connector Pipeline
add_cron_job("daily_connector_hub_ingestion", ..., hour=14, minute=30)  # 20:00 IST
add_cron_job("daily_market_intelligence", ..., hour=4, minute=0)        # 09:30 IST
```

If any are missing, add them. These are the permanent scheduled jobs — not patches.

---

## STEP 8 — VERIFY HARD DAILY LIMITS ARE IN PLACE

These are permanent system limits — never remove them:

**Outreach email cap (48/day):**
```bash
grep "DAILY_OUTREACH_CAP\|current_daily_cap\|return min" \
  backend/app/services/outreach/compliance.py
# Must show: return min(configured_cap, 48)
```

**Lead discovery cap (20/day from connectors):**
```bash
grep "DAILY_LEAD_DISCOVERY_CAP\|leads_raw\[:DAILY" \
  backend/app/services/integrations/connector_hub.py
# Must show: leads_raw = package.get("leads", [])[:DAILY_LEAD_DISCOVERY_CAP]
# and: DAILY_LEAD_DISCOVERY_CAP = 20
```

**How the 48 total leads/day work:**
- 20 leads from Claude's 9 connectors (pushed to GitHub /jarvis-data/ every morning)
- 28 leads from JARVIS's own Apollo discovery + lead scoring engine (internal)
- Total: 48 leads/day processed → 48 outreach emails/day sent
- Hard cap at Gmail prevents banning

---

## STEP 9 — SET ENVIRONMENT VARIABLES

Check what's already in `.env` — DO NOT overwrite existing values:
```bash
cat /opt/jarvis/.env | grep -E "HUBSPOT|JARVIS_REPO|ELEVENLABS|APOLLO|SLACK"
```

Add ONLY what is missing:
```bash
# Add to .env if not present (append, never overwrite)
[ -z "$(grep JARVIS_REPO_DATA_PATH .env)" ] && \
  echo "JARVIS_REPO_DATA_PATH=/opt/jarvis/jarvis-data" >> .env

[ -z "$(grep OUTREACH_DAILY_SEND_CAP .env)" ] && \
  echo "OUTREACH_DAILY_SEND_CAP=48" >> .env
```

Get secrets from AWS Secrets Manager (do NOT hardcode):
```bash
# These must come from AWS Secrets Manager — never hardcode
# HUBSPOT_ACCESS_TOKEN — HubSpot CRM sync
# ELEVENLABS_API_KEY — Call Intelligence voice agent
# APOLLO_API_KEY — jsGLiJu7s-1uUZPOzfPCDQ (already in .env from prior setup)
# SLACK_WEBHOOK_URL — Daily reports channel
```

---

## STEP 10 — BUILD FRONTEND

```bash
cd /opt/jarvis/frontend
npm install
npm run build
```

Verify all 25 views compiled successfully. Look for errors mentioning:
- `CaptainBridge` — Captain ops dashboard
- `DepartmentsView` — Phase 6 six-tab council dashboard
- `RevenueIntelligence` — Monte Carlo forecasts
- `WarRoom` — Threat detection + actions
- `SystemHUD` — Live system health
- `ExpertCouncil` — 5-agent debate viewer
- `Relationships` — CRM graph
- `IntelligenceHub` — All intelligence in one view

If build fails on a specific component, check the import paths.

Copy to nginx root if applicable:
```bash
NGINX_ROOT=$(cat /etc/nginx/sites-enabled/default 2>/dev/null | grep -m1 "root" | awk '{print $2}' | tr -d ';')
[ -n "$NGINX_ROOT" ] && cp -r dist/* "$NGINX_ROOT/" && echo "Frontend deployed to $NGINX_ROOT"
```

---

## STEP 11 — RESTART ALL SERVICES

```bash
cd /opt/jarvis
docker compose down
docker compose up -d --build
```

Wait 45 seconds:
```bash
sleep 45
docker compose ps
```

Every container must show `Up` or `running`. If any container is restarting:
```bash
docker compose logs <container_name> --tail=50
# Fix the error, then: docker compose restart <container_name>
```

Health checks:
```bash
curl -s http://localhost:8000/health | python3 -m json.tool
curl -s http://localhost:8000/readyz | python3 -m json.tool
```

Both must return `{"status": "ok"}` or `{"status": "healthy"}`.

---

## STEP 12 — INITIALIZE PHASE 6 DEPARTMENT INTELLIGENCE OFFICERS

```bash
curl -s -X POST "http://localhost:8000/api/v1/departments/dios/initialize" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}' | python3 -m json.tool
```

Expected: `{"status": "initialized", "dios_created": 15}`

The 15 DIOs initialized:
- Engineering DIO, AI/ML DIO, Cloud Infrastructure DIO, DevOps DIO, Security DIO
- Revenue DIO, Marketing DIO, Client Services DIO, Client Delivery DIO
- Customer Support DIO, Intelligence DIO, People Ops DIO, PMO DIO, Finance DIO, Strategy DIO

---

## STEP 13 — SMOKE TEST EVERY SYSTEM

Replace `$T` with `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa` or your actual tenant UUID.

```bash
T="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
BASE="http://localhost:8000"

echo "=== CORE HEALTH ==="
curl -sf "$BASE/health" && echo " ✓ health"
curl -sf "$BASE/readyz" && echo " ✓ readyz"

echo "=== PHASE 6 — COUNCIL + DEPARTMENTS ==="
curl -sf "$BASE/api/v1/departments/dios?tenant_id=$T" > /dev/null && echo " ✓ DIOs"
curl -sf "$BASE/api/v1/departments/milestones?tenant_id=$T" > /dev/null && echo " ✓ Milestones"
curl -sf "$BASE/api/v1/departments/tech/discoveries?tenant_id=$T" > /dev/null && echo " ✓ Tech Evolution"
curl -sf "$BASE/api/v1/departments/strategy/dashboard?tenant_id=$T" > /dev/null && echo " ✓ Strategy"
curl -sf "$BASE/api/v1/departments/health" > /dev/null && echo " ✓ Department Health"

echo "=== BATCH 2 — INTELLIGENCE ENGINES ==="
curl -sf "$BASE/api/v1/intelligence/self-assessment?tenant_id=$T" > /dev/null && echo " ✓ Self Assessment"
curl -sf "$BASE/api/v1/intelligence/pricing/catalog" > /dev/null && echo " ✓ Pricing Catalog"
curl -sf "$BASE/api/v1/intelligence/client-health?tenant_id=$T" > /dev/null && echo " ✓ Client Health"
curl -sf "$BASE/api/v1/intelligence/governance/evaluate?tenant_id=$T" > /dev/null && echo " ✓ Governance"

echo "=== BATCH 3 — CAPTAIN BRIDGE ==="
curl -sf "$BASE/api/v1/captain/situation?tenant_id=$T" > /dev/null && echo " ✓ Situation"
curl -sf "$BASE/api/v1/captain/threats?tenant_id=$T" > /dev/null && echo " ✓ Threats"
curl -sf "$BASE/api/v1/captain/predict-actions?tenant_id=$T" > /dev/null && echo " ✓ Predict Actions"

echo "=== BATCH 4 — FRONTIER SYSTEMS ==="
curl -sf "$BASE/api/v1/intelligence/flywheel?tenant_id=$T" > /dev/null && echo " ✓ Flywheel"
curl -sf "$BASE/api/v1/crm/relationship-graph?tenant_id=$T" > /dev/null && echo " ✓ Relationship Graph"

echo "=== 9-CONNECTOR PIPELINE ==="
curl -sf "$BASE/api/v1/connector-hub/status?tenant_id=$T" > /dev/null && echo " ✓ Connector Hub Status"
curl -sf "$BASE/api/v1/connector-hub/bridge-health" > /dev/null && echo " ✓ GitHub Bridge Health"

echo "=== VOICE ==="
curl -sf -X POST "$BASE/api/v1/voice/command" \
  -H "Content-Type: application/json" \
  -d "{\"transcript\": \"show pipeline\", \"tenant_id\": \"$T\"}" > /dev/null && echo " ✓ Voice Command"

echo ""
echo "=== ALL CHECKS COMPLETE ==="
```

Every line must show ✓. If any returns 404 → route not registered (fix Step 6).
If any returns 500 → `docker compose logs backend --tail=50`.

---

## STEP 14 — SET UP PERMANENT CRON JOB ON EACH EC2 INSTANCE

This is the permanent daily automation. Set it once — it runs forever.

```bash
cat > /home/ubuntu/jarvis_daily_pull.sh << 'SCRIPT'
#!/bin/bash
set -euo pipefail
LOG_PREFIX="[JARVIS $(date '+%Y-%m-%d %H:%M:%S UTC')]"
REPO_DIR="/opt/jarvis"
API="http://localhost:8000"
T="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

echo "$LOG_PREFIX ===== DAILY AUTOMATION START ====="
cd "$REPO_DIR"

# 1. Pull latest from GitHub (Claude's daily data push)
git pull origin claude/jarvis-cans-api-integration-ZThTD --rebase || {
    git rebase --abort 2>/dev/null || true
    git pull origin claude/jarvis-cans-api-integration-ZThTD --no-rebase
}
echo "$LOG_PREFIX GitHub pull complete."

# 2. Apply any new migrations automatically
alembic upgrade head 2>&1 | grep -v "^$" | tail -3
echo "$LOG_PREFIX Migrations checked."

# 3. Wait for JARVIS API
for i in $(seq 1 6); do
    curl -sf "$API/health" > /dev/null 2>&1 && break
    echo "$LOG_PREFIX Waiting for API... ($i/6)" && sleep 20
done

# 4. Connector Hub — ingest 20 leads from Claude's connectors + sequences + decks
INGEST=$(curl -sf -X POST "$API/api/v1/connector-hub/ingest" \
    -H "Content-Type: application/json" \
    -d "{\"tenant_id\":\"$T\",\"auto\":true}" 2>&1) || INGEST="FAILED"
echo "$LOG_PREFIX ConnectorHub: $INGEST"

# 5. Market intelligence generation for tomorrow
curl -sf -X POST "$API/api/v1/connector-hub/intelligence" \
    -H "Content-Type: application/json" \
    -d "{\"tenant_id\":\"$T\"}" > /dev/null 2>&1 || \
    echo "$LOG_PREFIX WARNING: Market intelligence failed (APScheduler covers at 04:00 UTC)"

# 6. Strategy report — Layer 6 cascade to all 15 DIOs
curl -sf -X POST "$API/api/v1/departments/strategy/daily-report" \
    -H "Content-Type: application/json" \
    -d "{\"tenant_id\":\"$T\"}" > /dev/null 2>&1 || \
    echo "$LOG_PREFIX WARNING: Strategy report failed (APScheduler covers at 23:00 UTC)"

# 7. Push JARVIS outputs back to GitHub for Claude to read tomorrow
git add jarvis-data/outputs/ jarvis-data/intelligence/ 2>/dev/null || true
git diff --cached --quiet 2>/dev/null || {
    git commit -m "chore(outputs): JARVIS outputs $(date '+%Y-%m-%d')" && \
    git push origin claude/jarvis-cans-api-integration-ZThTD
    echo "$LOG_PREFIX Outputs pushed to GitHub."
}

# 8. Notify Slack
[ -n "${SLACK_WEBHOOK_URL:-}" ] && curl -s -X POST "$SLACK_WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "{\"text\":\"*JARVIS Daily Complete* — $(date '+%Y-%m-%d %H:%M UTC'). Leads: 20 ingested. Strategy report sent. Pipeline active.\"}" > /dev/null

echo "$LOG_PREFIX ===== DAILY AUTOMATION COMPLETE ====="
SCRIPT

chmod +x /home/ubuntu/jarvis_daily_pull.sh
echo "Script created successfully."
```

Add to crontab:
```bash
crontab -l | grep -v jarvis_daily_pull > /tmp/crontab_clean
echo "30 14 * * * /home/ubuntu/jarvis_daily_pull.sh >> /var/log/jarvis_pull.log 2>&1" >> /tmp/crontab_clean
crontab /tmp/crontab_clean
crontab -l | grep jarvis
echo "Cron job confirmed."
```

---

## STEP 15 — VERIFY THE COMPLETE DAILY AUTOMATION LOOP

Trigger a manual test of the full loop:

```bash
echo "=== MANUAL DAILY LOOP TEST ==="
/home/ubuntu/jarvis_daily_pull.sh 2>&1 | tail -20

echo ""
echo "=== CHECKING INGESTION STATUS ==="
curl -s "http://localhost:8000/api/v1/connector-hub/status?tenant_id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" | python3 -m json.tool

echo ""
echo "=== CONFIRMING DAILY LIMITS ==="
# Confirm hard cap: 48 emails/day
python3 -c "
import sys
sys.path.insert(0, '.')
from app.services.outreach.compliance import outreach_compliance
cap = outreach_compliance.current_daily_cap()
assert cap == 48, f'Expected 48, got {cap}'
print(f'Email cap confirmed: {cap}/day')
"

# Confirm lead discovery cap: 20/day from connectors
python3 -c "
import sys
sys.path.insert(0, '.')
from app.services.integrations.connector_hub import DAILY_LEAD_DISCOVERY_CAP
assert DAILY_LEAD_DISCOVERY_CAP == 20, f'Expected 20, got {DAILY_LEAD_DISCOVERY_CAP}'
print(f'Lead discovery cap confirmed: {DAILY_LEAD_DISCOVERY_CAP}/day from connectors')
print('+ 28/day from JARVIS internal engine = 48 total leads/day')
"
```

---

## STEP 16 — FINAL VERIFICATION AND REPORT

Run the complete system status check:

```bash
echo "==============================================="
echo "JARVIS COMPLETE SYSTEM — FINAL VERIFICATION"
echo "==============================================="

echo ""
echo "1. Docker services:"
docker compose ps

echo ""
echo "2. Alembic migration head:"
alembic current

echo ""
echo "3. Cron job:"
crontab -l | grep jarvis

echo ""
echo "4. JARVIS health:"
curl -s http://localhost:8000/health

echo ""
echo "5. Scheduler active jobs:"
curl -s "http://localhost:8000/api/v1/scheduler/jobs" 2>/dev/null | python3 -m json.tool | grep '"id"' | head -20

echo ""
echo "6. DIOs initialized:"
curl -s "http://localhost:8000/api/v1/departments/dios?tenant_id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" | python3 -m json.tool | grep '"department"' | wc -l

echo ""
echo "==============================================="
echo "DEPLOYMENT COMPLETE"
echo "Report to Captain: Syed Abrar"
echo "==============================================="
```

---

## REPORT TO CAPTAIN WHEN DONE

Send this to Captain via Slack `#jarvis-alerts`:

```
✅ JARVIS Complete System Deployed

Instance: [EC2 IP address]
Migration head: 0014_merge_0013_heads
DIOs initialized: 15/15
All smoke tests: PASSED
Cron job: 14:30 UTC daily (20:00 IST)

DAILY AUTOMATION ACTIVE:
• Claude collects from 9 connectors → pushes to GitHub (09:00–12:00 IST)
• JARVIS pulls from GitHub → ingests 20 leads (20:00 IST)
• JARVIS internal engine discovers 28 more leads (daily)
• Total: 48 leads processed + 48 outreach emails sent (Google-safe)
• AI Council reviews all content (quality gate 0.70)
• 15 DIOs report → Council cascades strategy → all departments
• Strategy report generated daily at 23:00 UTC

No further action required from Captain.
The machine runs itself.
```

---

## WHAT RUNS AUTOMATICALLY — ZERO CAPTAIN INPUT REQUIRED

| Time (IST) | System | Action |
|---|---|---|
| 09:00 | Claude | Collects from Apollo, HubSpot, Close CRM, Klaviyo, Gamma, Zoho, Notion, Calendar, Slack |
| 09:30 | JARVIS APScheduler | Daily market intelligence generation (04:00 UTC) |
| 10:00 | Claude | Packages all data into /jarvis-data/daily/YYYY-MM-DD/ |
| 12:00 | Claude | Pushes packages to GitHub |
| 15:30 | JARVIS APScheduler | Milestone bulk review — Council reviews all pending DIOs milestones (10:00 UTC) |
| 20:00 | Codex EC2 cron | Pulls latest from GitHub |
| 20:00 | JARVIS ConnectorHub | Ingests 20 leads from connectors, loads sequences, matches decks |
| 20:00 | JARVIS Internal | Discovers 28 more leads via Apollo API + scoring engine |
| 20:00 | JARVIS Council | Quality gates all content — APPROVE (≥0.70) or REVISE (<0.70) |
| 20:30 | JARVIS Outreach | Sends up to 48 outreach emails (Google-safe hard cap) |
| 20:30 | Slack | #jarvis-sales daily report posted |
| 23:00 | JARVIS APScheduler | Daily strategy report — all 15 DIOs → Council → directives cascade |
| Every 6h | JARVIS APScheduler | Tech Evolution scan — discovers new AI/tech tools, scores 0-100 |
| Every 30m | JARVIS APScheduler | Pre-call briefing check — generates ElevenLabs briefing 1h before calls |
| 06:30 | JARVIS APScheduler | DIO health check — verifies all 15 departments operational |
| Sunday 07:00 UTC | JARVIS APScheduler | Weekly strategy review — full Council session, cascades to departments |

---

## PERMANENT SYSTEM CONSTANTS — DO NOT CHANGE

```python
DAILY_OUTREACH_CAP = 48          # Hard limit — Google Gmail safety
DAILY_LEAD_DISCOVERY_CAP = 20    # From Claude's 9 connectors
# JARVIS internal engine discovers additional 28 leads/day
# Total pipeline: 48 leads/day → 48 emails/day
COUNCIL_QUALITY_THRESHOLD = 0.7  # APPROVE if score >= 0.7, REVISE if below
ICP_QUALIFIED_THRESHOLD = 60.0   # Lead score minimum for pipeline entry
ICP_HOT_THRESHOLD = 80.0         # Auto-queue for immediate outreach
```

---

## IF ANYTHING FAILS — ROOT CAUSE FIRST, NEVER PATCH

| Symptom | Root Cause | Permanent Fix |
|---|---|---|
| `alembic multiple heads` | Two migrations share same down_revision | `alembic merge heads -m "merge"` then `alembic upgrade head` |
| `ImportError: cannot import X` | File missing from app/ directory | Copy from backend/ to app/ (Step 4) |
| `404 on /api/v1/departments` | Router not included in `__init__.py` | Add `api_router.include_router(departments.router)` (Step 6) |
| `500 on any endpoint` | Check `docker compose logs backend --tail=100` | Fix the Python error, restart container |
| `Scheduler jobs not running` | Job function not registered | Add to `_register_default_jobs()` in engine.py (Step 7) |
| `Emails sending over 48/day` | `compliance.py` cap wrong | Verify `return min(configured_cap, 48)` in `current_daily_cap()` |
| `More than 20 leads from connectors` | Hub cap not applied | Verify `leads_raw = package.get("leads", [])[:DAILY_LEAD_DISCOVERY_CAP]` |
| `Cron not running` | Cron not set | `crontab -e` → add `30 14 * * * /home/ubuntu/jarvis_daily_pull.sh >> /var/log/jarvis_pull.log 2>&1` |

Never wipe the database. Never overwrite `.env`. Never patch — fix the root cause.

---

_Aliyar Solutions | CEO: Syed Abrar | JARVIS Autonomous Operations System_
_This prompt is permanent. Run it once. JARVIS runs forever._
