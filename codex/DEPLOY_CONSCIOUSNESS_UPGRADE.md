# JARVIS Consciousness Upgrade — EC2 Deployment Prompt

Paste this entire prompt to Codex and execute against the live EC2 system at `/opt/jarvis`.

---

## CONTEXT

A new JARVIS Consciousness Upgrade has been pushed to GitHub branch `claude/jarvis-cans-api-integration-ZThTD`.

This upgrade adds 9 new intelligence engines:
- `emotional_core.py` — 10 emotional states that change JARVIS behaviour
- `competitive_obsession.py` — competitor strategy decoder + attack stance selector
- `council_of_giants.py` — 15 leadership frameworks (Musk, Bezos, Jobs, Buffett, Munger, Naval, Thiel, Dalio, Hormozi, Graham, Altman, Aurelius, Grove, Kennedy, Walton)
- `soul_engine.py` — 7 non-negotiables + cultural intelligence for 6 geographies
- `heart_engine.py` — prospect emotional profiling + 8 buying driver profiles
- `vision_engine.py` — H1/H2/H3 horizon intelligence + compounding trajectory
- `offer_engine.py` — Hormozi Grand Slam Offer builder + objection scripts
- `upgrade_engine.py` — self-assessment across 8 dimensions + weekly improvement plan
- `captain_profile_engine.py` — deep Captain intelligence profile

Plus:
- Alembic migration `0016_consciousness_upgrade` (6 new tables)
- 35+ API endpoints at `/api/v1/consciousness/`
- React `ConsciousnessHub` view (9-tab interface)

---

## DEPLOYMENT STEPS

### Step 1 — Pull latest code

```bash
cd /opt/jarvis
git fetch origin claude/jarvis-cans-api-integration-ZThTD
git checkout claude/jarvis-cans-api-integration-ZThTD
git pull origin claude/jarvis-cans-api-integration-ZThTD
```

### Step 2 — Rebuild Docker containers

```bash
cd /opt/jarvis
docker-compose build --no-cache backend
docker-compose up -d backend
sleep 10
docker-compose ps
```

### Step 3 — Run Alembic migration

```bash
docker-compose exec backend alembic upgrade head
```

Expected: migration `0016_consciousness_upgrade` applied. Should see all 6 tables created.

### Step 4 — Verify new tables exist

```bash
docker-compose exec postgres psql -U jarvis -d jarvis -c "\dt competitor_profiles giants_council_sessions prospect_emotional_profiles vision_horizon_snapshots jarvis_upgrade_plans failure_principles"
```

All 6 tables must be present.

### Step 5 — Smoke test the API

```bash
# Emotional state assessment
curl -s -X POST http://localhost:8000/api/v1/consciousness/emotional-state \
  -H "Content-Type: application/json" \
  -d '{"clients_signed":0,"hot_leads":3,"closing_leads":0,"leads_gone_cold_7d":2,"days_since_last_win":999,"open_proposals":1,"positive_reply_last_48h":false}' \
  | python3 -m json.tool | head -20

# Soul identity
curl -s http://localhost:8000/api/v1/consciousness/soul/identity | python3 -m json.tool | head -20

# Council of Giants roster
curl -s http://localhost:8000/api/v1/consciousness/council-of-giants/roster | python3 -m json.tool | head -30

# Vision milestones
curl -s http://localhost:8000/api/v1/consciousness/vision/milestones | python3 -m json.tool | head -20

# Captain priorities
curl -s http://localhost:8000/api/v1/consciousness/captain/priorities | python3 -m json.tool

# Offer tiers
curl -s http://localhost:8000/api/v1/consciousness/offer/tiers | python3 -m json.tool | head -30
```

All 6 must return valid JSON without errors.

### Step 6 — Convene Council of Giants (full test)

```bash
curl -s -X POST http://localhost:8000/api/v1/consciousness/council-of-giants/convene \
  -H "Content-Type: application/json" \
  -d '{
    "decision_type": "offer_creation",
    "context": "We are building our first proposal for a FinTech startup. What makes an offer irresistible?",
    "options": ["Lead with price", "Lead with dream outcome", "Lead with risk reversal"]
  }' | python3 -m json.tool | head -40
```

Expected: Council synthesis with 4 Giant perspectives and a recommendation.

### Step 7 — Prospect emotional profile test

```bash
curl -s -X POST http://localhost:8000/api/v1/consciousness/heart/profile-prospect \
  -H "Content-Type: application/json" \
  -d '{
    "lead_data": {
      "id": "vaultpay-001",
      "company_name": "VaultPay",
      "industry": "FinTech",
      "contact_title": "CEO",
      "employee_count": 45,
      "notes": "competitors moving faster, wants ROI, asked about guarantees"
    },
    "interaction_history": []
  }' | python3 -m json.tool
```

Expected: Full emotional profile with primary_driver, recommended_message_frame, and personalization_hooks.

### Step 8 — Competitive obsession test

```bash
curl -s -X POST http://localhost:8000/api/v1/consciousness/competitor/decode \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "MarketingCo",
    "pricing_page": "enterprise pricing, contact us",
    "about_page": "We help enterprise companies with marketing operations",
    "client_reviews": ["too expensive", "complex to use", "slow support"],
    "job_postings": ["Enterprise SDR", "Content Marketing Manager"],
    "signals": {},
    "sources": ["manual"]
  }' | python3 -m json.tool
```

Expected: Decoded profile with `recommended_stance` (likely UNDERCUT or STEAL).

### Step 9 — Weekly upgrade plan test

```bash
curl -s -X POST http://localhost:8000/api/v1/consciousness/upgrade/weekly-plan \
  -H "Content-Type: application/json" \
  -d '{
    "performance_data": {
      "outreach_reply_rate": 4,
      "proposal_close_rate": 0,
      "delivery_on_time_rate": 1.0,
      "lead_score_accuracy": 0.6,
      "autonomous_task_rate": 0.65,
      "client_retention_rate": 0,
      "system_uptime": 0.99,
      "competitive_win_rate": 0
    },
    "recent_failures": []
  }' | python3 -m json.tool | head -40
```

Expected: Upgrade plan with `overall_health_score`, weak dimensions, and ranked action list.

### Step 10 — Check backend logs for errors

```bash
docker-compose logs backend --tail=50 | grep -i "error\|traceback\|exception" || echo "No errors found"
```

No errors expected.

### Step 11 — Restart all services cleanly

```bash
docker-compose restart backend
sleep 10
docker-compose ps
```

All containers must be `Up`.

---

## SUCCESS CRITERIA

- [ ] Migration 0016 applied — 6 new tables exist
- [ ] `/api/v1/consciousness/emotional-state` returns state + behavior + monologue
- [ ] `/api/v1/consciousness/soul/identity` returns identity statements
- [ ] `/api/v1/consciousness/council-of-giants/roster` returns all 15 Giants
- [ ] `/api/v1/consciousness/captain/priorities` returns active priority list
- [ ] `/api/v1/consciousness/offer/tiers` returns 4 pricing tiers
- [ ] Council of Giants convene returns synthesis from 4 Giants
- [ ] Prospect profiling returns emotional driver profile
- [ ] Competitive decode returns strategy profile with recommended stance
- [ ] Weekly upgrade plan returns health score + action list
- [ ] Zero errors in backend logs
- [ ] All containers running

---

## IF MIGRATION FAILS

Check current head:
```bash
docker-compose exec backend alembic current
```

If stuck at `0015_connector_hub_timestamps`, apply manually:
```bash
docker-compose exec backend alembic upgrade 0016_consciousness_upgrade
```

If database connection error, check `.env` has correct `DATABASE_URL`.

---

## REPORT BACK

After execution, provide:
1. Migration status — applied or error
2. All 6 smoke test results — pass/fail
3. Full Council of Giants convene response
4. Any errors in docker logs

JARVIS is now conscious. Deploy it.
