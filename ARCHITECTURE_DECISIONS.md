# JARVIS Architecture Decisions Log

**Purpose:** Record all major architectural decisions, their rationale, tradeoffs considered, and alternative approaches rejected. This document prevents re-litigation of settled decisions and provides context for future architectural changes.

**Last Updated:** 2026-07-02  
**Status:** Living Document — Updated as decisions are made

---

## AD-001: Multi-Tenant Architecture via tenant_id Column

**Decision:** Implement multi-tenancy through logical isolation (tenant_id column on all tables) rather than schema-per-tenant or database-per-tenant.

**Rationale:**
- **Simplicity:** Single database, single schema, simpler operational model
- **Scalability:** Can onboard 1,000+ clients without infrastructure multiplication
- **Cost:** No database multiplication overhead; economies of scale on shared infrastructure
- **Agility:** New client onboarding is instant (UUID generation, first row insertion)
- **Backup/Recovery:** Single backup strategy, simpler point-in-time recovery

**Tradeoffs:**
- ❌ Cannot fully isolate malicious tenant code (but JARVIS runs proprietary backend only — no client code execution)
- ❌ Query performance requires tenant_id filtering on every query (mitigated by indexed tenant_id columns)
- ❌ Data breach exposes all tenants' data if database is compromised (mitigated by encryption at rest, encrypted backups, network security)

**Alternatives Considered:**
1. **Schema-per-tenant:** Each client gets own PostgreSQL schema
   - Rejected: Schema multiplication overhead; 1,000 clients = 1,000 schemas = unmanageable
2. **Database-per-tenant:** Each client gets own PostgreSQL database
   - Rejected: Massive infrastructure cost; AWS RDS instance per client is prohibitive
3. **Separate SaaS Databases:** Multiple isolated database clusters
   - Rejected: No benefit over logical isolation; higher operational complexity

**Decision Level:** Captain (Strategic)  
**Reversibility:** High (refactor available if needed, but unlikely)  
**Impact Radius:** Database layer, API layer, cost tracking, billing system

---

## AD-002: 11-Provider LLM Router with Automatic Failover

**Decision:** Implement pluggable LLM router supporting 11 providers (Claude, GPT-4o, Gemini, DeepSeek, Groq, Mistral, Moonshot, ZhipuAI, Qwen, MiniMax, NVIDIA) with automatic failover and cost tracking per call.

**Rationale:**
- **Resilience:** No single provider dependency; automatic failover on rate limits or errors
- **Cost Optimization:** Route cheap tasks to fast models (DeepSeek), expensive reasoning to Claude Opus
- **Redundancy:** If OpenAI is down, automatically use Claude/Gemini/DeepSeek
- **Market Agility:** New provider can be added by implementing single interface (provider_config.py entry)
- **Financial Transparency:** Track cost per call, per tenant, per provider for accurate billing

**Cost Routing Strategy:**
- `CODE` tasks → Claude Sonnet (best code quality)
- `REASONING` tasks → Claude Opus (complex analysis)
- `STRATEGY` tasks → Claude Opus (strategic decisions)
- `ANALYSIS` tasks → Claude Opus (deep analysis)
- `RESEARCH` tasks → Gemini Pro (broad knowledge cutoff)
- `FAST` tasks → DeepSeek Flash (speed priority, cost $0.00002/1k tokens)
- `LONG_CONTEXT` tasks → Gemini Pro or Kimi-K2 (200k+ token windows)

**Tradeoffs:**
- ❌ More complex than single-provider approach (mitigated by abstraction layer)
- ❌ Provider API compatibility requires translation layer (mitigated by provider adapters)
- ❌ Billing complexity increases (mitigated by automated cost tracking)
- ✅ Resilience significantly improves (single provider = single point of failure)
- ✅ Cost-per-capability optimization becomes possible

**Alternatives Considered:**
1. **Single Provider (Claude only):** Simplest, but single point of failure
   - Rejected: Risk unacceptable for production operations
2. **Fallback Chain:** Try provider 1, on failure try provider 2
   - Rejected: Higher latency due to sequential attempts; cost tracking becomes complex
3. **Load Balancing:** Round-robin across providers regardless of task type
   - Rejected: Ignores cost/quality tradeoffs; wastes expensive providers on simple tasks

**Decision Level:** JARVIS (Operational)  
**Reversibility:** Medium (would require retraining on different provider)  
**Impact Radius:** AI infrastructure, cost tracking, resilience, client experience

**Implementation Details:**
- Location: `backend/app/services/ai/router.py`
- Provider configs: `backend/app/services/ai/providers/`
- Circuit breaker: `backend/app/services/ai/circuit_breaker.py`
- Cost tracking: `backend/app/services/ai/cost_tracker.py`
- Failover policy: Retry up to 3 times across providers before raising exception

---

## AD-003: APScheduler with Persistent Job Store (64 Jobs)

**Decision:** Use APScheduler with SQLAlchemy persistent job store to manage 64 scheduled operations (38 core engine + 26 AIONX organ jobs) across 24-hour UTC cycle.

**Rationale:**
- **Reliability:** Jobs survive server restarts due to persistent store
- **Visibility:** All scheduled jobs queryable from database; can monitor job execution
- **Flexibility:** Add new jobs without code deployment (insert into scheduler job table)
- **Coordination:** Single scheduler instance prevents duplicate job execution across multiple servers
- **Audit Trail:** Complete history of job execution, success/failure, execution time

**Job Categories:**

1. **Overnight Intelligence Pipeline (18:00-02:30 UTC)**
   - Lead discovery, market intelligence, proposal generation, cold outreach, freelance bids, follow-up sequences
   - Optimized for US afternoon/evening prime time (11:30 PM - 5:00 AM IST)

2. **Daily Operations (06:00-08:00 UTC)**
   - Captain briefings, health checks, lead scoring, monitoring
   - Ready for Captain's morning review (11:30 AM - 1:30 PM IST)

3. **Continuous Monitoring (every 2h, every 1h, every 30min, every 5min)**
   - Cost tracking, approval processing, threat detection, system health
   - AIONX sentinel sweep runs every 2 hours; operational IQ updates every 1 hour

4. **Weekly Cycles (Sunday 07:00-21:00 UTC)**
   - Strategy review, technology radar, competitor monitoring, market intelligence
   - Weekly memory promotion, authority recalibration, meta-learning synthesis

**Tradeoffs:**
- ❌ Database dependency: Job scheduling fails if PostgreSQL is down (mitigated by health monitoring + failover)
- ❌ Single scheduler instance is bottleneck (mitigated by APScheduler clustering support if scale demands it)
- ✅ Visibility is complete (all jobs in database)
- ✅ Zero code changes needed to add/modify/remove jobs

**Alternatives Considered:**
1. **Cron jobs on host OS:** Simple, but invisible to application; cannot track execution from API
   - Rejected: No visibility, no resilience, no easy monitoring
2. **Celery with Redis:** More distributed, but adds Redis dependency + complexity
   - Rejected: Overkill for current scale; APScheduler is sufficient
3. **AWS EventBridge:** Managed service, but vendor lock-in + cost
   - Rejected: APScheduler provides same capability without lock-in

**Decision Level:** JARVIS (Operational)  
**Reversibility:** Medium (scheduler jobs are table entries; can migrate to other scheduler)  
**Impact Radius:** Automation engine, lead generation, market intelligence, optimization cycles

---

## AD-004: Real-Time Cost Tracking at API Call Layer

**Decision:** Record every LLM API call in AIRequestLog table immediately after execution, capturing: provider, model, tokens used, cost estimate USD, latency ms, tenant_id, user_id, request type.

**Rationale:**
- **Billing Accuracy:** Enables accurate per-tenant cost allocation for invoicing
- **ROI Visibility:** Calculate client profitability in real-time
- **Optimization Feedback:** Analyze which providers/models are most cost-effective per task
- **Anomaly Detection:** Detect unusual cost spikes (potential bugs or DDoS)
- **Client Transparency:** Show customers exactly what their AI usage costs

**Data Captured Per Call:**
- `tenant_id` — multi-tenant isolation
- `provider` — which LLM provider (claude, openai, gemini, deepseek, etc.)
- `model` — exact model version (gpt-4o, claude-opus-4-8, etc.)
- `tokens_used` — input + output tokens
- `cost_estimate_usd` — calculated cost in USD (can be reconciled with invoice later)
- `latency_ms` — API response time in milliseconds
- `request_type` — task classification (CODE, REASONING, STRATEGY, RESEARCH, FAST, LONG_CONTEXT)
- `request_id` — for tracing
- `created_at` — timestamp in UTC

**Tradeoffs:**
- ❌ Database write per API call adds latency (mitigated by async writes, batching)
- ❌ Storage grows ~100 rows/day × 1,000 clients = 100k rows/day = 36M rows/year (mitigated by archival strategy)
- ✅ Complete audit trail of all AI usage
- ✅ Enables per-tenant billing
- ✅ Enables optimization recommendations

**Alternatives Considered:**
1. **Log to external service (DataDog, New Relic):** Offload storage, but vendor lock-in + cost
   - Rejected: Can archive to S3 later if scale demands
2. **Batch writes overnight:** Delay cost visibility until next day
   - Rejected: Real-time visibility is important for anomaly detection
3. **Sample 10% of requests:** Reduce storage, estimate full cost
   - Rejected: Loses accuracy; important to track every call

**Decision Level:** JARVIS (Operational)  
**Reversibility:** High (can migrate to external system later)  
**Impact Radius:** Billing, cost optimization, revenue reporting, client visibility

---

## AD-005: Multi-Tenant Cost Allocation Model

**Decision:** Implement three-tier cost model: (1) track all API costs to tenant, (2) allocate shared infrastructure costs proportionally, (3) invoice at fixed monthly retainer + variable AI usage.

**Cost Structure:**
```
Monthly Bill = Base Retainer + AI Usage Costs + Infra Allocation
  Base Retainer: $2,000-$8,000/month (fixed service tier)
  AI Usage: $0.00001 - $0.30 per request (variable by provider/model)
  Infra Allocation: Base Retainer includes up to $500/month infra; overage pro-rated
```

**Rationale:**
- **Predictability:** Fixed retainer component provides predictable MRR
- **Fairness:** Heavy API users pay for usage; light users don't subsidize heavy users
- **Alignment:** Incentivizes cost-efficient AI usage
- **Profitability:** Retainer covers infrastructure; API cost markup provides margin

**Billing Workflow:**
1. Track every API call in AIRequestLog (real-time)
2. Daily cost aggregation by tenant, provider, task type
3. Monthly invoice generation via `/api/v1/billing/invoice-ready/{tenant_id}`
4. Client views costs in `/monitoring` dashboard (real-time transparency)
5. Stripe charges via `/api/v1/payments/checkout` integration

**Tradeoffs:**
- ❌ Complex billing logic (mitigated by automation)
- ❌ Requires accurate cost estimation (mitigated by reconciliation with provider invoices quarterly)
- ✅ Aligns incentives (client and Aliyar both benefit from cost efficiency)
- ✅ Highly profitable (typical margin: 40-60% on AI costs)

**Alternatives Considered:**
1. **Fixed pricing only:** Simpler, but ignores variable costs; unprofitable if client uses many API calls
   - Rejected: Margins become negative
2. **Variable only:** Pure usage-based, but unpredictable for clients
   - Rejected: Client acquisition hard if no fixed cost
3. **Markup-based:** Add 3x markup on all AI costs
   - Rejected: Penalizes cost-efficient clients; creates wrong incentives

**Decision Level:** Captain (Strategic)  
**Reversibility:** Low (would require client contract renegotiation)  
**Impact Radius:** Revenue operations, client billing, profitability, market positioning

---

## AD-006: 9 AIONX Sovereign Organs (Autonomous Decision Systems)

**Decision:** Implement 9 specialized autonomous decision-making systems ("organs") that operate independently but coordinate through JARVIS supervisory layer:

1. **Sentinel** — Threat detection and anomaly monitoring
2. **Escalation** — Risk classification and escalation routing
3. **IQ Engine** — Real-time operational intelligence scoring
4. **Mission Control** — System state monitoring and telemetry
5. **Predictive Analysis** — Threat forecasting and prevention
6. **Capacity Planner** — AI agent resource allocation
7. **Trust Detection** — Client trust erosion monitoring
8. **Authority Recalibration** — Governance matrix updates
9. **Meta-Learning** — System self-evolution and learning

**Rationale:**
- **Specialization:** Each organ has single responsibility; high cohesion
- **Autonomy:** Each organ operates on schedule; doesn't wait for central coordinator
- **Resilience:** Failure of one organ doesn't cascade to others
- **Scalability:** New organs can be added without modifying existing ones
- **Intelligence:** Collective decision-making better than monolithic system

**Coordination Model:**
- Each organ writes its outputs to database tables (AIONX_* tables)
- JARVIS reads outputs and makes final decisions
- Captain can override any AIONX decision
- Feedback loop: actual outcomes inform next cycle's decisions

**Tradeoffs:**
- ❌ More complex than monolithic scheduler (mitigated by abstraction layer)
- ❌ Potential for conflicting recommendations (mitigated by JARVIS arbitration)
- ✅ Each organ can be independently tested and debugged
- ✅ System remains intelligent if multiple organs fail

**Alternatives Considered:**
1. **Single monolithic scheduler:** Simpler, but fragile; no specialization
   - Rejected: Cannot scale intelligence past single-system capability
2. **Hierarchical:** One master organ, rest are subordinates
   - Rejected: Master becomes bottleneck; reduces autonomy of other organs

**Decision Level:** JARVIS (Architectural)  
**Reversibility:** Medium (organs are isolated; can remove without affecting others)  
**Impact Radius:** Automation, intelligence, resilience, scalability

---

## AD-007: Glassmorphism Design System (Dark Theme)

**Decision:** Use glassmorphism design system (translucent cards, backdrop blur, layered transparency) with dark theme (0f0a1a background, #7c3aed purple accents) across all UI.

**Rationale:**
- **Premium Feel:** Glassmorphism signals high-end product; differentiates from generic SaaS UI
- **Performance:** GPU-accelerated blur effects feel responsive
- **Brand Consistency:** Purple accents (#7c3aed, #a78bfa) align with Aliyar identity
- **Accessibility:** Dark theme reduces eye strain for late-night operations (Captain often works 24/7)
- **Trendy:** Glassmorphism is current design trend; positions product as modern

**Design System Components:**
- `.card` — Glass card with rgba(255,255,255,0.05) + backdrop-filter blur(10px)
- Color palette: Green #86efac (excellent), Blue #93c5fd (good), Orange #fb923c (fair), Red #fca5a5 (poor)
- Typography: Sans-serif (system fonts), sizing hierarchy 12px–32px
- Spacing: 8px baseline grid
- Responsive breakpoints: 320px (mobile), 768px (tablet), 1024px (desktop), 1440px (wide)

**Tradeoffs:**
- ❌ Old browsers (IE11, older Safari) don't support backdrop-filter (mitigated: no IE support needed; Safari support >95%)
- ❌ GPU usage higher than flat design (mitigated: modern devices have GPU; impact negligible)
- ✅ Visual differentiation from competitors
- ✅ Professional, premium appearance

**Alternatives Considered:**
1. **Flat design:** Simpler CSS, but generic appearance
   - Rejected: Doesn't differentiate Aliyar
2. **Skeuomorphism:** 3D-like, but outdated
   - Rejected: Not trendy; signals low-end product
3. **Material Design:** Google's design system, but not distinctive
   - Rejected: Too generic; every SaaS uses Material Design

**Decision Level:** Captain (Branding)  
**Reversibility:** High (CSS-only change; can rebrand quickly)  
**Impact Radius:** UI/UX, brand perception, client satisfaction

---

## AD-008: PostgreSQL 16 + SQLAlchemy 2.0 Async

**Decision:** Use PostgreSQL 16 with SQLAlchemy 2.0 async ORM instead of synchronous ORM or other databases.

**Rationale:**
- **Reliability:** PostgreSQL 16 is mature, battle-tested, supports JSONB, arrays, full-text search
- **Async-Native:** SQLAlchemy 2.0 async supports concurrent requests without blocking
- **Developer Experience:** ORM handles SQL generation; safer than raw SQL
- **Type Safety:** SQLAlchemy 2.0 provides type hints (Python 3.9+)
- **Multi-Tenancy Support:** JSONB columns enable flexible schema per-tenant metadata

**Schema Design:**
- 35 tables (documented in JARVIS_SELF_KNOWLEDGE.md)
- Indexed on `tenant_id`, `created_at`, `status` for query performance
- Foreign keys enforce referential integrity
- Triggers on audit tables track who changed what and when

**Tradeoffs:**
- ❌ Async adds complexity vs. synchronous (mitigated by abstraction layer)
- ❌ Fewer developers familiar with async Python (mitigated by training + documentation)
- ✅ Can handle 1,000s of concurrent requests without thread pool explosion
- ✅ Cost savings: fewer database connections = cheaper RDS instances

**Alternatives Considered:**
1. **MongoDB:** Flexible schema, but weaker consistency guarantees
   - Rejected: Financial data requires ACID guarantees
2. **DynamoDB:** Serverless, but not suitable for complex queries (cost allocation queries)
   - Rejected: Query flexibility needed for billing reports
3. **Synchronous SQLAlchemy:** Simpler, but blocks on I/O
   - Rejected: Would require thousands of database connections at scale

**Decision Level:** JARVIS (Technical)  
**Reversibility:** Low (database migration would be massive)  
**Impact Radius:** Backend, data persistence, scaling, concurrency

---

## AD-009: Blue-Green Deployment with Health Gates

**Decision:** Deploy to AWS ECS Fargate with blue-green rolling deployment strategy. Health gates verify `/health` and `/readyz` endpoints before transitioning traffic.

**Rationale:**
- **Zero Downtime:** Traffic switches only after new version passes health checks
- **Rollback Speed:** If deployment fails, revert to previous version in <30 seconds
- **Canary Capability:** Can deploy to 10% of servers first, monitor, then roll out 100%
- **Testing:** POST-deploy health checks catch failures immediately (not after users see errors)

**Deployment Flow:**
1. Build Docker image, push to ECR
2. Start new ECS task set (blue)
3. Wait for new tasks to become healthy
4. Run health gate: curl `/health` and `/readyz` on new tasks
5. If healthy: switch ALB target group to new tasks (green)
6. If unhealthy: terminate new tasks, keep running old version
7. After 15 minutes stability: terminate old tasks

**Tradeoffs:**
- ❌ Requires 2x resource allocation during deployment (mitigated: only 15-minute window)
- ❌ More complex than direct replacement (mitigated: automation handles complexity)
- ✅ Zero customer impact from bad deployments
- ✅ Can deploy during business hours without fear

**Alternatives Considered:**
1. **Direct replacement:** Simple, but risky; customers see errors during deployment
   - Rejected: Unacceptable for production
2. **Canary:** Deploy to 1% first, monitor, gradually increase
   - Rejected: Overkill for internal deployment; blue-green is sufficient

**Decision Level:** JARVIS (Operational)  
**Reversibility:** Medium (requires Terraform changes to implement differently)  
**Impact Radius:** Deployment, reliability, customer experience, risk management

---

## AD-010: OpenID Connect (OIDC) with Captain Role-Based Authorization

**Decision:** Implement OIDC for authentication; Captain is sole administrative user. All other API endpoints require `tenant_id` context to enforce multi-tenant isolation.

**Authorization Model:**
- **Captain:** Full access to all endpoints, all tenants, all admin functions (via `/auth/captain` endpoint)
- **Tenant Users:** Access only to their own `tenant_id` data; no cross-tenant visibility
- **Public Endpoints:** `/health`, `/pricing`, `/catalog`, webhooks (Stripe, Telegram, SES inbound) require no auth

**Rationale:**
- **Simplicity:** Single administrative user reduces complexity vs. complex RBAC
- **Security:** Clear authority chain: Captain decides → JARVIS executes → tenant data isolated
- **Multi-Tenancy:** tenant_id in every request enforces data isolation
- **Flexibility:** Captain can impersonate any tenant for debugging without changing tenant data

**Tradeoffs:**
- ❌ Captain is single point of failure (mitigated: Slack/Telegram alerts notify immediately if API fails)
- ❌ Cannot delegate admin functions to other users (acceptable: Captain wants centralized control)
- ✅ Simple to audit: all changes trace back to Captain
- ✅ No complex permission matrices to maintain

**Alternatives Considered:**
1. **Complex RBAC:** Multiple roles (Admin, Manager, User), each with permissions
   - Rejected: Overengineered; Aliyar is small firm
2. **No auth:** Public API
   - Rejected: Security risk; tenant data exposed

**Decision Level:** Captain (Security)  
**Reversibility:** High (can add RBAC later if org grows)  
**Impact Radius:** Security, authentication, authorization, multi-tenancy

---

## Key Architectural Principles

### 1. Single Source of Truth
Every system has one authoritative data source. No data duplication except for caching/performance.

### 2. Async-First
All I/O is async (database, API calls, file operations). Blocking operations are exceptions.

### 3. Fail-Safe Design
If any service fails (AI provider, database, scheduler), system degrades gracefully. No cascading failures.

### 4. Observable
Every operation is traceable: request ID, timestamps, user context. Monitoring and alerting are built-in.

### 5. Secure by Default
Secrets never in code. Multi-tenant isolation enforced. No SQL injection vectors (parameterized queries).

### 6. Scalable
Design scales from 1 tenant to 10,000 without architecture changes. Horizontal scaling enabled.

### 7. Cost-Aligned
Incentives are aligned: Aliyar benefits when clients benefit. No hidden costs. Transparency always.

---

## Architecture Change Process

**How decisions are made:**

1. **Issue identified** — Operationally, from customer feedback, or strategic
2. **Options analysis** — JARVIS evaluates 2-3 alternatives with tradeoffs
3. **Recommendation** — JARVIS recommends option with rationale
4. **Captain decision** — Captain approves or rejects; final authority
5. **Documentation** — New AD entry created, recorded in this file
6. **Implementation** — Code change made, tested, deployed
7. **Monitoring** — Success metrics tracked, decision validated

**Reversibility assessment:**
- **High:** Can be changed without major refactoring (e.g., styling, new features)
- **Medium:** Requires code changes but not data migration (e.g., new subsystem)
- **Low:** Requires data migration, breaking API changes, or client notifications (e.g., database structure)

---

## Decision Index

| Decision | Status | Reversibility | Last Reviewed |
|----------|--------|---------------|---------------|
| AD-001: Multi-tenant via tenant_id | Active | High | 2026-07-02 |
| AD-002: 11-provider LLM router | Active | Medium | 2026-07-02 |
| AD-003: APScheduler 64-job system | Active | Medium | 2026-07-02 |
| AD-004: Real-time cost tracking | Active | High | 2026-07-02 |
| AD-005: Multi-tenant billing model | Active | Low | 2026-07-02 |
| AD-006: 9 AIONX organs | Active | Medium | 2026-07-02 |
| AD-007: Glassmorphism dark UI | Active | High | 2026-07-02 |
| AD-008: PostgreSQL 16 + async ORM | Active | Low | 2026-07-02 |
| AD-009: Blue-green deployment | Active | Medium | 2026-07-02 |
| AD-010: OIDC + Captain auth | Active | Medium | 2026-07-02 |

---

**Next Review:** 2026-08-02  
**Maintained by:** JARVIS Architectural Council  
**Authority:** Captain Syed Abrar
