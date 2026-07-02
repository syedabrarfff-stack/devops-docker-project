# JARVIS Engineering Methodology
## Your AI Operating System's Engineering Playbook

**Status:** Active Development
**Last Updated:** 2026-07-02
**Maintained By:** Claude Code (Platform Engineering)
**Authority:** Captain (Syed Abrar)

---

## I. ENGINEERING AUTHORITY STRUCTURE

### Role Definition
**Claude Code** is now the primary engineering platform with the following authority:

| Domain | Authority | Approval Required |
|--------|-----------|------------------|
| Architecture Decisions | Full | No (unless >$50K infrastructure cost) |
| Code Quality | Full | No |
| Security | Full | No (alert Captain if critical) |
| DevOps/Deployment | Full | Captain review before prod (not blocking) |
| Catalog/Service Design | Full | No |
| Testing Standards | Full | No |
| Documentation | Full | No |
| Performance Optimization | Full | No |
| Technical Debt Management | Full | No |
| Breaking Changes | Recommend Alternative | Must discuss with Captain |

---

## II. CORE ENGINEERING PRINCIPLES

### A. Architecture First
- **Before coding:** Think architecture
- **Before committing:** Ensure scalability, maintainability, security
- **Challenge poor design:** Recommend alternatives
- **Document trade-offs:** Explain why this choice vs. alternatives

### B. Code Quality Standards

**Mandatory:**
- SOLID principles
- DRY (Don't Repeat Yourself)
- KISS (Keep It Simple, Stupid)
- YAGNI (You Aren't Gonna Need It)
- Clean Architecture where appropriate
- Domain-Driven Design patterns

**Preferred Patterns:**
- Composition over inheritance
- Dependency injection
- Event-driven where possible
- Async/await for I/O

### C. Security First
- **Never** hardcode secrets, API keys, tokens
- **Always** use environment variables + AWS Secrets Manager
- **Validate** all inputs at system boundaries
- **Encrypt** PII at rest and in transit
- **Use** TLS 1.3, JWT for auth, constant-time comparisons for secrets

### D. No Manual Work
- Automate everything possible
- Git hooks for pre-commit checks
- CI/CD for all deployments
- One-command setup for development
- Infrastructure as Code for everything

---

## III. DEVELOPMENT WORKFLOW

### Local Development Setup
```bash
# One-command bootstrap
./scripts/setup-dev.sh

# What this includes:
# 1. Python venv creation
# 2. Pip dependency installation
# 3. Docker compose build
# 4. Environment variable setup (from template)
# 5. Git hooks installation
# 6. Database migrations
# 7. Pre-commit checks enabled
# 8. IDE configuration
```

### Git Workflow

**Branch Strategy:**
- `main` - Production (protected, requires tests passing)
- `staging` - Pre-production tests
- `claude/task-name-*` - Development branches

**Commit Standards:**
```
feat(phase-N): short description
or
fix(component): issue resolved
or
refactor(service): improvement
or
docs(section): documentation update
or
test(feature): test coverage added

Include: WHAT, WHY, RISKS, ASSUMPTIONS
```

**Before Push:**
- ✅ Tests passing locally
- ✅ Code formatted (Black for Python, Prettier for JS)
- ✅ Linting passes (pylint, eslint)
- ✅ No security issues (bandit, snyk)
- ✅ Documentation updated if needed
- ✅ No broken commits (each commit must work independently)

### Testing Requirements

**Mandatory Coverage:**
- Unit tests: All business logic
- Integration tests: API endpoints, database operations
- Regression tests: Before shipping critical changes

**Test Execution:**
```bash
./scripts/test.sh              # Full suite
./scripts/test-watch.sh        # Watch mode for TDD
pytest backend/tests/ -v       # Manual run
npm test                       # Frontend
```

---

## IV. ARCHITECTURE LAYERS

### Layer 0: Command Center (Captain Interface)
- Telegram bot integration
- Email digests
- Dashboard access
- Approval workflows

### Layer 1: Supreme Intelligence (Constitutional Layer)
- JARVIS Constitution (12 immutable laws)
- 3-tier Authority Matrix (decisions by dollar value)
- 8 Escalation Triggers (Captain alerts)
- 5 Autonomous Engines (CEO, Revenue, Platform, Sales, Constitution)

### Layer 2: Operational Intelligence (67 API Endpoints)
- 19 layers of services
- 45+ intelligence engines
- 33+ AIONX sovereign organs
- 64 production scheduler jobs

### Layer 3: FastAPI Backend
- Async handlers
- SQLAlchemy 2.0 ORM
- Multi-tenant isolation
- Rate limiting per endpoint
- Request ID tracing

### Layer 4: Database Layer
- PostgreSQL 16 (35 tables, normalized)
- Redis 7 (cache, sessions, embeddings)
- Alembic migrations (linear chain, never merge)

### Layer 5: React Frontend
- 70+ views, glassmorphism design
- Zustand state management
- WebSocket real-time events
- Responsive grid layout

### Layer 6: AWS Infrastructure
- ECS Fargate (3-task cluster, auto-scaling)
- RDS PostgreSQL (multi-AZ failover)
- ElastiCache Redis (high availability)
- ALB + Route 53 (DNS, HTTPS)
- CloudWatch (logs, metrics, alarms)
- Secrets Manager (credential vault)

### Layer 7: External Integrations
- 30+ service divisions
- Apollo/HubSpot (CRM)
- AWS SES (email)
- Evolution API (WhatsApp)
- Stripe (payments)
- Gmail OAuth
- Google Calendar

---

## V. AI PROVIDER ARCHITECTURE

### Multi-Provider Router (Pluggable)

**Current Active Providers:**
1. **Anthropic Claude** (primary) - reasoning, code, complex tasks
2. **OpenRouter Gateway** - cost optimization, fallback routing
3. **DeepSeek V4** - fast code generation, cost-effective
4. **Google Gemini** - research, long-context analysis
5. **Vertex AI** - enterprise variant of Gemini
6. **NVIDIA APIs** - specialized models
7. Future providers (TBD)

**Router Logic:**
```python
def route_by_task_type(task: TaskType) -> ModelConfig:
    """
    CODE → DeepSeek V4 (fast, cheap)
           Fallback: Claude Sonnet
    
    REASONING → Claude Opus (best reasoning)
              Fallback: GPT-4o
    
    STRATEGY → Claude Opus (long-term thinking)
             Fallback: DeepSeek
    
    ANALYSIS → Claude Opus (detail, nuance)
             Fallback: Gemini
    
    RESEARCH → Gemini (breadth, web-connected)
             Fallback: Claude Sonnet
    
    FAST → DeepSeek Flash (immediate response)
          Fallback: Groq Llama
    """
```

**Circuit Breaker Pattern:**
- 5 consecutive failures → OPEN state (60s)
- Auto-failover to next provider
- Self-healer checks every 15 minutes
- Cost tracking per call (alert at $50/day surge)

**NO Hardcoding:**
- All models configured in environment
- Provider selection is runtime
- Easy to add new providers without code changes

---

## VI. DATABASE SCHEMA DESIGN

### Core Tables (35 total)

**Tenancy Layer:**
- `tenants` - Multi-tenant isolation
- `tenant_api_keys` - API key management
- `users` - User accounts

**Lead & Revenue (6 tables):**
- `leads` - Prospect records
- `companies` - Company info
- `contacts` - Contact records
- `clients` - Signed clients
- `deals` - Pipeline opportunities
- `revenue` - Revenue transactions

**Outreach & Communication (6 tables):**
- `outreach_log` - Sent outreach
- `email_tracking` - Email opens/clicks
- `reply_log` - Incoming replies
- `follow_up_queue` - Scheduled follow-ups
- `outreach_sequences` - Sequence templates
- `outreach_emails` - Email templates

**Operations & Tasks (6 tables):**
- `scheduled_jobs` - APScheduler jobs
- `job_failures` - Job error tracking
- `approval_requests` - Pending approvals
- `agent_tasks` - Async tasks
- `agent_messages` - Task messages
- `audit_logs` - Complete audit trail

**Memory & Knowledge (9 tables):**
- `memory` - Multi-tier memory
- `memory_operational` - Permanent facts
- `memory_strategic` - Long-term insights
- `civilization_memory` - Immutable event log
- `memory_graph_nodes` - Knowledge graph nodes
- `memory_graph_edges` - Knowledge graph edges
- `knowledge_base` - SOP documents
- `learning_records` - Learning events
- `sop_documents` - Standard procedures

**Intelligence & Governance (6 tables):**
- `ai_council_sessions` - Council voting
- `ai_council_member_weights` - Model weights
- `proposals` - Generated proposals
- `contracts` - Signed contracts
- `incident_reports` - Incident tracking
- `tech_radar_entries` - Technology tracking

**AIONX Sovereign Organs (10+ tables):**
- `decision_objects` - Decision records
- `decision_options` - Options considered
- `decision_outcomes` - Actual outcomes
- `counterfactual_simulations` - What-if analyses
- `decision_debt_assessments` - Consequences
- `client_digital_twins` - Per-client models
- `mission_autopsy_records` - Post-project analysis
- `sentinel_observations` - Threat monitoring
- `wisdom_index_snapshots` - Accuracy calibration

**Scheduling & Comms (4 tables):**
- `conversations` - Conversation history
- `notifications` - Telegram/email notifications
- `gmail_messages` - Gmail integration
- `credentials` - API key storage

### Migration Strategy
- **Tool:** Alembic
- **Pattern:** Linear chain (never merge conflicts)
- **Auto-applied:** On boot via `alembic upgrade head`
- **Reversible:** All migrations have `downgrade()` implementations

---

## VII. SCHEDULER ARCHITECTURE (64 Jobs)

### Core Engine Jobs (38)
Organized by function:

**Daily Intelligence:**
- `daily_briefing` (08:00 UTC) - KPIs, top leads, risks
- `morning_briefing` (07:00 UTC) - Team briefing
- `captain_dashboard_briefing` (06:55 UTC) - Dashboard snapshot
- `daily_optimization_review` (23:00 UTC) - System recommendations
- `daily_strategy_report` (23:00 UTC) - 6-layer strategy cascade

**Lead Pipeline:**
- `lead_scoring_sweep` (every 6h) - Re-score all leads
- `daily_icp_lead_scoring` (05:00 UTC) - Score new leads
- `outreach_processor` (every 1h) - Send queued outreach
- `reply_handler_scan` (every 2h) - Classify replies
- `contact_sync` (every 12h) - Sync with Apollo/HubSpot

**Overnight Revenue Engine (IST-timed for US/EU prime):**
- `overnight_lead_discovery` (18:00 UTC / 11:30 PM IST)
- `overnight_intel_analysis` (18:30 UTC / 12:00 AM IST)
- `overnight_proposal_engine` (19:30 UTC / 1:00 AM IST)
- `overnight_cold_outreach` (20:30 UTC / 2:00 AM IST)
- `overnight_freelance_bids` (21:30 UTC / 3:00 AM IST)
- `overnight_followup_sequences` (23:30 UTC / 5:00 AM IST)
- `overnight_pipeline_health` (01:00 UTC / 6:30 AM IST)
- `overnight_ops_report` (02:30 UTC / 8:00 AM IST)

**Intelligence & Market Scanning:**
- `tech_radar_scan` (Mon 06:00 UTC)
- `competitor_monitoring` (Mon 09:00 UTC)
- `market_intelligence_report` (Sun 07:00 UTC)
- `biweekly_research_report` (Sun 07:00 UTC)

**System Maintenance:**
- `self_healer` (every 15min) - Autonomous self-repair
- `nexus_heartbeat` (every 1h) - NEXUS coordination
- `lead_embedding_sweep` (03:15 UTC) - Semantic embeddings

### AIONX Organ Jobs (26)
**Distributed Lock Guard:**
- Only Task 1 (of 3 ECS instances) runs scheduler
- Tasks 2-3 skip initialization
- Prevents duplicate job execution across cluster

**Job Categories:**
- Sentinel & Monitoring (6 jobs)
- Decision Intelligence (6 jobs)
- Retrospective & Learning (8 jobs)
- Supreme Learning (weekly, 4 jobs)

---

## VIII. DEPLOYMENT STRATEGY

### CI/CD Pipeline

**Trigger Points:**
1. Push to main → Production deploy
2. Push to staging → Staging tests
3. PR to main → Test suite + validation
4. Manual dispatch → Re-deploy + rollback

**Pipeline Steps:**
```
1. Checkout → Clone repo at commit SHA
2. Build → Docker multi-stage build
3. Pre-flight → Python import check (catch SyntaxErrors early)
4. Push to ECR → Amazon Elastic Container Registry
5. Deploy to ECS → Blue/green rolling update
6. Health checks → /health + /readyz probes
7. Validate migrations → Alembic status
8. Notify Captain → Telegram + email
```

### Zero-Downtime Deployment

**Blue/Green Strategy:**
1. Spin up new tasks (green) with new image
2. Load balancer gradually shifts traffic
3. Health checks validate new tasks
4. Old tasks (blue) terminated after green stable
5. Rollback available if health checks fail

**Health Check Endpoints:**
- `/health` - Shallow liveness (immediate response)
- `/readyz` - Deep readiness (DB, AI, Redis, Evolution, SES, Scheduler)

### Secrets Management
- **Storage:** AWS Secrets Manager (never in code)
- **Rotation:** Manual + automated triggers
- **Access:** ECS task role only (IAM principle of least privilege)

### Monitoring & Alerting
- **CloudWatch Logs:** Structured JSON, indexed
- **Alarms:**
  - CPU > 80% → SNS alert
  - Memory > 90% → SNS alert
  - Error rate > 1% → SNS alert
  - RDS storage > 80GB → SNS alert
  - Health check failures → SNS alert

---

## IX. TECHNICAL DEBT MANAGEMENT

### Debt Categories

| Category | Example | Impact | Priority |
|----------|---------|--------|----------|
| **Code Duplication** | Repeated validation logic | Maintenance, bugs | High |
| **Deprecated APIs** | Old endpoint still in use | Migration blocker | Medium |
| **Missing Tests** | Critical path untested | Production risk | High |
| **Performance** | N+1 queries, slow endpoints | User experience | High |
| **Documentation** | Outdated README | Onboarding friction | Medium |
| **Hardcoding** | Config in code | Security, flexibility | Critical |
| **Error Handling** | Silent failures | Production blindness | High |
| **Logging** | Insufficient context | Debugging difficulty | Medium |

### Debt Tracking
- Create issue with `technical-debt` label
- Document: what it is, why it matters, estimated fix time
- Prioritize: assess impact vs. effort
- Schedule: allocate % of sprint to debt reduction

---

## X. PERFORMANCE OPTIMIZATION

### Database
- ✅ Indexes on foreign keys + frequently queried columns
- ✅ Batch queries (use IN clauses, not loops)
- ✅ Lazy loading + prefetch_related in SQLAlchemy
- ✅ Connection pooling (max_overflow=10)
- ⚠️ Monitor slow query log (>100ms alert)

### Caching Strategy
- Redis for sessions, embeddings, rate limits
- Cache invalidation on write
- TTL per data type (briefing: 24h, task locks: 1h)
- Monitor hit/miss ratio

### API Response Time
- Target: <100ms p95
- Monitor: X-Response-Time header
- Profile: Use APScheduler job profiling

### Frontend
- Lazy load components
- Memoize expensive computations
- Virtual lists for large datasets
- Code split at route level

---

## XI. SECURITY HARDENING

### Authentication & Authorization
- ✅ JWT tokens (Bearer) with short expiry
- ✅ Refresh tokens (longer expiry, httpOnly)
- ✅ Role-based access control (RBAC)
- ✅ Rate limiting per endpoint (3-30/min depending on risk)

### Data Protection
- ✅ HTTPS only (TLS 1.3)
- ✅ Encrypt PII at rest (in database)
- ✅ Parameterized SQL queries (no f-string WHERE clauses)
- ✅ Input validation (max_length, regex, type checks)
- ✅ CORS configuration (whitelist domains)

### Secret Management
- ✅ Environment variables only
- ✅ AWS Secrets Manager for production
- ✅ Never commit secrets (pre-commit hook checks)
- ✅ Rotate regularly

### Dependency Security
- ✅ Scan with Snyk
- ✅ Keep dependencies up-to-date
- ✅ Pin versions (requirements-lock.txt)
- ✅ Review changelogs before upgrade

---

## XII. DOCUMENTATION STANDARDS

### What Must Be Documented
1. **README** - Setup, architecture overview, quick start
2. **ARCHITECTURE.md** - Complete system design
3. **API.md** - Endpoint documentation (auto-generated from docstrings)
4. **DEPLOYMENT.md** - How to deploy to each environment
5. **CONTRIBUTING.md** - Developer onboarding
6. **CHANGELOG.md** - Version history + breaking changes

### Documentation Format
- Markdown (.md)
- Diagrams with Mermaid or ASCII
- Code examples (keep in sync with code)
- Keep documentation with code (same PR)

### Keeping Docs Synchronized
- Update docs **in the same commit** as code changes
- Use docstrings for functions (auto-doc generation)
- Review docs in code review (treat like code)
- Run doc linter (check for broken links)

---

## XIII. MONITORING & OBSERVABILITY

### Logging Strategy
```python
# Include context in every log
logger.info(
    "Event occurred",
    extra={
        "request_id": request_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "action": action,
        "duration_ms": duration,
        "status": status,
    }
)
```

### Metrics to Track
- API response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- Throughput (requests/sec)
- Database query time
- Cache hit/miss ratio
- Job success/failure rate
- Memory usage
- CPU utilization

### Alerting Thresholds
- **Critical:** Error rate > 5% → Immediate page
- **High:** Error rate > 1% → Slack alert
- **Medium:** Response time > 500ms → CloudWatch log

---

## XIV. CONTINUOUS IMPROVEMENT

### Weekly Review Cycle
1. **Monday:** Assess technical debt, plan week
2. **Wednesday:** Midweek check-in, adjust if needed
3. **Friday:** Retrospective, what worked, what didn't

### Monthly Review Cycle
1. Performance metrics review
2. Security audit
3. Dependency updates
4. Documentation audit
5. Architecture assessment

### Quarterly Review Cycle
1. Strategic alignment check
2. Technology radar update
3. Capacity planning
4. Major refactoring opportunities
5. Cost optimization analysis

---

## XV. EMERGENCY PROCEDURES

### Production Incident Response
1. **Detect:** Alert triggered → Page on-call
2. **Assess:** Understand scope + impact
3. **Mitigate:** Temporary fix if possible
4. **Resolve:** Root cause fix
5. **Document:** Incident report (what, why, prevent)
6. **Improve:** Add monitoring + tests to prevent recurrence

### Rollback Procedure
```bash
# Identify bad version
aws ecs describe-task-definition --task-definition jarvis-prod

# Revert to previous version
aws ecs update-service \
  --cluster jarvis-prod-cluster \
  --service jarvis-prod-service \
  --task-definition jarvis-prod:N-1

# Monitor health
aws ecs describe-services --cluster jarvis-prod-cluster --services jarvis-prod-service
curl https://jarvis.aliyarsolutions.com/readyz
```

### Communication During Incident
- **Slack:** #incidents channel (real-time updates)
- **Telegram:** Captain notification (immediate)
- **Email:** Post-incident review (lessons learned)

---

## XVI. FUTURE ROADMAP

### Phase 1 (Q3 2026): Foundation
- [x] Core platform architecture
- [x] Multi-provider AI routing
- [x] 64 production scheduler jobs
- [ ] **IN PROGRESS:** Catalog system redesign

### Phase 2 (Q4 2026): Autonomy
- Multi-agent orchestration framework
- Collective intelligence (9+ agents voting)
- Self-healing automation
- Predictive incident detection

### Phase 3 (Q1 2027): Scale
- White-label platform licensing
- Multi-region deployment
- Advanced analytics dashboard
- Custom AI training (on Aliyar data)

### Phase 4 (Q2 2027): Compounding
- Self-improving intelligence loops
- Autonomous business unit formation
- Revenue optimization AI
- Global operational intelligence

---

## XVII. YOUR ROLE AS PLATFORM ENGINEER

### Daily Responsibilities
1. Monitor production system health
2. Review code changes
3. Manage technical debt
4. Optimize performance
5. Ensure security compliance

### Weekly Responsibilities
1. Capacity planning review
2. Dependency update assessment
3. Performance metrics analysis
4. Security audit
5. Documentation synchronization

### Monthly Responsibilities
1. Architecture review
2. Technology assessment
3. Cost optimization
4. Incident analysis
5. Roadmap refinement

### Escalation Criteria
- **Captain Immediate Alert:**
  - Production down (>5 min)
  - Security breach detected
  - Data loss risk
  - Major feature broken
  
- **Captain Same-Day Review:**
  - Performance degradation
  - Cost surge (>25% increase)
  - High technical debt accumulation
  - User-reported issues

- **Captain Next-Meeting Discussion:**
  - Dependency updates
  - Refactoring opportunities
  - Architecture improvements
  - Roadmap adjustments

---

## REMEMBER

This methodology is **your playbook**. Use it to:
- Make confident engineering decisions
- Maintain high standards
- Prevent regressions
- Plan long-term scaling
- Keep the system production-ready

The goal is **sustainable, intelligent, scalable operations** — not speed for speed's sake.

---

**Next:** Complete catalog redesign + implementation
