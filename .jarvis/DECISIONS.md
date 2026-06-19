# JARVIS — ARCHITECTURAL DECISIONS
_Every major decision recorded here. Any model reads this and understands WHY, not just WHAT._

## Architecture

### ADR-001: FastAPI over Django/Flask
- **Decided:** Session 1
- **Why:** Native async, Pydantic validation, automatic OpenAPI docs, SQLAlchemy 2.0 async compatibility
- **Trade-off:** Smaller ecosystem than Django; accepted because we need async performance at scale

### ADR-002: PostgreSQL 16 with pgvector over separate vector DB
- **Decided:** Session 1
- **Why:** Single database = simpler ops, no sync issues, pgvector handles our semantic search scale
- **Trade-off:** Not as fast as Pinecone for pure vector workloads; acceptable for <1M vectors

### ADR-003: Multi-provider AI router over single provider lock-in
- **Decided:** Session 2
- **Why:** Provider outages, cost optimization, task-type specialization (Gemini for research, Claude for strategy)
- **Result:** 11 providers with circuit breakers, auto-failover, cost tracking per call

### ADR-004: AWS ECS Fargate over Kubernetes
- **Decided:** Session 1
- **Why:** No cluster management overhead; Captain operates alone; Fargate auto-scales containers
- **Trade-off:** Less control than EKS; acceptable at current scale (<50 concurrent users)

### ADR-005: APScheduler with SQLAlchemy job store over Celery
- **Decided:** Session 3
- **Why:** No separate broker (Redis already used for rate limiting); single process; simpler ops
- **Trade-off:** Not distributed; if ECS task restarts, jobs reschedule from DB state

### ADR-006: JWT HS256 (symmetric) over RS256 (asymmetric)
- **Decided:** Session 4 (security hardening)
- **Why:** Single-service auth; symmetric is simpler, no key management overhead
- **Trade-off:** If secret leaks, all tokens compromised; mitigated by AWS Secrets Manager

### ADR-007: Slowapi (Redis) rate limiting over API Gateway throttling
- **Decided:** Session 4
- **Why:** More granular (per-route, per-user); Redis state shared across ECS tasks
- **In-memory fallback:** Active if Redis is unavailable (non-production only)

### ADR-008: Blue/green ECS deployment over rolling update
- **Decided:** Session 1
- **Why:** Zero downtime; instant rollback if health gates fail
- **Health gates:** /health (liveness) + /readyz (database + Redis connectivity)

### ADR-009: AWS SES for outbound email over SendGrid/Mailgun
- **Decided:** Session 2
- **Why:** Already in AWS ecosystem; cheapest at volume; SES inbound handles reply parsing
- **Trade-off:** More setup for new domains; mitigated by SES sandbox → production process

### ADR-010: Alembic for migrations over SQLAlchemy auto-migrate
- **Decided:** Session 1
- **Why:** Explicit control, reviewable migration history, rollback capability
- **Convention:** Sequential numbering 0001–NNNN; never skip numbers

## Frontend

### ADR-011: Zustand over Redux for state management
- **Decided:** Session 1
- **Why:** Minimal boilerplate; works with React 18 concurrent features; no provider hell
- **Pattern:** Single store `useJarvisStore.js` — all views subscribe to relevant slices

### ADR-012: Glassmorphism design over material/flat design
- **Decided:** Session 1
- **Why:** Premium, distinctive brand identity; differentiates from generic SaaS dashboards
- **Implementation:** `backdrop-filter: blur()` + semi-transparent cards + gradient accents

### ADR-013: Vite over Create React App
- **Decided:** Session 1
- **Why:** 10x faster HMR; native ESM; smaller build output

## Business Logic

### ADR-014: Named human team members over "Aliyar Solutions Team"
- **Decided:** Session 5
- **Why:** Clients trust people, not brands; named authors convert better
- **Implementation:** `team_service.py` routes 36 service types to named team members

### ADR-015: Proposal → Contract auto-trigger on "accepted" status
- **Decided:** Session 6
- **Why:** Eliminate manual step; contract generated and emailed within seconds of acceptance
- **Trigger:** `update_proposal_status()` checks new_status in ("accepted", "won")

### ADR-016: Background tasks for all email over synchronous
- **Decided:** Session 6
- **Why:** Email delivery (SES) can take 200-2000ms; never block HTTP response for it
- **Pattern:** `bg.add_task(_send_email_bg, data)` immediately after DB flush

### ADR-017: Trust scoring with engagement events over manual qualification
- **Decided:** Session 6
- **Why:** Objective qualification; prevents hot leads from going cold unnoticed
- **Threshold:** trust_score ≥ 40 → ready_for_proposal flag set True

## What Was NOT Built (and Why)

- **GraphQL:** Over-engineering for our API surface; REST is sufficient
- **Microservices:** Premature; monolith with internal service layer is correct at this stage
- **Custom ML models:** Using frontier LLMs via router; custom models only when volume justifies
- **Multi-tenant auth:** Single Captain auth model; tenancy via tenant_id column (future-proofed)
