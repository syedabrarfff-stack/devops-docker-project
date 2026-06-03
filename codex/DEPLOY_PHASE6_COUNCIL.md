# CODEX DEPLOYMENT PROMPT — PHASE 6: AI COUNCIL + DEPARTMENT INTELLIGENCE
## Deploy to ALL EC2 Instances

You are JARVIS Codex. Execute every step below in strict order on EVERY EC2 instance.
Do NOT stop. Do NOT ask questions. Make the best decision and continue.
If a step fails, fix the error and retry before moving on.

---

## SYSTEM IDENTITY

GitHub repo: `syedabrarfff-stack/devops-docker-project`
Branch: `claude/jarvis-cans-api-integration-ZThTD`
Working directory (EC2 instance 1): `/opt/jarvis/`
Working directory (EC2 instance 2): same path unless configured differently
Docker stack: `docker compose up -d --build`

---

## WHAT THIS DEPLOYS

| Layer | System | Purpose |
|---|---|---|
| Layer 1 | Department Intelligence Officers (DIOs) | 15 AI officers across all departments — each monitors KPIs, submits milestones, escalates issues |
| Layer 2 | Council Intelligence Loop | Every DIO milestone → AI Council reviews → improvement PDF generated → DIO implements |
| Layer 4 | Technology Evolution Engine | 24/7 scan of AI/tech landscape — scores discoveries 0-100, auto-submits high-value finds (>80) to Council |
| Layer 5 | Call Intelligence (ElevenLabs) | Pre-call briefing generation, what-to-say/not-say, objection handlers, Council-reviewed script, post-call debrief |
| Layer 6 | Strategy Oversight | Daily + weekly strategy reports, Council strategic session, directives cascade to all 15 departments |
| Connector Hub | 9-Connector Daily Pipeline | Apollo → HubSpot → Klaviyo → Gamma → Slack daily ingestion at 20:00 IST |

---

## STEP 1 — PULL LATEST CODE

```bash
cd /opt/jarvis
git fetch origin
git pull origin claude/jarvis-cans-api-integration-ZThTD --rebase
```

If conflicts occur:
```bash
git rebase --abort
git stash
git pull origin claude/jarvis-cans-api-integration-ZThTD
git stash pop
```

Verify these commits are present in `git log --oneline -5`:
- `fix(migrations): merge dual-0013 heads`
- `feat(connector-hub): 9-connector daily automation`
- `feat(phase-6): migration + department intelligence frontend dashboard`
- `feat(phase-6): 6-Layer Autonomous Intelligence System`

---

## STEP 2 — INSTALL DEPENDENCIES

```bash
cd /opt/jarvis
pip install -r requirements.txt --quiet
```

Phase 6 requires these packages (should already be in requirements.txt):
- `reportlab` — PDF generation for milestone reports
- `httpx` — async HTTP for ElevenLabs + HubSpot APIs
- `apscheduler` — scheduled jobs

---

## STEP 3 — RUN ALL DATABASE MIGRATIONS

```bash
cd /opt/jarvis
alembic upgrade head
```

This applies migrations 0008 through 0014 in order:
- `0008_department_intelligence` — 5 tables: department_intelligence_officers, department_milestones, technology_discoveries, client_call_intelligence, strategy_reports
- `0009_intelligence_engines` — 6 intelligence tables
- `0009_master_prompt_contract_gaps` — gap fixes
- `0010_captain_bridge` — 4 captain tables
- `0011_frontier_systems` — 6 frontier tables
- `0012_merge_heads` — merge commit (no schema change)
- `0013_bootstrap_live_schema_gaps` — live schema gaps
- `0013_connector_hub` (→ now `0014_connector_hub` on remote) — connector_hub_ingestions, connector_hub_packages
- `0014_merge_0013_heads` — merge commit (no schema change)

If alembic reports multiple heads:
```bash
alembic merge heads -m "merge_deployment_heads"
alembic upgrade head
```

Verify:
```bash
alembic current
# Should show: 0014_merge_0013_heads (head)
```

---

## STEP 4 — VERIFY PHASE 6 FILES ARE IN PLACE

```bash
ls /opt/jarvis/backend/app/services/departments/
```

Expected files:
- `__init__.py`
- `department_agent_service.py`
- `milestone_engine.py`
- `tech_evolution_engine.py`
- `call_intelligence_service.py`
- `strategy_report_service.py`

If NOT there (EC2 app uses different directory layout), copy from backend:
```bash
cp -r /opt/jarvis/backend/app/services/departments /opt/jarvis/app/services/
cp /opt/jarvis/backend/app/models/department_intelligence.py /opt/jarvis/app/models/
```

Also verify connector hub:
```bash
ls /opt/jarvis/backend/app/services/integrations/
# Should show: __init__.py, connector_hub.py, github_bridge.py, hubspot_sync.py, market_intelligence_engine.py
```

---

## STEP 5 — REGISTER NEW MODELS

In `app/models/__init__.py`, verify these imports exist (add if missing):
```python
from app.models.department_intelligence import (
    DepartmentIntelligenceOfficer,
    DepartmentMilestone,
    TechnologyDiscovery,
    ClientCallIntelligence,
    StrategyReport,
)
from app.models.connector_hub import ConnectorHubIngestion, ConnectorHubPackage
```

---

## STEP 6 — REGISTER NEW ROUTES

In `app/main.py` or `app/api/v1/__init__.py`, verify these routers are included (add if missing):

```python
from app.api.v1.routes.departments import router as departments_router
from app.api.v1.routes.connector_hub import router as connector_hub_router

app.include_router(departments_router, prefix="/api/v1")
app.include_router(connector_hub_router, prefix="/api/v1")
```

---

## STEP 7 — SET ENVIRONMENT VARIABLES

Add to `/opt/jarvis/.env` (DO NOT overwrite existing values):
```bash
# Only add these if not already present
echo "JARVIS_REPO_DATA_PATH=/opt/jarvis/jarvis-data" >> .env
echo "HUBSPOT_ACCESS_TOKEN=your_token_here" >> .env
```

Replace `your_token_here` with the actual HubSpot token from AWS Secrets Manager.

---

## STEP 8 — BUILD FRONTEND

```bash
cd /opt/jarvis/frontend
npm install
npm run build
```

New Phase 6 views:
- `/departments` — 6-tab dashboard (Overview, DIOs, Milestones, Tech Evolution, Call Intelligence, Strategy)

Copy dist to nginx root if applicable:
```bash
cat /etc/nginx/sites-enabled/default | grep root
# Then: cp -r dist/* <nginx_root>/
```

---

## STEP 9 — RESTART ALL SERVICES

```bash
cd /opt/jarvis
docker compose down
docker compose up -d --build
```

Wait 30 seconds, then verify:
```bash
docker compose ps
curl -s http://localhost:8000/health | python3 -m json.tool
curl -s http://localhost:8000/readyz | python3 -m json.tool
```

---

## STEP 10 — INITIALIZE DEPARTMENT INTELLIGENCE OFFICERS

After restart, initialize all 15 DIOs:
```bash
curl -s -X POST "http://localhost:8000/api/v1/departments/dios/initialize" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}' | python3 -m json.tool
```

Expected: `{"status": "initialized", "dios_created": 15}`

---

## STEP 11 — SMOKE TEST ALL PHASE 6 ENDPOINTS

```bash
TENANT="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

# Layer 1 — DIOs
curl -s "http://localhost:8000/api/v1/departments/dios?tenant_id=$TENANT" | python3 -m json.tool

# Layer 2 — Milestones
curl -s "http://localhost:8000/api/v1/departments/milestones?tenant_id=$TENANT" | python3 -m json.tool

# Layer 4 — Tech Evolution
curl -s "http://localhost:8000/api/v1/departments/tech/discoveries?tenant_id=$TENANT" | python3 -m json.tool

# Layer 6 — Strategy
curl -s "http://localhost:8000/api/v1/departments/strategy/dashboard?tenant_id=$TENANT" | python3 -m json.tool

# Connector Hub
curl -s "http://localhost:8000/api/v1/connector-hub/status?tenant_id=$TENANT" | python3 -m json.tool

# Council
curl -s "http://localhost:8000/api/v1/intelligence/self-assessment?tenant_id=$TENANT" | python3 -m json.tool
```

Replace `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa` with your actual Aliyar Solutions tenant UUID.

If any endpoint returns 404: route not registered in main.py — add it (Step 6).
If any endpoint returns 500: `docker compose logs backend --tail=50`

---

## STEP 12 — SET UP DAILY CRON JOB

Set up the permanent daily automation on EACH EC2 instance:

```bash
# Create the pull script
cat > /home/ubuntu/jarvis_daily_pull.sh << 'EOF'
#!/bin/bash
set -euo pipefail
LOG_PREFIX="[JARVIS-PULL $(date '+%Y-%m-%d %H:%M:%S UTC')]"
REPO_DIR="/opt/jarvis"
JARVIS_API="http://localhost:8000"
TENANT_ID="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

echo "$LOG_PREFIX Starting daily pull..."
cd "$REPO_DIR"

# Pull latest data from GitHub (Claude's daily push)
git pull origin claude/jarvis-cans-api-integration-ZThTD --rebase || {
    git rebase --abort 2>/dev/null || true
    git pull origin claude/jarvis-cans-api-integration-ZThTD --no-rebase
}
echo "$LOG_PREFIX Git pull complete."

# Wait for JARVIS API
for i in $(seq 1 5); do
    curl -sf "$JARVIS_API/health" > /dev/null 2>&1 && break
    echo "$LOG_PREFIX Waiting for JARVIS API (attempt $i/5)..."
    sleep 30
done

# Trigger connector hub ingestion (leads, sequences, decks, intelligence)
curl -sf -X POST "$JARVIS_API/api/v1/connector-hub/ingest" \
    -H "Content-Type: application/json" \
    -d "{\"tenant_id\": \"$TENANT_ID\", \"auto\": true}" || \
    echo "$LOG_PREFIX WARNING: Ingestion failed"

# Trigger market intelligence generation
curl -sf -X POST "$JARVIS_API/api/v1/connector-hub/intelligence" \
    -H "Content-Type: application/json" \
    -d "{\"tenant_id\": \"$TENANT_ID\"}" || \
    echo "$LOG_PREFIX WARNING: Intelligence trigger failed (non-fatal)"

# Trigger daily strategy report (Layer 6)
curl -sf -X POST "$JARVIS_API/api/v1/departments/strategy/daily-report" \
    -H "Content-Type: application/json" \
    -d "{\"tenant_id\": \"$TENANT_ID\"}" || \
    echo "$LOG_PREFIX WARNING: Strategy report failed (non-fatal)"

# Commit JARVIS outputs back to GitHub (for Claude to read tomorrow)
git add jarvis-data/outputs/ jarvis-data/intelligence/ 2>/dev/null || true
git diff --cached --quiet 2>/dev/null || \
    git commit -m "chore(outputs): JARVIS daily outputs $(date '+%Y-%m-%d')" && \
    git push origin claude/jarvis-cans-api-integration-ZThTD || true

echo "$LOG_PREFIX Daily pull complete."
EOF

chmod +x /home/ubuntu/jarvis_daily_pull.sh
```

Add to crontab:
```bash
crontab -e
# Add this line:
30 14 * * * /home/ubuntu/jarvis_daily_pull.sh >> /var/log/jarvis_pull.log 2>&1
```

Verify cron is set:
```bash
crontab -l | grep jarvis
```

---

## STEP 13 — FINAL COMMIT AND REPORT

After all smoke tests pass on ALL instances:

```bash
cd /opt/jarvis
git add -A
git diff --cached --quiet || git commit -m "deploy: phase-6 council + connector hub live on EC2"
git push origin claude/jarvis-cans-api-integration-ZThTD
```

Report back to Captain:
- Which EC2 instance(s) this was deployed on
- How many DIOs were initialized
- Whether all smoke tests passed
- Current `docker compose ps` output
- Health check result
- Cron job confirmation (`crontab -l`)

---

## AFTER DEPLOYMENT — WHAT RUNS AUTOMATICALLY

| Time (IST) | System | Action |
|---|---|---|
| 09:00 | Claude | Collects from 9 connectors (Apollo, HubSpot, Klaviyo, Gamma, etc.) |
| 09:30 | Claude | Generates daily market intelligence report |
| 12:00 | Claude | Packages all data → pushes to GitHub `/jarvis-data/` |
| 20:00 | Codex EC2 cron | Pulls latest from GitHub |
| 20:00 | JARVIS | Ingests leads, sequences, decks through ConnectorHub |
| 20:00 | JARVIS | AI Council quality-gates all content (0.7 threshold) |
| 20:30 | JARVIS | Slack `#jarvis-sales` daily report posted |
| 23:00 | JARVIS APScheduler | Daily strategy report (Layer 6) — cascades to all 15 DIOs |
| Every 6h | JARVIS APScheduler | Tech evolution scan (Layer 4) |
| Daily 10:00 | JARVIS APScheduler | Milestone bulk review — Council reviews all pending milestones |
| Daily 06:30 | JARVIS APScheduler | DIO health check across all 15 departments |

**Captain's input required:** Zero. The machine runs itself.

---

## IF ANYTHING FAILS

1. Check logs: `docker compose logs backend --tail=100`
2. Check alembic: `alembic current` and `alembic history`
3. Check cron: `tail -f /var/log/jarvis_pull.log`
4. Never wipe the database — only run forward migrations
5. Never overwrite `.env` — secrets stay as-is
6. Test imports: `python3 -c "from app.services.departments.department_agent_service import DepartmentAgentService"`

Do not stop until all smoke tests pass on ALL instances. Report to Captain when done.
