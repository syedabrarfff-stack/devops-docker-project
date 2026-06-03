# CODEX DEPLOYMENT PROMPT — ALL 4 BATCHES
## Deploy to EC2: `/opt/jarvis/`

You are JARVIS Codex. Execute every step below in strict order.
Do NOT stop. Do NOT ask questions. If anything is unclear, make the best decision and continue.
If a step fails, fix the error and retry before moving on.

---

## SYSTEM IDENTITY

Working directory on EC2: `/opt/jarvis/`
GitHub repo: `syedabrarfff-stack/devops-docker-project`
Branch: `claude/jarvis-cans-api-integration-ZThTD`
Backend lives at: `app/` inside the working directory
Docker stack: `docker compose up -d --build` (or `docker-compose` depending on EC2 version)

---

## STEP 1 — PULL LATEST CODE FROM GITHUB

```bash
cd /opt/jarvis
git fetch origin
git pull origin claude/jarvis-cans-api-integration-ZThTD --rebase
```

If there are local conflicts, stash and pull:
```bash
git stash
git pull origin claude/jarvis-cans-api-integration-ZThTD --rebase
git stash pop
```

Verify the pull succeeded — you should see these commits in `git log --oneline -10`:
- feat(batch4): frontier backend
- feat(batch3): captain bridge
- feat(batch2): intelligence engines
- feat(codex): single master prompt

---

## STEP 2 — INSTALL PYTHON DEPENDENCIES

```bash
cd /opt/jarvis
pip install -r requirements.txt --quiet
```

If `requirements.txt` is missing the following packages, add them and re-run pip install:
- `asyncio` (stdlib)
- `random` (stdlib)
- `statistics` (stdlib)

All other dependencies (fastapi, sqlalchemy, alembic, asyncpg, redis, reportlab) should already be installed.

---

## STEP 3 — RUN ALL DATABASE MIGRATIONS

Run Alembic migrations in order. The EC2 database already has migrations 0001–0008 applied (from batch 1 deployment). Apply the new ones:

```bash
cd /opt/jarvis
alembic upgrade head
```

This will apply:
- `0009_intelligence_engines` — adds 6 tables: prospect_psychology_profiles, revenue_forecasts, self_assessment_reports, client_health_scores, dynamic_pricing_records, autonomous_governance_log
- `0009_master_prompt_contract_gaps` — any gap fixes
- `0010_captain_bridge` — adds 4 tables: captain_brain_dumps, captain_email_intelligence, predicted_actions, captain_pushbacks + two new columns on leads table
- `0011_frontier_systems` — adds 6 tables: expert_council_sessions, red_team_analyses, relationship_nodes, relationship_edges, flywheel_snapshots, cialdini_sessions

If `alembic upgrade head` fails with a revision conflict (two heads), run:
```bash
alembic merge heads -m "merge_batch_heads"
alembic upgrade head
```

Verify migrations applied:
```bash
alembic current
```

---

## STEP 4 — DEPLOY BATCH 2: INTELLIGENCE ENGINES

The following new service files now exist in the repo at `backend/app/services/intelligence/`:
- `prospect_psychology.py` — ProspectPsychologyEngine
- `revenue_forecaster.py` — RevenueForecaster with Monte Carlo
- `self_assessment.py` — JarvisSelfAssessment (8 dimensions, A-F grades)
- `client_health.py` — ClientHealthScorer
- `dynamic_pricing.py` — DynamicPricingEngine
- `memory_synthesis.py` — MemorySynthesisEngine

And at `backend/app/services/governance/`:
- `autonomous_governance.py` — AutonomousGovernanceEngine (Tier 1/2/3 decisions)

**Action required:** Copy/sync these files into your live app structure. If your EC2 app uses the same directory layout as the GitHub repo (`app/services/...`), the git pull in Step 1 already placed them correctly.

Verify the files exist:
```bash
ls /opt/jarvis/app/services/intelligence/
ls /opt/jarvis/app/services/governance/
```

If they are NOT there (because your EC2 app structure differs), manually copy from the GitHub pull location:
```bash
cp -r /opt/jarvis/backend/app/services/intelligence/* /opt/jarvis/app/services/intelligence/
cp /opt/jarvis/backend/app/services/governance/autonomous_governance.py /opt/jarvis/app/services/governance/
```

New intelligence endpoints are now registered at:
- `POST /api/v1/intelligence/prospect-psychology`
- `POST /api/v1/intelligence/revenue-forecast`
- `GET /api/v1/intelligence/self-assessment`
- `POST /api/v1/intelligence/dynamic-pricing`
- `GET /api/v1/intelligence/governance/evaluate`
- `GET /api/v1/intelligence/client-health`
- `GET /api/v1/intelligence/pricing/catalog`

---

## STEP 5 — DEPLOY BATCH 3: CAPTAIN BRIDGE

New service directory: `backend/app/services/captain/`
Files: `__init__.py`, `bridge.py`, `predictive_action.py`, `pushback.py`, `voice_command.py`

New model file: `backend/app/models/captain_intelligence.py`
(Contains: CaptainBrainDump, CaptainEmailIntelligence, PredictedAction, CaptainPushback)

Updated route: `backend/app/api/v1/routes/captain.py`
(Now has 10+ endpoints including /captain/bring-lead, /captain/brain-dump, /captain/situation, /captain/threats, /captain/predict-actions, /captain/war-room-brief, /captain/evaluate-decision, /voice/command, /voice/morning-briefing)

**Action required:** Same as Step 4 — verify files are in place. If EC2 directory differs, copy:
```bash
cp -r /opt/jarvis/backend/app/services/captain /opt/jarvis/app/services/
cp /opt/jarvis/backend/app/models/captain_intelligence.py /opt/jarvis/app/models/
```

Register the `captain_intelligence` model in `app/models/__init__.py` if not already there:
```python
from app.models.captain_intelligence import CaptainBrainDump, CaptainEmailIntelligence, PredictedAction, CaptainPushback
```

Register new voice router in `app/api/v1/__init__.py` or `app/main.py`:
```python
from app.api.v1.routes.captain import voice_router
app.include_router(voice_router, prefix="/api/v1")
```

---

## STEP 6 — DEPLOY BATCH 4: FRONTIER INTELLIGENCE SYSTEMS

New backend service files:
- `backend/app/services/intelligence/expert_council.py` — ExpertCouncilEngine (5 parallel AI agents)
- `backend/app/services/intelligence/red_team.py` — RedTeamEngine (adversarial analysis)
- `backend/app/services/intelligence/conscience.py` — ConscienceLayer (values engine)
- `backend/app/services/intelligence/flywheel.py` — FlywheelEngine (compound growth)
- `backend/app/services/intelligence/cialdini.py` — CialdiniEngine (persuasion engineering)
- `backend/app/services/crm/relationship_graph.py` — RelationshipGraph

New endpoints now active:
- `POST /api/v1/intelligence/expert-council`
- `POST /api/v1/intelligence/red-team/run`
- `GET /api/v1/intelligence/flywheel`
- `POST /api/v1/intelligence/cialdini/enhance`
- `POST /api/v1/intelligence/cialdini/sequence`
- `GET /api/v1/crm/relationship-graph`
- `GET /api/v1/crm/relationship-graph/warm-intros/{lead_id}`

**Action required:** Copy if needed, same pattern as Steps 4-5.

---

## STEP 7 — DEPLOY FRONTEND (7 NEW VIEWS)

New React views at `frontend/src/components/`:
- `CaptainBridge/CaptainBridge.jsx`
- `RevenueIntelligence/RevenueIntelligence.jsx`
- `WarRoom/WarRoom.jsx`
- `SystemHUD/SystemHUD.jsx`
- `ExpertCouncil/ExpertCouncil.jsx`
- `Relationships/Relationships.jsx`
- `IntelligenceHub/IntelligenceHub.jsx`

**Build the frontend:**
```bash
cd /opt/jarvis/frontend
npm install
npm run build
```

If the frontend is served by nginx from a dist folder:
```bash
cp -r /opt/jarvis/frontend/dist/* /var/www/html/
```
or whatever your nginx root is. Check with:
```bash
cat /etc/nginx/sites-enabled/default | grep root
```

---

## STEP 8 — RESTART ALL SERVICES

```bash
cd /opt/jarvis
docker compose down
docker compose up -d --build
```

Wait 30 seconds for services to start, then verify:
```bash
docker compose ps
curl -s http://localhost:8000/health | python3 -m json.tool
curl -s http://localhost:8000/readyz | python3 -m json.tool
```

Both endpoints should return `{"status": "healthy"}` or equivalent.

---

## STEP 9 — SMOKE TEST ALL BATCH ENDPOINTS

Run these curl tests to confirm every batch is live:

```bash
# Batch 2 — Intelligence Engines
curl -s -X GET "http://localhost:8000/api/v1/intelligence/self-assessment?tenant_id=00000000-0000-0000-0000-000000000001" | python3 -m json.tool
curl -s -X GET "http://localhost:8000/api/v1/intelligence/pricing/catalog" | python3 -m json.tool

# Batch 3 — Captain Bridge
curl -s -X GET "http://localhost:8000/api/v1/captain/situation?tenant_id=00000000-0000-0000-0000-000000000001" | python3 -m json.tool
curl -s -X GET "http://localhost:8000/api/v1/captain/threats?tenant_id=00000000-0000-0000-0000-000000000001" | python3 -m json.tool
curl -s -X GET "http://localhost:8000/api/v1/captain/predict-actions?tenant_id=00000000-0000-0000-0000-000000000001" | python3 -m json.tool

# Batch 4 — Frontier Systems
curl -s -X GET "http://localhost:8000/api/v1/intelligence/flywheel?tenant_id=00000000-0000-0000-0000-000000000001" | python3 -m json.tool
curl -s -X GET "http://localhost:8000/api/v1/crm/relationship-graph?tenant_id=00000000-0000-0000-0000-000000000001" | python3 -m json.tool

# Voice
curl -s -X POST "http://localhost:8000/api/v1/voice/command" -H "Content-Type: application/json" -d '{"transcript": "show me the pipeline", "tenant_id": "00000000-0000-0000-0000-000000000001"}' | python3 -m json.tool
```

Replace `00000000-0000-0000-0000-000000000001` with your actual Aliyar Solutions tenant UUID from the database.

If any endpoint returns 404, check that the route is registered in `app/main.py` or `app/api/v1/__init__.py`.
If any endpoint returns 500, check docker logs: `docker compose logs backend --tail=50`

---

## STEP 10 — FINAL COMMIT AND REPORT

After everything is deployed and smoke tests pass:

```bash
cd /opt/jarvis
git add -A
git commit -m "deploy: all 4 batches live on EC2 — intelligence engines, captain bridge, frontier systems, frontend views"
git push origin claude/jarvis-cans-api-integration-ZThTD
```

Then report back to Captain with:
- Which migrations were applied
- Which endpoints are now live
- Any errors encountered and how they were resolved
- Current docker compose ps output
- Health check results

---

## WHAT IS NOW DEPLOYED AFTER ALL 4 BATCHES

| System | What It Does |
|---|---|
| ProspectPsychologyEngine | Profiles every lead as ANALYTICAL/DRIVER/AMIABLE/EXPRESSIVE |
| RevenueForecaster | Monte Carlo P10/P50/P90 revenue forecast for 30/60/90 days |
| JarvisSelfAssessment | Grades JARVIS performance A-F across 8 operational dimensions |
| ClientHealthScorer | CHAMPION/HEALTHY/AT_RISK/CRITICAL scoring for every client |
| DynamicPricingEngine | Auto-calculates optimal price with 6 adjustment factors |
| MemorySynthesisEngine | Converts every interaction into a structured memory |
| AutonomousGovernanceEngine | Tier 1 (auto) / Tier 2 (notify) / Tier 3 (captain approval) decision routing |
| CaptainIntelligenceBridge | Lead intake, brain dump parser, email thread intelligence, threat detection |
| PredictiveActionEngine | Top 5 next actions ranked by revenue impact |
| JarvisPushbackEngine | Evaluates Captain decisions, pushes back when risky |
| VoiceCommandProcessor | Processes voice transcripts into actions |
| ExpertCouncilEngine | 5 parallel AI agents (Strategist, Contrarian, Technologist, Financier, Ethicist) |
| RedTeamEngine | Weekly adversarial stress-testing of business strategy |
| ConscienceLayer | Values engine — blocks unethical actions |
| RelationshipGraph | Maps connections between leads/clients/partners, finds warm intros |
| FlywheelEngine | Measures compound growth velocity and weakest link |
| CialdiniEngine | Engineers outreach using 6 persuasion principles |
| 7 React Views | Captain Bridge, Revenue Intelligence, War Room, System HUD, Expert Council, Relationships, Intelligence Hub |

---

## IF ANYTHING FAILS

1. Check docker logs: `docker compose logs --tail=100`
2. Check alembic state: `alembic current` and `alembic history`
3. Fix the specific error and re-run the failed step
4. Never wipe the database — only run forward migrations
5. Never overwrite `.env` — all secrets stay in `.env` as-is
6. If a Python import fails, check that the new service file exists and has no syntax errors: `python3 -c "from app.services.intelligence.expert_council import ExpertCouncilEngine"`

Do not stop until all smoke tests pass. Report completion to Captain.
