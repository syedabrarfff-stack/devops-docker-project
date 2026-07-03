# JARVIS v4 — Task Book
## Machine-Readable Work Breakdown for Multi-Agent Implementation

> Every task below is a discrete, independently-buildable unit. Any agent picking up a
> task MUST: (1) read `JARVIS_V4_ARCHITECTURE.md` first, (2) build ONLY the assigned unit,
> (3) write output to the specified path, (4) mark status DRAFT until a REVIEWER model
> approves and the Verification Engine validates.
>
> **builder** = free-tier model (NVIDIA NIM / Gemini / DeepSeek) or Claude subagent.
> **reviewer** = Claude (Opus/Sonnet) or OpenRouter premium. Reviewer approval is
> mandatory before any merge. No exceptions.

Legend: `deps` = task IDs that must be VERIFIED first. `est` = focused hours.

---

## PHASE 0 — PRODUCTION BLOCKERS (sequential, Claude-only, no free-model drafting)

| ID | Task | Output | deps | est |
|----|------|--------|------|-----|
| P0-1 | Set DEBUG=false for production env path | `.env` guidance + `ec2-deploy-script.sh` enforcement | — | 0.5 |
| P0-2 | Key rotation runbook + Secrets Manager migration plan | `docs/runbooks/SECRETS_ROTATION.md` | — | 1 |
| P0-3 | SSL cert generation via certbot on EC2 (automate in deploy script) | deploy script section | — | 1 |
| P0-4 | Verify AWS IAM role permissions (SSM describe/send, EC2 describe) | verification log | — | 0.5 |
| P0-5 | Test alembic migrations against fresh pg16 container locally | verification log | — | 1 |
| P0-6 | DB backup strategy: pg_dump nightly → S3, RTO 30min / RPO 24h | `docs/runbooks/BACKUP_RESTORE.md` + cron | — | 1 |
| P0-7 | End-to-end rollback test (deploy previous SHA, verify health) | verification log | P0-5 | 1 |

## PHASE 1 — KERNEL FOUNDATION (`backend/app/services/kernel/`)

| ID | Task | Output | builder | reviewer | deps | est |
|----|------|--------|---------|----------|------|-----|
| K1-1 | Alembic migration: all kernel tables (§5 schemas) | `backend/alembic/versions/*_kernel_tables.py` | NIM | Claude | — | 2 |
| K1-2 | State Machine service (transactional, versioned) | `kernel/state_machine.py` | NIM | Claude | K1-1 | 4 |
| K1-3 | Policy Engine (Authority Matrix as data + interceptor) | `kernel/policy_engine.py` + `kernel/authority_matrix.py` | Gemini | Claude | K1-1 | 4 |
| K1-4 | Event Bus (Redis pub/sub wrapper, typed events) | `kernel/event_bus.py` | NIM | Claude | — | 3 |
| K1-5 | Task Queue (priority, persistent, Redis + PG) | `kernel/task_queue.py` | NIM | Claude | K1-1 | 4 |
| K1-6 | Retry Coordinator (circuit breaker, backoff+jitter, escalation) | `kernel/retry_coordinator.py` | DeepSeek | Claude | K1-4 | 3 |
| K1-7 | Health Aggregator (poll engines 30s, aggregate, publish) | `kernel/health_aggregator.py` | Gemini | Claude | K1-4 | 3 |
| K1-8 | Audit Logger (append-only, queryable) | `kernel/audit_logger.py` | NIM | Claude | K1-1 | 2 |
| K1-9 | Override Controller (Telegram PAUSE/STOP/ROLLBACK/SHUTDOWN) | `kernel/override_controller.py` | Gemini | Claude | K1-2,K1-5 | 4 |
| K1-10 | Unit tests for K1-2..K1-9 | `backend/tests/kernel/` | NIM | Claude | each | 6 |

## PHASE 2 — KERNEL COMPLETION

| ID | Task | Output | builder | reviewer | deps | est |
|----|------|--------|---------|----------|------|-----|
| K2-1 | Config Service (feature flags, hot reload) | `kernel/config_service.py` | NIM | Claude | K1-1 | 3 |
| K2-2 | Sync Protocol (read-after-write between engines) | `kernel/sync_protocol.py` | Gemini | Claude | K1-4 | 3 |
| K2-3 | Service Discovery (engine registry) | `kernel/service_discovery.py` | NIM | Claude | K1-2 | 2 |
| K2-4 | Plugin Loader (engine manifests, registration) | `kernel/plugin_loader.py` | Gemini | Claude | K2-3 | 3 |
| K2-5 | Failover Controller (deep health → DR switch logic) | `kernel/failover_controller.py` | DeepSeek | Claude | K1-7 | 4 |
| K2-6 | Ops Dashboard API routes | `api/v1/routes/kernel_dashboard.py` | NIM | Claude | K1-2,K1-5,K1-7 | 3 |
| K2-7 | Ops Dashboard frontend view | `frontend/src/components/KernelDashboard/` | NIM | Claude | K2-6 | 4 |
| K2-8 | Unit + integration tests Phase 2 | `backend/tests/kernel/` | NIM | Claude | each | 5 |

## PHASE 3 — AI FABRIC (`backend/app/services/fabric/`)

| ID | Task | Output | builder | reviewer | deps | est |
|----|------|--------|---------|----------|------|-----|
| F3-1 | Alembic migration: fabric tables (§4.5) | migration file | NIM | Claude | K1-1 | 1 |
| F3-2 | Model Registry + health monitor (extends existing ai router) | `fabric/model_registry.py` | Gemini | Claude | F3-1 | 4 |
| F3-3 | Intelligent Router (task profile → model selection → fallback) | `fabric/router.py` | DeepSeek | Claude | F3-2 | 6 |
| F3-4 | Token Governor (budgets, quotas, 80% throttle) | `fabric/token_governor.py` | NIM | Claude | F3-1 | 4 |
| F3-5 | Context Sync (memory snapshots, lock, versioned merge) | `fabric/context_sync.py` | Gemini | Claude | K1-2 | 4 |
| F3-6 | Response Verifier (hallucination, policy, format checks) | `fabric/response_verifier.py` | Gemini | Claude | K1-3 | 4 |
| F3-7 | Migrate ALL existing direct LLM calls to Fabric | refactor across `services/` | DeepSeek | Claude | F3-3 | 8 |
| F3-8 | Fabric tests | `backend/tests/fabric/` | NIM | Claude | each | 5 |

## PHASE 4 — AI COUNCIL (`backend/app/services/council/`)

| ID | Task | Output | builder | reviewer | deps | est |
|----|------|--------|---------|----------|------|-----|
| C4-1 | Council Assembly engine (select members per task) | `council/assembly.py` | Gemini | Claude | F3-3 | 4 |
| C4-2 | Parallel reasoning orchestrator | `council/reasoning.py` | NIM | Claude | C4-1,F3-5 | 5 |
| C4-3 | Conflict resolution framework | `council/conflict_resolution.py` | Gemini | Claude | C4-2 | 4 |
| C4-4 | Confidence scoring + unified recommendation | `council/recommendation.py` | DeepSeek | Claude | C4-3 | 3 |
| C4-5 | Verification Engine integration | wiring in `council/__init__.py` | Claude | Claude | C4-4 | 3 |
| C4-6 | Executive Memory outcome recording | wiring | NIM | Claude | C4-5 | 2 |
| C4-7 | Council tests (5+ example decisions end-to-end) | `backend/tests/council/` | NIM | Claude | each | 5 |

## PHASE 5 — OPTIMIZATION & HARDENING

| ID | Task | Output | builder | reviewer | deps | est |
|----|------|--------|---------|----------|------|-----|
| O5-1 | Routing Optimizer (monthly weight learning job) | `fabric/routing_optimizer.py` + scheduler job | DeepSeek | Claude | F3-3, 30d data | 5 |
| O5-2 | Load test suite (1000 concurrent through router) | `scripts/load_test_fabric.py` | NIM | Claude | F3-7 | 4 |
| O5-3 | Failover drill (kill primary model, verify chain) | verification log | Claude | Claude | F3-3 | 2 |
| O5-4 | DR region failover drill | verification log | Claude | Captain | K2-5 | 3 |
| O5-5 | Rate limiting middleware (per-IP, per-user) | `backend/app/middleware.py` | NIM | Claude | — | 3 |
| O5-6 | Structured request audit logging | middleware | NIM | Claude | K1-8 | 2 |
| O5-7 | Final Production Readiness Review v4 | report to Captain | Claude | Captain | ALL | 3 |

---

## Merge Protocol (every task, no exceptions)

1. Builder writes DRAFT to a `draft/<task-id>` working area (never directly to service paths)
2. Reviewer model reviews: correctness, integration fit, security, style vs existing code
3. Reviewer corrects or rejects (rejected → back to builder with notes)
4. Tests must pass locally
5. Claude integrates into real path, commits `feat(v4-<phase>): <task-id> <description>`
6. Verification: import check + unit tests + (if service touched) health check
7. Status VERIFIED → next dependent task unblocked

## Status Tracking

Task status lives in `docs/architecture/TASKBOOK_STATUS.json`:
`{"K1-2": {"status": "VERIFIED|DRAFT|IN_REVIEW|REJECTED|PENDING", "builder": "...", "reviewer": "...", "commit": "..."}}`
Updated on every transition. This file is the coordination point for all parallel agents.

## PHASE 6A — REVENUE ACTIVATION

| ID | Task | Output | builder | reviewer | deps | est |
|----|------|--------|---------|----------|------|-----|
| R6-1 | Slack bot (two-way: slash commands + events) | `notifications/slack_bot.py` + `routes/slack_bot.py` | Claude | Claude | — | 3 |
| R6-2 | Zapier / Make.com webhook gateway | `integrations/zapier_gateway.py` + `routes/zapier.py` | Claude | Claude | — | 3 |
| R6-3 | White-label licensing manager + Captain routes | `whitelabel/license_manager.py` + `routes/captain_whitelabel.py` | Claude | Claude | K1-8 | 4 |
| R6-4 | LinkedIn outreach activation (Proxycurl enrichment + scheduler) | `outreach/linkedin_outreach.py` + scheduler job | Claude | Claude | — | 4 |
| R6-5 | Revenue activation dashboard (frontend) | `components/RevenueActivation/index.jsx` | Claude | Claude | R6-1..R6-4 | 3 |
| R6-6 | Phase 6A tests | `backend/tests/revenue/` | Claude | Claude | each | 3 |

## PHASE 6B — VOICE & MEDIA

| ID | Task | Output | builder | reviewer | deps | est |
|----|------|--------|---------|----------|------|-----|
| V6-1 | WhatsApp voice transcription pipeline (Whisper) | `voice/transcription.py` + `routes/voice_webhook.py` | Claude | Claude | — | 4 |
| V6-2 | Voice briefing activation (ElevenLabs → Telegram voice note) | `voice/briefing_voice.py` | Claude | Claude | V6-1 | 3 |
| V6-3 | Call summariser (record → transcribe → AI summary → memory) | `voice/call_summariser.py` + `routes/call_recording.py` | Claude | Claude | V6-1 | 4 |
| V6-4 | WhatsApp voice automation (TTS → Evolution send) | `voice/whatsapp_voice.py` | Claude | Claude | V6-2 | 3 |
| V6-5 | Voice analytics + scheduler job | `voice/analytics.py` + scheduler registration | Claude | Claude | V6-4 | 2 |
| V6-6 | Phase 6B tests | `backend/tests/voice/` | Claude | Claude | each | 3 |
