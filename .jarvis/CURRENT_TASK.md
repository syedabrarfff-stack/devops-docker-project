# CURRENT TASK
_Update this file every session. Any model reads this and continues instantly._

## System Phase
**Phase 2 — Revenue Acquisition**
Infrastructure is complete. The mission now is: get the first 10 paying clients.

## Active Blockers (Captain Must Do First)
These are NOT code tasks. They require AWS console / DNS access:
1. IAM: Attach AdministratorAccess to JarvisGitHubActionsRole
2. Terraform: `cd infra/terraform && terraform init && terraform apply`
3. DNS: CNAME aliyarsolutions.com → ALB DNS output from Terraform
4. Merge PR #1 on GitHub → auto-triggers ECS blue/green deploy
5. AWS SES: request production access (remove sandbox)
6. AWS Secrets Manager: set STRIPE_WEBHOOK_SECRET
7. Post-deploy: register Telegram webhook

## Next Development Tasks (For Any Model)

### Priority 1 — Executive Intelligence Layer
**What:** Morning briefing system that proactively surfaces what matters
**Why:** Captain needs a single daily digest instead of checking multiple routes
**How to build:**
- Route: GET /api/v1/briefing/morning-ai (already exists — may need enhancement)
- Check: backend/app/api/v1/routes/briefing.py for current implementation
- Scheduled job: daily_morning_briefing at 07:00 UTC (already exists in scheduler)
- Output should include: hot leads (trust_score ≥ 60), overdue proposals, pending contracts, pipeline value, system health, top actions for the day
- Delivery: Telegram + WebSocket push to Captain

### Priority 2 — Opportunity Radar
**What:** Overnight scanner that finds top 5 "ready to contact" leads each morning
**Why:** Prevents hot leads from going cold unnoticed
**How to build:**
- New scheduled job: opportunity_radar at 06:00 UTC
- Logic: query leads where trust_score ≥ 40, no outreach in 7 days, not in active sequence
- Generate personalized brief angle for each (POST /trust/briefs/generate)
- Package as morning radar report → Captain (Telegram + WebSocket)
- File to add to: backend/app/services/scheduler/ or backend/app/api/v1/routes/intelligence.py

### Priority 3 — War Room Dashboard
**What:** Frontend view showing live pipeline, MRR, trust scores, agent activity
**Why:** Captain needs a single-screen command center
**Where:**
- New component: frontend/src/components/dashboard/WarRoom.jsx
- Register in: frontend/src/App.jsx VIEWS map + frontend/src/components/layout/Sidebar.jsx NAV
- API helpers: frontend/src/services/api.js
- Data sources: GET /revenue/pipeline, GET /revenue/mrr, GET /leads, GET /trust/score/{id}

### Priority 4 — First Client Activation Script ✅ DONE
`scripts/first_client_activation.py` — complete, all imports verified clean. Run it after Captain unblocks infrastructure.

### Priority 5 — CSV Lead Import ✅ DONE
`POST /api/v1/leads/import-csv` + `GET /api/v1/leads/csv-template` + LeadsDashboard "📥 Import CSV" modal.
Captain can now upload Apollo/LinkedIn CSV exports to bulk-seed the pipeline.

### Priority 6 — Outreach Campaign Launcher
**What:** One-click "Launch Campaign" for a batch of hot leads — generates personalized trust brief + queues outreach email for each
**Why:** Current flow is manual per-lead. Captain needs to arm 20+ leads for outreach in one action
**How:**
- Backend: `POST /api/v1/outreach/campaign` — accepts list of lead_ids, generates trust brief for each, queues outreach
- Frontend: Add "Launch Campaign" button to LeadsDashboard (appears when 2+ leads selected via checkboxes)
- Checkbox multi-select state on LeadRow
- Campaign result modal showing queued count

### Priority 7 — Proposal Preview in Approvals Queue
**What:** When a proposal is queued for Captain approval, show the rendered proposal content inline (not just metadata)
**Why:** Captain currently approves blind — can't see what the proposal says before approving
**How:**
- Backend: `GET /api/v1/proposals/{id}/preview` — return full rendered markdown/HTML
- Frontend: Expand ApprovalQueue card to show proposal content inline or in modal
- Route: approvals.py + proposals route

## Completed This Session
- [x] Priority 1 — Executive Intelligence Layer (grounded morning briefing with live DB metrics)
- [x] Priority 2 — Opportunity Radar (scheduler job at 06:00 UTC + manual trigger endpoint + frontend panel)
- [x] Priority 3 — War Room HQ Dashboard (/control-room/war-room-hq — live pipeline command centre)
- [x] Priority 4 — CSV Lead Import (POST /leads/import-csv + GET /leads/csv-template + LeadsDashboard modal)
- [x] Priority 6 — Outreach Campaign Launcher (multi-select on LeadsDashboard + POST /outreach/launch-campaign)
- [x] Priority 7 — Proposal Preview in Approvals Queue (GET /proposals/{id}/preview + inline ProposalPreviewPanel)
- [x] Priority 8 — Contract Generation from Proposal (POST /proposals/{id}/generate-contract + Approvals UI button)
- [x] Priority 9 — Contracts Dashboard Tab (ContractsTab in GovernanceDashboard + POST /governance/contracts/{id}/send-email)
- [x] VS Code full operational audit + all fixes applied (see audit report in session)
- [x] VS Code deep integration: REST Client environments, compound launch, React snippets, pyrightconfig, .prettierrc
- [x] NVIDIA SSL fix: verify=False on httpx client for TLS inspection proxy in cloud containers
- [x] Full repository audit (57 routes, 35 models, 36 service directories, 411 endpoints)
- [x] API_INVENTORY.md — completely rewritten with accurate data (NVIDIA NIM routing, 15 task types)

## Previously Completed (Prior Sessions)
- [x] Security hardening: rate limiting, JWT auth, N+1 fixes, DB indexes, HSTS
- [x] Auto-delivery: invoices, proposals, demos, client welcome emails
- [x] Contract system: model + migration + AI generator + routes + auto-trigger
- [x] Trust Engine: executive briefs, engagement scoring, referral engine
- [x] VS Code HQ: workspace file, 11 memory files, multi-model council

## How to Continue From Any Model
1. Read `.jarvis/CURRENT_STATE.md` — system status and blockers
2. Read `.jarvis/CURRENT_TASK.md` (this file) — what to build next
3. Read `.jarvis/API_INVENTORY.md` — all routes and AI routing
4. Read `.jarvis/DECISIONS.md` — architectural decisions (WHY)
5. Read `.jarvis/LESSONS.md` — what not to do
6. Check git log: `git log --oneline -10` for recent commits
7. Pick next priority from "Next Development Tasks" above
8. Build, commit with `feat(phase-2): description`, push

## Conventions (Must Follow)
- All new routes: register in `backend/app/api/v1/__init__.py`
- All new models: import in `backend/app/models/__init__.py`
- All new views: add to `frontend/src/App.jsx` + `Sidebar.jsx`
- All new API calls: add helper to `frontend/src/services/api.js`
- Next migration number: **0030** (down_revision = '0029_trust_engine')
- Branch: `claude/jarvis-cans-api-integration-ZThTD`
- Commit format: `feat(phase-2): short description`
- NEVER commit .env, terraform.tfvars, .htpasswd
- NEVER put secrets in code
- NEVER use debug=True in production
