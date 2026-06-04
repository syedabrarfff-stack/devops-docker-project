# AIONX Deployment Manifest — Batch 2: Sovereign Organs
## Production-Ready Deployment Package for Codex/EC2

**Branch:** `claude/jarvis-cans-api-integration-ZThTD`
**EC2 Path:** `/opt/jarvis`
**Deployment Date:** 2026-06-04

---

## STEP 1 — PULL FROM GITHUB

```bash
cd /opt/jarvis
git fetch origin claude/jarvis-cans-api-integration-ZThTD
git checkout claude/jarvis-cans-api-integration-ZThTD
git pull origin claude/jarvis-cans-api-integration-ZThTD
```

---

## STEP 2 — RUN DATABASE MIGRATION

```bash
cd /opt/jarvis
docker-compose exec backend alembic upgrade head
```

**Verifies:**
```bash
docker-compose exec postgres psql -U jarvis -d jarvis -c "\dt decision_*"
docker-compose exec postgres psql -U jarvis -d jarvis -c "\dt client_digital_twins"
docker-compose exec postgres psql -U jarvis -d jarvis -c "\dt wisdom_index_snapshots"
docker-compose exec postgres psql -U jarvis -d jarvis -c "\dt convergence_council_*"
docker-compose exec postgres psql -U jarvis -d jarvis -c "\dt sentinel_*"
```

Expected: All 23 new AIONX tables visible.

---

## STEP 3 — REBUILD BACKEND IMAGE

```bash
cd /opt/jarvis
docker-compose build backend
```

---

## STEP 4 — ROLLING RESTART

```bash
docker-compose up -d --no-deps backend
```

Wait 15 seconds, then verify health:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health
```

Both must return: `{"status": "ok"}`

---

## STEP 5 — VERIFY AIONX ENDPOINTS

```bash
# Wisdom Index
curl http://localhost:8000/api/v1/aionx/wisdom

# Sentinel observations
curl http://localhost:8000/api/v1/aionx/sentinel/threats

# Decision genealogy (Glass Wall)
curl http://localhost:8000/api/v1/aionx/decisions/genealogy
```

---

## STEP 6 — VERIFY SCHEDULER JOBS

```bash
curl http://localhost:8000/api/v1/scheduler/jobs
```

Expected: Existing 7+ scheduler jobs active.

---

## STEP 7 — END-TO-END VERIFICATION CHECKLIST

```
[ ] Migration 0017 applied: all 23 AIONX tables exist
[ ] /api/v1/health returns status: ok
[ ] /api/v1/aionx/wisdom returns JSON with wisdom_score
[ ] /api/v1/aionx/decisions/genealogy returns JSON array
[ ] /api/v1/aionx/sentinel/threats returns JSON array
[ ] Backend logs show no import errors
[ ] No broken dependencies in startup
[ ] Existing routes still operational (check /api/v1/leads, /api/v1/outreach)
[ ] Database connection pool healthy
[ ] Redis connection healthy
```

---

## NEW FILES IN THIS DEPLOYMENT

### Database Migration
- `backend/alembic/versions/0017_aionx_sovereign_organs.py`
  - 23 new tables for all sovereign organs
  - Indexes on all foreign keys and high-traffic columns

### Models
- `backend/app/models/aionx_organs.py`
  - SQLAlchemy mapped classes for all 23 AIONX tables

### Services
- `backend/app/services/aionx/__init__.py`
- `backend/app/services/aionx/decision_memory_engine.py` — Decision Object creation, retrospectives, pattern extraction, Glass Wall
- `backend/app/services/aionx/sentinel_layer.py` — 24/7 world observation, threat registry
- `backend/app/services/aionx/provider_sovereign_council.py` — 11-provider advisory council with Brier-scored calibration
- `backend/app/services/aionx/grand_convergence_council.py` — 10-phase convergence state machine, live feed
- `backend/app/services/aionx/institutional_wisdom_index.py` — Weekly 0-1000 score computation
- `backend/app/services/aionx/client_digital_twin.py` — Persistent client executive profile, HIA briefings

### Routes
- `backend/app/api/v1/routes/aionx.py` — 25 endpoints across all organs

### Registrations
- `backend/app/models/__init__.py` — aionx_organs module registered
- `backend/app/api/v1/__init__.py` — aionx router registered

---

## ROLLBACK PROCEDURE

If any step fails:

```bash
cd /opt/jarvis
docker-compose exec backend alembic downgrade 0016_consciousness_upgrade
docker-compose up -d --no-deps backend
```

---

## CONSTITUTIONAL INTEGRITY CHECK

After deployment, verify immutable core is untouched:

```bash
# Governance layer must still be active
curl http://localhost:8000/api/v1/governance/status

# Existing council routes must still work
curl http://localhost:8000/api/v1/council/status
```

---

## BATCH STATUS

| Batch | Name | Status |
|-------|------|--------|
| Batch 1 | 33-Stage Client Journey Orchestrator | PARTIAL — Orchestration Cortex live |
| Batch 2 | 9 Sovereign Organs + Supreme Council Layer | DEPLOYED |
| Batch 2.5 | Orchestration Cortex + Scheduler Heartbeat | **THIS DEPLOYMENT** |
| Batch 3 | Infrastructure, HIA System, Zero-SPOF, Governance | PENDING |

---

## BATCH 2.5 — ORCHESTRATION CORTEX + HEARTBEAT (makes organs autonomous)

After pulling and restarting backend, the organs are no longer dormant.

**New scheduler jobs (auto-registered on backend start):**

| Job | Cadence | Purpose |
|-----|---------|---------|
| `aionx_sentinel_sweep` | every 2h | Layer 1 — world observation |
| `aionx_escalation_processor` | every 30m | Layer 2 — escalate signals to councils |
| `aionx_operational_iq` | every 1h | Live Operational IQ recompute |
| `aionx_retro_30d` | daily 22:00 | 30-day decision retrospective |
| `aionx_retro_90d` | daily 22:15 | 90-day decision retrospective |
| `aionx_twin_predictions` | daily 03:00 | Refresh churn/upsell; fire churn alerts |
| `aionx_wisdom_weekly` | Sun 19:00 | Institutional Wisdom Index |
| `aionx_decision_retrospective` | Sun 19:30 | Weekly decision review |

**New endpoints:**

```bash
# Live Operational IQ (0-100) — how the whole company is doing right now
curl http://localhost:8000/api/v1/aionx/cortex/operational-iq

# Full situational snapshot for Captain Glass Wall
curl http://localhost:8000/api/v1/aionx/cortex/snapshot

# Fire an Event Fabric cascade manually (e.g. test CLIENT_SIGNED)
curl -X POST http://localhost:8000/api/v1/aionx/cortex/event \
  -H "Content-Type: application/json" \
  -d '{"event_type":"CLIENT_SIGNED","client_id":"<uuid>"}'
```

**Verify heartbeat is live:**

```bash
curl http://localhost:8000/api/v1/scheduler/jobs | grep aionx
```

Expected: 8 `aionx_*` jobs listed with next_run times.

**Event Fabric cascades wired:**
- `CLIENT_SIGNED` → twin + decision + delivery council + ownership + notify
- `LEAD_REPLIED` → decision + twin interaction + speed-to-lead queue
- `MISSION_FAILED` → autopsy + convergence council + decision + notify
- `CHURN_RISK_DETECTED` → convergence council + decision + notify
- `SENTINEL_STRONG_SIGNAL` → provider council + decision

---

## CAPTAIN VERIFICATION

After successful deployment, Captain can access:

1. **Wisdom Index:** `GET /api/v1/aionx/wisdom`
2. **Glass Wall:** `GET /api/v1/aionx/decisions/genealogy`
3. **Council Feed:** `GET /api/v1/aionx/convergence/session/{id}/feed`
4. **Digital Twins:** `GET /api/v1/aionx/digital-twin/{client_id}`
5. **Threats:** `GET /api/v1/aionx/sentinel/threats`
