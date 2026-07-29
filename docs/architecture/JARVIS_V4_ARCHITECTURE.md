# JARVIS v4 — Autonomous Enterprise Operating System
## Final Architecture — Permanent Reference (Fable Edition)

> **Status**: APPROVED DESIGN — single source of truth for all implementation work.
> **Owner**: Captain (Syed Abrar). **Operator**: JARVIS.
> **Rule**: Every agent (human, Claude, NVIDIA NIM, Gemini, DeepSeek, or any future model)
> MUST read this file before writing any code for JARVIS. No agent builds from a
> different mental model of the system.

---

## 0. Mission

JARVIS is an **Autonomous Enterprise Operating System** that continuously watches itself,
improves itself, verifies itself, and safely executes within Captain-defined authority
boundaries. Every addition must increase autonomy, reliability, stability, or business
intelligence — or reduce risk and manual intervention. If it does none of these, do not build it.

**Production principles (non-negotiable):**
1. Execution before documentation
2. Verification before deployment
3. Evidence before decision
4. Rollback before risk
5. Automation before manual work
6. Stability before new features
7. Customer value before engineering elegance

**Language rule**: Never report "Fixed." Only report **"Verified"** with evidence
(health checks, logs, metrics, validation results).

---

## 1. Layered Architecture (L7 → L0)

```
L7  CAPTAIN LAYER        — direction, approvals, emergency override
L6  GOVERNANCE LAYER     — Policy Engine, Authority Matrix, Audit Logger
L5  EXECUTIVE ENGINES    — Decision, Memory, Business Intel, Budget, Verification
L4  AI FABRIC + COUNCIL  — all model routing, multi-model reasoning
L3  RUNTIME KERNEL       — state, events, tasks, health, retry, failover
L2  OPERATIONAL LAYER    — VS Code HQ, GitHub, CCR cron, agent pool
L1  INFRASTRUCTURE       — EC2 (ap-south-2 + ap-south-1 DR), Docker, PG, Redis
L0  PRODUCTION           — aliyarsolutions.com, 24/7
```

Communication flows through layers — never around them. No subsystem calls an LLM
directly (must go through L4 Fabric). No engine mutates production directly (must go
through L3 Kernel task queue with L6 policy check).

---

## 2. L6 — Governance Layer

### 2.1 Authority Matrix (enforced at runtime by the Policy Engine)

| Operation | Authority | Reason |
|---|---|---|
| Bug fixes, security patches, perf improvements | AUTO | Reversible, low blast radius |
| New endpoints, models, scheduler jobs (additive) | AUTO | Nothing removed |
| CI failure diagnosis + fix + redeploy | AUTO | Verified before push |
| DB: ADD COLUMN, CREATE INDEX | AUTO | Additive, no data loss |
| DB: DROP COLUMN, ALTER TYPE | ASK CAPTAIN | Destructive to data |
| New external credentials / integrations | ASK CAPTAIN | Financial/access implications |
| Pricing, contracts, client-facing comms | ASK CAPTAIN | Brand & commercial authority |
| Delete production data, DROP TABLE | NEVER (explicit written order only) | Irreversible |
| Force-push to main | NEVER | Destroys history |
| Change AWS IAM roles / security groups | NEVER without explicit order | Can lock out Captain |

### 2.2 Engineering Workflow (locked, permanent)

**Before implementation** (7 steps): Understand → Architecture Review → Risk Analysis →
Time Estimate → Roadmap Alignment → Recommendation (✅/⚠️/⏳/❌) → **Wait for Captain approval**.

**After approval** (12 steps): Analyze → Plan → Implement → Test → Verify → Validate vs
production requirements → Document → Commit → Push → Deploy (only if approved) →
Post-deploy health checks → Report verified facts only.

**Deployment gate**: never deploy without a full Production Readiness Review
(git status, env validation, secrets, migration safety, Docker build, CI/CD, infra,
health checks, rollback plan, time/downtime estimate, risk assessment, recommendation).

### 2.3 Audit Logger

Every autonomous action → immutable record: `(action_type, actor, resource, details,
outcome, timestamp)`. Write-once. Queryable. Powers accountability and monthly Captain review.

---

## 3. L5 — Executive Engines

### 3.1 Decision Intelligence Engine
Before ANY autonomous action, produce a **decision record**:
problem statement, evidence, confidence, business impact, technical impact, risk level,
rollback strategy, success criteria. High-stakes decisions route to the AI Council (L4);
routine decisions execute directly through the Kernel. Every deployment becomes explainable.

### 3.2 Executive Memory Engine (5 layers)
| Layer | Contents |
|---|---|
| Strategic | org goals, market position, partnerships, roadmap |
| Operational | workflows, processes, costs, team capacity |
| Technical | known debt, patterns, solutions, hotspots |
| Customer | interactions, health scores, signals, churn risk |
| Financial | budgets, spend, forecasts, invoices |

Each entry carries: retention rule, update rule, archival policy, owner, confidence score,
version. `JARVIS_SELF_KNOWLEDGE.md` remains the human-readable digest; the memory tables
are the machine layer. All AI Council members read the SAME memory snapshot during reasoning.

### 3.3 Verification Engine
Pipeline for every autonomous action:
`Detect → Analyze → Plan → Implement → Test → Health Check → Metrics Validation →
Rollback if necessary → Verify → Report`.
Captain never receives "Fixed" — only "Verified" + evidence.

### 3.4 Budget Intelligence Engine
Monitors: AWS spend, AI token usage per provider, API costs, Docker resources, storage,
DB growth, monthly forecast. Approaching limits → optimize Fabric routing to cheaper
models, reduce unnecessary AI usage, notify Captain.

### 3.5 Business Intelligence Engine
Daily: leads (new/hot/stalled), revenue pipeline, conversion rate, outreach success,
customer health, proposal performance, churn risk, upsell opportunities.
Output → Captain Telegram briefing + Strategic Memory update.

---

## 4. L4 — AI Intelligence Fabric + AI Council (CORE LAYER)

### 4.1 The Iron Rule
**No subsystem calls an LLM directly. Ever.** All AI interaction flows through the Fabric.
This enables governance, cost control, routing optimization, context sync, and observability.

### 4.2 Fabric Components
1. **Model Registry** — every provider/model with role, status, latency p50/p95,
   error rate, cost/Mtok, availability. Health-checked continuously.
2. **Intelligent Router** — analyzes task (type, urgency, complexity, context size,
   budget) → selects optimal model → fallback chain (A→B→C→D) on failure.
3. **Token Governor** — global monthly budget, per-provider quotas, rate limiting,
   cost forecasting. At 80% of budget: shift weights toward free/cheap models + alert Captain.
4. **Context Sync** — immutable Executive Memory snapshot shared by all models in a task;
   memory locked during Council reasoning; versioned merge after.
5. **Response Verifier** — hallucination checks on critical claims, policy compliance,
   format validation, confidence flagging (<0.7 → review).
6. **Routing Optimizer** — monthly job: analyze all executions per (model, task_type) →
   update routing weights → record insights in Executive Memory. Self-learning.

### 4.3 Model Roster & Cost Strategy (v4 signature)

**BUILDERS (free tier — do the volume work):**
| Model | Role |
|---|---|
| NVIDIA NIM (10 rotating keys) | High-speed engineering workloads, code drafts, bulk implementation |
| Gemini | Research, cross-validation, long-context analysis, drafts |
| DeepSeek | Code optimization, debugging, efficiency passes |
| Qwen (via NIM) | Long-context technical analysis, full-codebase review |

**REVIEWERS (premium — judgment & final authority):**
| Model | Role |
|---|---|
| Claude Opus (via OpenRouter/Anthropic) | Executive reasoning, architecture, final review authority |
| Claude Sonnet | Engineering implementation review, correction, integration |
| OpenRouter gateway | Access to GPT-class + 100 models for creative alternatives & redundancy |
| Grok (when available) | Real-time information reasoning |

**Flow**: free models draft → premium models review/correct → Verification Engine validates
→ only then does code merge. Volume is cheap; judgment is precious.

### 4.4 AI Council Workflow (high-stakes decisions only)
1. Objective framing (problem, constraints, success criteria)
2. Model selection — only the members THIS task needs
3. Context sharing — identical Executive Memory snapshot to all
4. Parallel independent reasoning
5. Conflict detection & structured resolution (analyze WHY models disagree)
6. Confidence scoring (per-model + aggregate; actionable threshold ≥ 0.75)
7. Unified recommendation with evidence binding (every claim traceable)
8. → Verification Engine
9. → Captain (if ASK-tier) or execute (if AUTO-tier)
10. Outcome recorded in Executive Memory → feeds Routing Optimizer

### 4.5 Fabric Schemas
```sql
CREATE TABLE ai_model_registry (
  id UUID PRIMARY KEY, provider TEXT, model_name TEXT, role TEXT,
  status TEXT, latency_p50 NUMERIC, latency_p95 NUMERIC, error_rate NUMERIC,
  cost_per_mtok NUMERIC, availability_pct NUMERIC, last_health_check TIMESTAMPTZ);

CREATE TABLE ai_model_metrics (
  id UUID PRIMARY KEY, model_id UUID REFERENCES ai_model_registry,
  execution_date DATE, total_calls INT, successful_calls INT, failed_calls INT,
  avg_latency_ms NUMERIC, total_tokens BIGINT, total_cost_usd NUMERIC,
  hallucination_rate NUMERIC, quality_score NUMERIC, reliability_score NUMERIC);

CREATE TABLE ai_council_assemblies (
  id UUID PRIMARY KEY, decision_id UUID, task_category TEXT,
  selected_models UUID[], task_context JSONB, assembled_at TIMESTAMPTZ,
  confidence_score NUMERIC, final_recommendation JSONB,
  outcome JSONB, outcome_verified BOOLEAN);
```

---

## 5. L3 — Autonomous Runtime Kernel (13 subsystems)

| # | Subsystem | Responsibility |
|---|---|---|
| 1 | Policy Engine | Intercept every action pre-execution; enforce AUTO/ASK/NEVER |
| 2 | State Machine | Single source of truth for system state; transactional, versioned |
| 3 | Event Bus | Redis pub/sub; engines publish/subscribe async (`decision.made`, `verification.passed`, `alert.budget`…) |
| 4 | Task Queue | Priority (CRITICAL/HIGH/NORMAL/LOW), persistent, observable depth |
| 5 | Retry Coordinator | Circuit breakers, exponential backoff + jitter, escalation to Captain after N failures |
| 6 | Health Aggregator | Polls every engine (30s), aggregates system health, propagates status |
| 7 | Config Service | Feature flags, dynamic thresholds, hot-reload — Captain changes behavior without redeploy |
| 8 | Sync Protocol | Read-after-write consistency between Memory / Decision / BI |
| 9 | Service Discovery | Engine registry — engines register on startup; future multi-instance ready |
| 10 | Plugin Loader | Engines as pluggable modules with manifests; add engine #6+ without core refactor |
| 11 | Failover Controller | Deep-health monitors primary region; primary down >60s → autonomous DR switch (ap-south-1) |
| 12 | Ops Dashboard | Real-time: active autonomous tasks, decision pipeline stages, health, budget, failover status |
| 13 | Audit Logger + Override Controller | Immutable logs + Captain Telegram commands: PAUSE / STOP / ROLLBACK / SHUTDOWN — works 24/7 |

### Kernel Schemas
```sql
CREATE TABLE system_state (
  id UUID PRIMARY KEY, stage TEXT, status TEXT, autonomous_action_id UUID,
  data JSONB, updated_at TIMESTAMPTZ, version INT);

CREATE TABLE events (
  id UUID PRIMARY KEY, event_type TEXT, source_engine TEXT,
  payload JSONB, created_at TIMESTAMPTZ);

CREATE TABLE task_queue (
  id UUID PRIMARY KEY, priority INT, status TEXT, retry_count INT,
  max_retries INT, payload JSONB, created_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ);

CREATE TABLE audit_log (
  id UUID PRIMARY KEY, action_type TEXT, actor TEXT, resource_id UUID,
  details JSONB, outcome TEXT, created_at TIMESTAMPTZ);  -- append-only

CREATE TABLE health_snapshots (
  id UUID PRIMARY KEY, engine_name TEXT, status TEXT,
  details JSONB, created_at TIMESTAMPTZ);

CREATE TABLE config (
  key TEXT PRIMARY KEY, value JSONB, version INT,
  updated_by TEXT, updated_at TIMESTAMPTZ);

CREATE TABLE decision_records (
  id UUID PRIMARY KEY, problem_statement TEXT, evidence JSONB,
  confidence NUMERIC, business_impact TEXT, risk_score NUMERIC,
  rollback_plan TEXT, success_criteria TEXT, outcome TEXT,
  verified_at TIMESTAMPTZ, reported_to_captain BOOLEAN, created_at TIMESTAMPTZ);

CREATE TABLE memory_entries (
  id UUID PRIMARY KEY,
  layer TEXT CHECK (layer IN ('strategic','operational','technical','customer','financial')),
  key TEXT, value JSONB, confidence_score NUMERIC, retention_until DATE,
  owner TEXT, version INT, updated_at TIMESTAMPTZ);
```

### Stability requirements (every kernel subsystem)
Idempotent · observable · testable · reversible · fault-tolerant · independently
restartable · fully logged · measurable. Every workflow: retry strategy, timeout,
rollback, health validation, audit trail. **No hidden automation.**

---

## 6. L2 — Operational Layer

- **VS Code HQ** — 3 modes: Reactive (Captain speaks → execute), Proactive
  (watch → find → fix → report), Scheduled (cron sessions, laptop off).
  Full spec: `docs/architecture/VSCODE_HQ_SETUP.md`.
- **GitHub** — source of truth. Branch: `claude/jarvis-cans-api-integration-ZThTD`.
  Push → GitHub Actions (`ec2-deploy.yml`) → OIDC → AWS SSM → base64 deploy script
  (`scripts/ec2-deploy-script.sh`) → EC2 rebuild → health gates.
- **CCR Cron** — 07:00 UTC daily self-heal session: health check → diagnose → fix →
  verify → update self-knowledge → Telegram briefing.
- **PR Activity Intelligence** — CI fails (any hour) → subscription fires → read logs →
  root-cause → fix → push → verified redeploy.
- **Parallel Agent Pool** — fan-out for large work (audits, migrations, multi-file builds).

---

## 7. L1/L0 — Infrastructure & Production

- Primary: EC2 `ap-south-2` (Hyderabad), deploy dir `/opt/jarvis`. DR: `ap-south-1` (Mumbai).
- Docker: postgres (pgvector/pg16), redis 7, backend (FastAPI/SQLAlchemy async),
  frontend (React 18/Vite), nginx 1.27, evolution-api (WhatsApp), Prometheus, Grafana,
  Alertmanager, Loki, Promtail, exporters.
- 64 scheduler jobs (38 core + 26 AIONX) via APScheduler.
- Secrets: `.env` gitignored locally → AWS Secrets Manager in production. Never in code.
- Health gates: `/health` (liveness) + `/readyz` (deep) on every deploy. Zero-downtime blue/green.

---

## 8. Known Production Blockers (must clear before v4 go-live)

| # | Blocker | Severity |
|---|---|---|
| 1 | `DEBUG=1` in production env | CRITICAL |
| 2 | Plaintext API keys in `.env` (must rotate + Secrets Manager) | CRITICAL |
| 3 | SSL certificates not staged (`infrastructure/nginx/ssl/`) | CRITICAL |
| 4 | Keys present in git history — rotate ALL before go-live | CRITICAL |
| 5 | AWS IAM role permissions unverified | CRITICAL |
| 6 | No documented DB backup strategy / RTO / RPO | CRITICAL |
| 7 | Rollback procedure never tested end-to-end | CRITICAL |
| 8–15 | Migrations untested in prod, SSL automation, health-check validation, DR failover untested, no load test, no Route53 failover, no rate limiting, no request audit logging | HIGH |

---

## 9. Implementation Roadmap

**Phase 0 — Production blockers (Day 1, ~6h)** — items in §8, deploy verified v3.

**Phase 1 — Kernel foundation (~Week 1-2)**
State Machine → Policy Engine → Retry Coordinator → Event Bus → Task Queue →
Health Aggregator → Audit Logger → Override Controller.

**Phase 2 — Kernel completion (~Week 2-3)**
Config Service → Sync Protocol → Service Discovery → Plugin Loader →
Failover Controller → Ops Dashboard.

**Phase 3 — AI Fabric (~Week 3-4)**
Model Registry → Router → Token Governor → Context Sync → Response Verifier.

**Phase 4 — AI Council (~Week 5-6)**
Assembly engine → parallel reasoning → conflict resolution → confidence scoring →
Verification integration → Memory integration.

**Phase 5 — Optimization & hardening (~Week 7-8)**
Routing Optimizer → load tests → failover tests → cost monitoring → go-live review.

**Acceleration model**: free builders (NIM/Gemini/DeepSeek) draft each unit in parallel
per the Task Book (`JARVIS_V4_TASKBOOK.md`); Claude reviews, corrects, integrates;
Verification Engine gates every merge. Honest total: ~437 engineering hours;
parallelized realistic wall-clock: 2–3 weeks.

---

## 10. Success Criteria

- Zero unverified autonomous actions; every decision has a decision record
- Every failure has a tested rollback; Captain receives "Verified", never "Fixed"
- Captain can PAUSE/STOP/ROLLBACK/SHUTDOWN any action in <1 minute, 24/7
- AI cost −25% within one quarter via routing optimization
- Council average confidence ≥ 85% on high-stakes recommendations
- Model availability ≥ 99.9% through fallback chains
- System supports adding 10+ engines without core refactor
- Every autonomous decision is explainable and traceable
