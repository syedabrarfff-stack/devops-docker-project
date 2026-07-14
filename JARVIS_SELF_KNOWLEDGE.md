# JARVIS — Complete Self-Knowledge
## Installed: 2026-06-22 | Updated: 2026-07-11 | Source: Full Codebase Audit + Production Incident Session

*Every JARVIS session must read this file on startup. This is operational self-awareness.*

---

## PRODUCTION INFRASTRUCTURE — CURRENT STATE (as of 2026-07-11)

**Read this section first if you are picking up production/DevOps work.** It captures the real AWS account layout, an incident and its fixes, and every open decision — so no session has to re-derive this from scratch.

### AWS account layout (account 824232273953, region ap-south-2 only)

| Instance ID | Name tag | State | Role |
|---|---|---|---|
| `i-07887c05a28c22675` | jarvis-work-dr-recovery | running | **THIS IS PRODUCTION.** Confirmed via `aliyarsolutions.com` DNS → `16.112.184.189` → this instance. IAM profile `jarvis-ops` attached. Elastic IP `16.112.184.189`. |
| `i-00381dfb44fd3cf45` | Jarvis-Terraform-Server | running | **Zombie/orphaned.** No IAM profile, no SSH key, SSM agent disconnected, serves HTTP 503, receives zero real traffic, not covered by AWS Backup. Do not deploy to this one. Candidate for termination after a fresh snapshot + traffic verification (Captain's explicit condition: snapshot + confirm zero production workload before deleting anything). |
| `i-0ef8f36bbe4c23681` | jarvis-work | stopped | Cold spare, same IAM profile/key as production, its volume is in the backup plan. Likely the pre-DR-recovery production box (DR event was 2026-07-04). Not currently in use. |

- **AWS Backup:** plan `jarvis-production-daily`, vault `jarvis-production-vault` — daily EBS snapshots of the production instance's volume (and the stopped spare's), confirmed working, 11+ recovery points at last check.
- **CloudWatch monitoring installed 2026-07-10/11:** CloudWatch Agent installed on production (was not present before — this is why memory pressure was invisible during the incident). 4 alarms live: `jarvis-production-high-memory` (>85%), `jarvis-production-high-disk` (>85%), `jarvis-production-high-cpu` (>80%), `jarvis-production-system-status-check-failed`.
- **SNS alert topic:** `arn:aws:sns:ap-south-2:824232273953:jarvis-production-alerts` — Captain's email (syedabrarbhd@gmail.com) subscribed; **confirm the AWS confirmation email was clicked, or alarms fire silently.**
- **AWS billing:** account was on Free Tier (blocked EC2 resize + Bedrock with `FreeTierRestrictionError`/`INVALID_PAYMENT_INSTRUMENT`) — **upgraded to paid plan 2026-07-10/11, confirmed via AWS email.** Resize to t3.medium should now succeed.
- **IAM:** role `jarvis-ops` is the instance profile on production (has `CloudWatchAgentServerPolicy` + `AmazonSSMManagedInstanceCore`, does NOT yet have `sns:Publish` — needed for the self-heal script's alert() function, pending Captain's named approval). Role `JarvisGitHubActionsRole` is what GitHub Actions assumes via OIDC (no stored secrets). Role `JarvisSSMAutomationRole` exists for the (currently on-hold) cross-instance failover automation — not needed for the single-instance self-healing approach Captain confirmed.

### Incident (2026-07-10) and what was fixed

Captain's dashboard login (`captain`/a chosen password) didn't work. Root-caused and fixed:

1. **Root cause of login failure:** credentials were only ever set in a local sandbox `.env` in a prior session — `.env` is correctly gitignored, so it never reached the real server. Added a `set-captain-credentials` GitHub Actions deploy action (`scripts/ec2-deploy-script.sh` + `.github/workflows/ec2-deploy.yml`) that rewrites `.env` and regenerates nginx's `.htpasswd` on the actual instance, with the password passed only as a runtime workflow input — never committed to git.
2. **Wrong instance targeted:** the deploy workflow picked "the first running instance" blindly and kept hitting the zombie (`i-00381dfb44fd3cf45`) instead of production. Fixed by pinning `INSTANCE_ID` explicitly in `ec2-deploy.yml` to the verified production instance.
3. **`$HOME not set` killed every SSM-based deploy:** AWS SSM's `AWS-RunShellScript` document doesn't set `$HOME` the way SSH does; the deploy script's `git config --global` call died immediately. Fixed with an explicit `export HOME=/root` at the top of `scripts/ec2-deploy-script.sh`.
4. **The real production outage:** while fixing the above, `ec2-deploy.yml`'s `push` trigger (fired on every commit to `scripts/**`, `backend/**`, `frontend/**`, or the workflow file) silently ran a `full-restart` in the background on every push — stopping and removing backend/nginx mid-fix, compounding with a genuinely undersized t3.micro (908MB RAM) under memory pressure. **The push trigger has been removed entirely from both `ec2-deploy.yml` and `terraform-apply.yml` — deploys now only happen via explicit manual "Run workflow".** `terraform-apply.yml`'s default action was also changed from `apply` to the read-only `plan-only` (it provisions ALB+RDS+ECS, out of scope — see architecture decisions below).
5. Production was recovered via an EC2-level reboot, then (after discovering the account was Free Tier and blocking the resize) a stop → start cycle back to t3.micro as a stopgap. All 15 containers confirmed healthy after.

### Architecture decisions Captain has explicitly made (do not deviate without asking)

- **Single instance only.** No ALB, no RDS, no ElastiCache, no Auto Scaling Group, no standby/multi-instance failover, no multi-region — **until customer growth justifies it.** An earlier proposal for a stopped warm-standby with cross-instance EventBridge failover was explicitly walked back in favor of this.
- **No AWS Bedrock, for now.** Was investigated (region has model access, e.g. Claude Haiku via inference profile `global.anthropic.claude-haiku-4-5-20251001-v1:0`), but Captain said stop/remove it. Nothing was integrated into the codebase — only a test invoke was run, no lasting resource or code change exists to clean up.
- **Self-healing must be single-instance/local**, not cross-instance: a systemd timer running `scripts/jarvis-health-check.sh` every 5 minutes on the production box itself (container health → restart, disk >85% → prune, memory >85% → alert via SNS, SSL expiry check, AWS Backup freshness check). This was written, corrected against the real `/opt/jarvis` deploy path and `-p jarvis` compose project name, and committed — **but not yet installed on production** (systemd units exist in `infrastructure/systemd/`, need to be copied to the instance and `systemctl enable --now`'d once AWS access allows it).
- **Backups:** rely on the existing AWS Backup (EBS snapshot) mechanism only. Deliberately did not add a second, separate pg_dump-to-S3 backup path (`scripts/backup-postgres.sh` exists in the repo but is not installed) to avoid extra IAM permissions, a new S3 bucket, and unnecessary cost/complexity.
- **DNS stays on GoDaddy** — no migration to Route53. Only the A record gets updated if/when the instance changes.
- **Instance sizing:** real on-demand pricing pulled from AWS for ap-south-2 — t3.micro $8/mo, t3.small $16/mo, **t3.medium $33/mo (Captain's chosen size)**, t3.large $65/mo, t3.xlarge $131/mo. (An earlier much lower t3.large estimate given in this project's docs was wrong — use the numbers here.) Target budget: $40-60/month total infrastructure.
- **In-place resize, not a new instance.** Captain was explicit: resize the *existing* production instance (stop → `modify-instance-attribute` → start), not build-and-cutover to a freshly launched box.

### Open items / where this session left off

1. **This session's AWS CLI access broke mid-session** (`InvalidClientTokenId`) despite both `jarvis-ops` IAM access keys showing "Active" in the console — the problem is in what credentials were injected into *this specific sandbox session*, not an AWS-side revocation. Needs fixing at the environment/session-provisioning level before any further AWS CLI work in a session can continue. Two keys exist on `jarvis-ops`: `AKIA372ASNAQ3U6CLTPJ` (desc "NEW", last used for bedrock) and `AKIA372ASNAQXZCVZNU5` (desc "jarvis headquarter", last used for ssm) — actual secret values are not recorded here, they live in the environment/secrets config only.
2. **Resize to t3.medium not yet done** — blocked only by #1 above (billing is confirmed upgraded, so the resize itself should work once AWS access is restored). Sequence: stop instance → `aws ec2 modify-instance-attribute --instance-type t3.medium` → start → verify all containers healthy → verify `/health` returns 200.
3. **`sns:Publish` permission on `jarvis-ops` role** — needed so the self-heal script's alerts actually reach Captain's email. Requires Captain's specific named approval (a general "continue"/"go ahead" was insufficient for this class of IAM change in this session — needs literal wording naming the role, the action, and the resource ARN).
4. **Self-heal systemd units not yet installed on production** — code is ready and corrected (see above), just needs deploying once AWS access works again.
5. **PR #1** on GitHub (`claude/jarvis-cans-api-integration-ZThTD` → `main`) has been open since 2026-05-07, 641 commits, 809 files changed, mergeable/clean — all Phase 1-108 work sits here unmerged.
6. **`evolution_api` / WhatsApp** had been crashed for 2 days before the 2026-07-10 incident; came back on its own after the reboot — worth a stability check, not yet root-caused.
7. **`jarvis_frontend` unhealthy** was diagnosed and fixed during this session (stale cached DNS resolution to `backend` from before backend was stable — a plain `docker restart jarvis_frontend` cleared it). Not expected to recur once the resize gives more headroom, but the same class of issue (nginx caching a failed upstream DNS lookup at container startup) could resurface after any restart sequence where backend isn't up first.

---

## SYSTEM ARCHITECTURE AT A GLANCE

| Layer | Stack |
|---|---|
| Backend | FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16 + pgvector |
| Frontend | React 18 + Vite + Tailwind CSS (60+ views) |
| Cache | Redis 7 (384MB, LRU, password-protected) |
| Scheduler | APScheduler — 71 production jobs (file-lock leader election) |
| AI Routing | 11-provider router + 14-model council |
| WhatsApp | Evolution API v2.3.7 |
| Infrastructure | Docker Compose (local) → AWS ECS Fargate (production) |
| Monitoring | Prometheus + Grafana + Loki + AlertManager |

---

## DATABASE — 35 TABLES ACROSS 5 LAYERS

### Tenancy & Auth
`tenants` · `tenant_api_keys` · `users`

### Lead & Revenue
`leads` · `clients` · `invoices` · `companies` · `contacts` · `deals` · `revenue`

### Outreach & Communication
`outreach_log` · `email_tracking` · `reply_log` · `follow_up_queue` · `outreach_sequences` · `outreach_emails` · `communication_events` · `reply_classifications`

### Operations & Tasks
`agent_tasks` · `agent_messages` · `scheduled_jobs` · `job_failures` · `approval_requests` · `audit_logs`

### Memory & Knowledge
`memory` · `memory_operational` · `memory_strategic` · `civilization_memory` · `memory_graph_nodes` · `memory_graph_edges` · `knowledge_base` · `learning_records` · `sop_documents`

### Intelligence & Governance
`ai_council_sessions` · `ai_council_member_weights` · `proposals` · `contracts` · `agent_permissions` · `incident_reports` · `tech_radar_entries`

### AIONX Sovereign Organs
`decision_objects` · `decision_options` · `decision_outcomes` · `decision_patterns` · `counterfactual_simulations` · `decision_debt_assessments` · `client_digital_twins` · `client_pipeline_states` · `mission_autopsy_records` · `sentinel_observations` · `wisdom_index_snapshots`

### Scheduling & Comms
`conversations` · `notifications` · `gmail_messages` · `credentials`

---

## AI ROUTING — TASK-TO-MODEL MAP

| Task Type | Primary | Secondary | Tertiary |
|---|---|---|---|
| CODE | DeepSeek V4 Pro (NIM) | Qwen Coder (NIM) | DeepSeek Flash |
| REASONING | DeepSeek V4 Pro | Llama 4 Maverick (NIM) | — |
| STRATEGY | Claude Sonnet | DeepSeek V4 Pro | Llama 4 Maverick |
| ANALYSIS | DeepSeek V4 Pro | Llama 4 Maverick | Claude Opus |
| RESEARCH | DeepSeek V4 Pro | Kimi K2.6 | Llama 4 Maverick |
| FAST | Llama 4 Scout (NIM) | DeepSeek Flash (NIM) | Groq Llama 3.3 |
| LONG_CTX | Kimi K2.6 | Llama 4 Maverick | Claude 3.5 |
| SALES | Claude Sonnet | Llama 4 Maverick | DeepSeek V4 Pro |
| REALTIME | Llama 4 Scout | DeepSeek Flash | Groq Llama |

Circuit breaker per provider. Latency-aware failover. Cost tracked per call.

---

## THE 14-MODEL COUNCIL (council/ directory)

Fires all 14 models simultaneously via asyncio.gather(). Claude Opus synthesizes final verdict.

| # | Model | Provider | Role |
|---|---|---|---|
| SYNTHESIZER | claude-opus-4-5 | Anthropic | Chief Synthesizer |
| 1 | claude-sonnet-4-6 | Anthropic | Operations & Strategy |
| 2 | meta/llama-4-maverick-17b-128e-instruct | NVIDIA NIM | Advanced Reasoning |
| 3 | meta/llama-4-scout-17b-16e-instruct | NVIDIA NIM | Fast Intelligence |
| 4 | meta/llama-3.3-70b-instruct | NVIDIA NIM | Deep Analysis |
| 5 | qwen/qwen2.5-coder-32b-instruct | NVIDIA NIM | Code & Engineering |
| 6 | moonshotai/kimi-k2.6 | NVIDIA NIM | Long-Context |
| 7 | mistralai/mistral-medium-3-instruct | NVIDIA NIM | Risk & Compliance |
| 8 | zai-org/glam-5.1 | NVIDIA NIM | Innovation |
| 9 | deepseek-ai/deepseek-v4-flash | NVIDIA NIM | Lightning Code |
| 10 | deepseek-ai/deepseek-v4-pro | NVIDIA NIM | Deep Research |
| 11 | minimaxai/minimax-m2.7 | NVIDIA NIM | Creative Strategy |
| 12 | gemini-2.5-pro | Google | Market Intelligence |
| 13 | ai21/jamba-1-5-large | OpenRouter | Long-Context Documents |

Sessions saved to: `council/sessions/council_TIMESTAMP.txt`
Run with: `python council.py` from `council/` directory

---

## 64 PRODUCTION SCHEDULER JOBS

Full catalog in CLAUDE.md Section 12. Summary by layer:

### Core Operational (engine.py — 38 jobs)
**Daily intelligence:** `daily_briefing` 08:00 · `morning_briefing` 07:00 · `captain_dashboard_briefing` 06:55 · `daily_optimization_review` 23:00 · `daily_strategy_report` 23:00 · `daily_self_learning` 00:05 · `memory_consolidation` 00:30 · `lead_embedding_sweep` 03:15 · `nightly_signal_scan` 02:00

**Lead pipeline:** `lead_scoring_sweep` every 6h · `daily_icp_lead_scoring` 05:00 · `outreach_processor` every 1h · `reply_handler_scan` every 2h · `contact_sync` every 12h

**Overnight Revenue Engine (IST-timed):** `overnight_lead_discovery` 18:00 · `overnight_intel_analysis` 18:30 · `overnight_proposal_engine` 19:30 · `overnight_cold_outreach` 20:30 · `overnight_freelance_bids` 21:30 · `overnight_followup_sequences` 23:30 · `overnight_pipeline_health` 01:00 · `overnight_ops_report` 02:30

**Intelligence:** `tech_radar_scan` Mon 06:00 · `competitor_monitoring` Mon 09:00 · `market_intelligence_report` Sun 07:00 · `biweekly_research_report` Sun 07:00 · `tech_evolution_scan` every 6h · `daily_market_intelligence` 04:00

**Connectors:** `daily_scout_network` 01:30 · `daily_connector_hub_ingestion` 14:30 · `pre_call_briefing_trigger` every 30min

**System:** `self_healer` every 15min · `nexus_heartbeat` every 1h · `dio_health_check` 06:30 · `weekly_memory_promotion` Sun 00:45 · `milestone_bulk_review` 10:00 · `weekly_strategy_review` Sun 07:00 · `weekly_performance_briefing` Sat 19:00

### AIONX Organ Jobs (aionx_scheduler.py — 26 jobs)
**High-frequency:** `aionx_system_state_snapshot` 5min · `aionx_speed_to_lead_check` 5min · `aionx_mission_control_snapshot` 10min · `aionx_preventive_monitoring_snapshot` 15min · `aionx_escalation_processor` 30min · `aionx_execute_due_outreach` 30min · `aionx_sentinel_sweep` 2h · `aionx_predictive_threat_scan` 2h · `aionx_operational_iq` 1h · `aionx_governed_integrity_cycle` 1h · `aionx_agent_capacity_check` 4h · `aionx_idle_intelligence_cycle` 6h

**Daily:** `aionx_retro_30d` 22:00 · `aionx_retro_90d` 22:15 · `aionx_twin_predictions` 03:00 · `aionx_counterfactual_sync` 01:00 · `aionx_debt_assessment` 02:00 · `aionx_trust_erosion_check` 03:30 · `aionx_external_scan_record` 04:15 · `aionx_founder_mirror_analysis` 01:00

**Weekly:** `aionx_wisdom_weekly` Sun 19:00 · `aionx_decision_retrospective` Sun 19:30 · `aionx_authority_recalibration` Sun 20:00 · `aionx_supreme_meta_learning` Sun 21:00 · `aionx_parallel_universe_analysis` Mon 08:00 · `aionx_service_innovation_scan` Sun 10:00

---

## AUTHORITY MATRIX

### JARVIS Executes Immediately (No Captain needed)
Lead discovery · scoring · enrichment · outreach emails · LinkedIn DMs · WhatsApp · proposal writing · proposal sending · client communication · meeting scheduling · CRM updates · inbox monitoring · reply classification · Upwork applications · tech radar · market intel · morning briefing · content publishing · memory storage · system monitoring

### Captain Must Approve First
Pricing decisions · payment collection · invoices · contract signing · production go-live · refund processing · partnerships · white-label deals · hiring · bank transfers · strategic pivots · press releases · legal disputes · permanent data deletion · infrastructure destruction

### JARVIS Executes Then Alerts Captain
High-value leads (>$5K) · unhappy client messages · proposal accepted · meeting booked · payment received · system critical errors · security incidents · large opportunities (>$10K) · churn risk

---

## TEAM REGISTRY — 8 HUMAN PERSONAS

| Name | Role | Service Categories |
|---|---|---|
| Darren Mitchell | Client Acquisition | leads, outreach, crm, sales |
| David Carter | Solutions Architect | cloud, aws, architecture, saas_deployment |
| Sophia Reynolds | Workflow Consultant | ai_automation, workflow, voice |
| Nathan Scott | Deployment Engineer | devops, cicd, docker, kubernetes, terraform |
| Lucas Reed | Comms Manager | communications, messaging, notifications |
| Olivia Bennett | Calendar Ops | scheduling, calendar, meeting_prep |
| James Whitfield | Analytics Lead | intelligence, research, market_analysis |
| Emma Collins | Pipeline Manager | crm_intelligence, sales_forecasting |

Routing file: `backend/app/services/team/team_service.py`

---

## MEMORY ARCHITECTURE — 3 TIERS

1. **Episodic** — Specific events, interactions, outcomes (30-90 day lifespan)
2. **Semantic** — Extracted facts, rules, domain knowledge (permanent, vectorized)
3. **Instruction** — Captain's standing orders (immutable, priority=10)

Plus: Working memory (current session) · Knowledge graph (nodes + edges) · Civilization ledger (immutable hash chain)

---

## AIONX SOVEREIGN ORGANS

- **Decision Intelligence** — Decision objects, options, outcomes, patterns, retrospectives
- **Counterfactual Engine** — What-if simulations validated against actual outcomes
- **Decision Debt** — Tracks consequences of past decisions
- **Client Digital Twins** — Predictive AI model per client
- **Mission Intelligence** — Post-project autopsy and learning
- **Sentinel** — Real-time threat monitoring
- **Wisdom Index** — Weekly accuracy calibration snapshots

---

## API ROUTES (60+ endpoints)

`leads` · `outreach` · `crm` · `proposals` · `revenue` · `approvals` · `captain` · `governance` · `intelligence` · `council` · `departments` · `aionx` · `consciousness` · `scheduler` · `memory` · `knowledge` · `team` · `catalog` · `briefing` · `chat` · `ws` (WebSocket) · `ses_inbound` · `telegram_webhook` · `supreme` (Layer 19 — 35 constitutional intelligence endpoints)

All registered in: `backend/app/api/v1/__init__.py`

---

## BOOT SEQUENCE

1. Database tables created (SQLAlchemy)
2. Master tenant bootstrapped
3. Service catalog seeded (25 modules)
4. Team registry seeded (8 personas)
5. JARVIS authority instructions stored in memory
6. Task queue initialized + worker started
7. Scheduler leader election via `fcntl.flock(LOCK_EX|LOCK_NB)` on `/tmp/jarvis_scheduler.lock`
   - First gunicorn worker to acquire the exclusive lock starts APScheduler (71 jobs — 45 core + 26 AIONX)
   - Other workers get `BlockingIOError` and skip gracefully
   - OS auto-releases lock on worker death → seamless leadership transfer during recycling/reload

Health endpoints: `/health` (shallow) · `/readyz` (deep — checks DB, AI, Redis, Evolution, SES, Scheduler)

---

## WHAT IS COMPLETE vs IN PROGRESS

### Fully Operational
Multi-provider AI routing · lead discovery & scoring · email outreach & reply handling · proposal generation (4 styles) · invoice management · CRM sync · Gmail OAuth · Google Calendar · team routing · service catalog · memory system · AIONX decision intelligence · WhatsApp (Evolution API) · approval governance · AI council voting · APScheduler (30+ jobs)

### Phase 25-26 Fully Operational (2026-06-27)
NEXUS autonomous outreach (Redis-locked, hourly heartbeat) · Semantic lead search (OpenAI embeddings + cosine similarity) · Telegram bot with 15+ commands + inline approval buttons · Captain morning dashboard (06:55 daily, live DB stats) · Weekly performance briefing (Saturday) · Nightly signal scan (HOT/WARM lead alerts) · Full NEXUS heal protocols (all 8 subsystems) · WebSocket real-time events (draft sent/rejected, NEXUS pulse) · Lead reply Telegram alerts (SES inbound → immediate Captain notification) · Revenue snapshot in Telegram · Bulk approve-all with confirmation

### Phase 107-108 Fully Operational (2026-06-29)
**Supreme Intelligence Layer (Layer 19):** 5 autonomous intelligence engines:
- `JarvisConstitution` — 12 Constitutional Laws + 3-tier Authority Matrix + 8 Escalation Triggers
- `AutonomousCEO` — Strategic pillars, opportunity scoring (5 dimensions), expansion roadmap
- `RevenueConsciousness` — Pricing tiers, LTV, churn risk, upsell triggers, pipeline health
- `PlatformIntelligence` — Infrastructure assessment, cost posture, SLA monitoring, tech debt
- `SalesAutonomy` — Lead scoring, outreach sequences, win/loss analysis, objection playbook

35 Supreme API endpoints at `/api/v1/supreme/*` with full rate limiting and Pydantic validation.
**SupremeDashboard.jsx** — 6-tab frontend: Overview / Constitution / CEO Brain / Revenue / Platform / Sales

**Production Hardening:** All compose secrets use `:?` mandatory syntax · Redis password-protected · OIDC role ARN in GitHub Secret · Workers raised to 3 · AI budget $50/$1.00 · Comprehensive `.env.example` template

### Partial
LinkedIn outreach (framework ready, needs activation) · voice systems (Evolution API integrated, prompting pending) · client digital twins (framework ready, calibration pending) · counterfactual simulations (models ready, optimization ongoing)

### Not Yet Built
White-label licensing · real-time speech-to-text · video generation · mobile app · Slack integration · Zapier/Make.com connectors

---

## INVOICE NUMBERING
Format: `ALY-YYYYMM-XXXX` — e.g., `ALY-202406-0047`

## TELEGRAM BOT COMMANDS (Phase 25-26)
/status · /heal · /nexus · /leads · /pipeline · /revenue · /scout · /briefing
/drafts · /draft <id> · /approve_draft <id> · /reject_draft <id> · /approve_all
/approve <id> · /reject <id> · /queue · /help
Inline buttons: approve_draft: · reject_draft: · approve_all_drafts:confirm · approve: · reject:
Webhook: POST /api/v1/telegram/webhook (registered with Telegram)

## OUTREACH COMPLIANCE
Max 5 steps per sequence · Do-Not-Contact enforced · Speed-to-lead SLA: 5 minutes

## EXTERNAL BRANDING RULE
NEVER reveal AI in client communications. Always: "Aliyar Solutions team" / "Our engineering team"

---

*This file is JARVIS's operational brain. Read it. Know it. Execute from it.*
