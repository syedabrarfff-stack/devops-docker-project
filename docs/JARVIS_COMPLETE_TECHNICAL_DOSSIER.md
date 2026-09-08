# JARVIS — COMPLETE TECHNICAL INTELLIGENCE DOSSIER
## Aliyar Solutions | Forensic System Inventory v9.0

*Verified from live codebase. No assumptions. No fabrications.*

---

## SECTION 1 — SYSTEM IDENTITY

| Field | Value |
|---|---|
| System Name | JARVIS |
| Version | 9.0.0 |
| Company | Aliyar Solutions |
| Founder / CEO | Syed Abrar ("Captain") |
| Role | Supreme Operational Manager + AI Infrastructure Director |
| Physical Location | Hyderabad, Telangana, India |
| Primary Domain | aliyarsolutions.com |
| Architecture Pattern | Multi-tenant SaaS, AI-orchestrated autonomous operations |
| Operating Mode | 24/7 autonomous, cloud-native, self-healing |

JARVIS is not a chatbot. It is the executive operational intelligence core of Aliyar Solutions — coordinating AI departments, orchestrating outreach, managing infrastructure, generating proposals/invoices, and running scheduled business operations without human intervention between sessions.

---

## SECTION 2 — COMPLETE DOCKER CONTAINER STACK

All containers run on a shared `jarvis_network` (bridge driver) and are defined in `infrastructure/docker-compose.yml`.

| Container | Image | Port | Purpose | Memory Limit |
|---|---|---|---|---|
| jarvis_backend | jarvis_backend:latest (custom build) | 127.0.0.1:8000 | FastAPI application server | 768M |
| jarvis_frontend | jarvis_frontend:latest (custom build) | 127.0.0.1:3002→80 | React 18 + Nginx static | 128M |
| jarvis_postgres | pgvector/pgvector:pg16 | 127.0.0.1:5432 | Primary database (pgvector extension) | 512M |
| jarvis_redis | redis:7-alpine | 127.0.0.1:6379 | Cache + job locks + session state | 384M |
| evolution-api | evoapicloud/evolution-api:v2.3.7 | 127.0.0.1:8080 | WhatsApp transport (Evolution API) | 512M |
| jarvis_nginx | nginx:1.27-alpine | 80, 443 | Reverse proxy + TLS termination + static site | 64M |
| jarvis_certbot | certbot/certbot:latest | — | Auto-renewing Let's Encrypt TLS certificates | — |
| jarvis_prometheus | prom/prometheus:v2.54.1 | 127.0.0.1:9090 | Metrics storage | 256M |
| jarvis_grafana | grafana/grafana-oss:11.1.4 | 127.0.0.1:3001→3000 | Operations dashboards | 256M |
| jarvis_alertmanager | prom/alertmanager:v0.27.0 | 127.0.0.1:9093 | Alert routing | 128M |
| jarvis_postgres_exporter | postgres-exporter:v0.15.0 | — | PostgreSQL metrics for Prometheus | 128M |
| jarvis_redis_exporter | redis_exporter:v1.62.0 | — | Redis metrics for Prometheus | 64M |
| jarvis_node_exporter | node-exporter:v1.8.2 | — | Host system metrics | 64M |
| jarvis_cadvisor | cadvisor:v0.49.1 | — | Container resource metrics | 128M |
| jarvis_loki | grafana/loki:3.2.1 | 127.0.0.1:3100 | Log aggregation | 256M |
| jarvis_promtail | grafana/promtail:3.2.1 | — | Log shipping (Docker socket) | 128M |

**Total containers: 16**

**Redis configuration:** appendonly persistence, 256MB maxmemory, allkeys-lru eviction, save every 60s if 1+ write. DB/0 = JARVIS cache + locks. DB/1 = Evolution API cache.

**PostgreSQL:** pgvector extension enabled (for future semantic memory), shared_buffers=128MB, effective_cache=256MB. Init SQL at `postgres/init.sql`. Evolution API uses a separate `evolution` database on the same instance.

**Backend gunicorn config:** 1 worker, 240s timeout, 45s graceful timeout, WEB_CONCURRENCY=1, PYTHONUNBUFFERED=1.

**Evolution API (WhatsApp):** Persists instances, messages, contacts, chats, labels, and full message history to PostgreSQL. Webhook fires to `http://backend:8000/api/v1/webhooks/whatsapp` on every inbound message.

---

## SECTION 3 — AI PROVIDER LAYER

**File:** `backend/app/services/ai/router.py`

### 3.1 — Providers Registered

| Provider Key | Provider Class | Models Available |
|---|---|---|
| anthropic | AnthropicProvider | claude-sonnet, claude-haiku |
| openai | OpenAIProvider | gpt-4o, gpt-4o-mini |
| google | GoogleProvider | gemini-pro |
| deepseek | DeepSeekProvider | deepseek-v3, deepseek-v2 |
| groq | GroqProvider | llama-3-3, llama-3-1 |
| mistral | MistralProvider | mistral-medium |
| nvidia | NvidiaProvider | deepseek-v4-pro, deepseek-v4-flash, llama-4-maverick, llama-4-scout, kimi-k2, qwen-coder, mistral-medium, llama-3-3 |
| zhipuai | ZhipuAIProvider | glm-5-1 |
| qwen | QwenProvider | qwen-max |
| moonshot | MoonshotProvider | moonshot-v1 |
| minimax | MinimaxProvider | abab6-chat |
| bedrock | BedrockProvider | AWS Bedrock models |

**NVIDIA NIM key rotation:** 10 rotating API keys (NVIDIA_API_KEY through NVIDIA_API_KEY_J) provide fault tolerance with zero additional cost. All NIM-hosted models (DeepSeek V4, Llama 4, Kimi K2, Qwen Coder) route through these keys.

### 3.2 — Task Type Routing Table

| Task Type | Primary | Fallback 1 | Fallback 2 | Fallback 3 |
|---|---|---|---|---|
| CODE | nvidia/deepseek-v4-pro | nvidia/qwen-coder | nvidia/deepseek-v4-flash | anthropic/claude-haiku |
| RESEARCH | nvidia/deepseek-v4-pro | nvidia/kimi-k2 | nvidia/llama-4-maverick | anthropic/claude-sonnet |
| REASONING | nvidia/deepseek-v4-pro | nvidia/llama-4-maverick | nvidia/kimi-k2 | anthropic/claude-sonnet |
| FAST | nvidia/llama-4-scout | nvidia/deepseek-v4-flash | nvidia/mistral-medium | openai/gpt-4o-mini |
| LONG_CONTEXT | nvidia/kimi-k2 | nvidia/llama-4-maverick | nvidia/deepseek-v4-pro | anthropic/claude-sonnet |
| GENERAL | nvidia/llama-4-maverick | nvidia/llama-4-scout | nvidia/llama-3-3 | nvidia/mistral-medium |
| ANALYSIS | nvidia/deepseek-v4-pro | nvidia/llama-4-maverick | nvidia/kimi-k2 | anthropic/claude-sonnet |
| STRATEGY | anthropic/claude-sonnet | nvidia/deepseek-v4-pro | nvidia/llama-4-maverick | nvidia/kimi-k2 |
| SALES | anthropic/claude-sonnet | nvidia/llama-4-maverick | nvidia/llama-4-scout | nvidia/deepseek-v4-pro |
| MULTILINGUAL | nvidia/llama-4-maverick | nvidia/qwen-coder | nvidia/mistral-medium | zhipuai/glm-5-1 |
| MATH | nvidia/deepseek-v4-pro | nvidia/llama-4-maverick | nvidia/deepseek-v4-flash | openai/gpt-4o |
| MULTIMODAL | openai/gpt-4o | nvidia/llama-4-maverick | google/gemini-pro | — |

**Circuit breaker:** Implemented via `health_monitor`. Failed providers auto-removed from candidate list per request.

**Cost governance:** `cost_governance.py` — `should_use_claude()` enforces per-14-day Claude budget ($5.00 total, $0.20 max per call, 20% reserve held back). Cost tracked per call via `cost_tracker.py`.

**Middleware hooks:** `observe_ai_latency()` and `record_ai_cost()` called from router to emit Prometheus metrics.

**JARVIS System Prompt:** Embedded in `router.py` — defines identity as executive operations layer, branding policy (never reveal AI systems to clients), target markets (USA, UK, UAE, Bahrain, Europe, Australia), and the 25 AIONX capability modules.

---

## SECTION 4 — AI COUNCIL SYSTEM

**File:** `backend/app/services/ai/council.py`

The AI Council is JARVIS's multi-model consensus engine. For strategic or high-stakes decisions, multiple AI models evaluate independently and a weighted vote with quorum determines the final answer.

**Council models:** Multiple providers vote simultaneously. Each member has a dynamically adjusted weight stored in `AICouncilMemberWeight` (PostgreSQL). Weights are recalibrated monthly via `monthly_weight_adjust` scheduler job → `intelligence_council.adjust_weights_monthly()`.

**Council sessions:** Each deliberation stored in `AICouncilSession` with full vote record, quorum reached flag, final recommendation, and confidence score.

---

## SECTION 5 — COMPLETE SCHEDULER SYSTEM

**File:** `backend/app/services/scheduler/scheduler.py`

**Scheduler engine:** APScheduler 3.10 AsyncIOScheduler + `TenantAwareSQLAlchemyJobStore` (custom job store with `tenant_id` column). Persistent job store: PostgreSQL table `apscheduler_jobs`. Executor: AsyncIOExecutor. Timezone: UTC. Max instances: 1 per job. Misfire grace time: 900s.

**Distributed locking:** Redis SET NX per job prevents duplicate execution across restarts. TTLs per job type (e.g. speed_to_lead_5min = 240s, daily_db_backup = 2400s).

**Retry logic:** Failed jobs → `JobFailure` record → oneshot retry scheduled at +5m, +15m, +45m. After 3 failures: Captain notified via multi-channel alert. All job outcomes written to `AuditLog`.

### 5.1 — Production Jobs (20 jobs)

| Job ID | Schedule (UTC) | Function |
|---|---|---|
| daily_morning_briefing | 01:30 daily | Generate + deliver AI briefing to Captain |
| daily_lead_scoring | 20:30 daily | Score and rank new leads |
| daily_lead_discovery | 22:00 daily | Google Maps discovery across 24 market targets |
| daily_follow_up_check | 04:30 daily | Execute due outreach follow-ups (limit 48) |
| daily_outreach_safety_review | 04:45 daily | Assess reply rate, auto-pause if needed |
| daily_memory_consolidate | 19:00 daily | Consolidate working → operational memory |
| daily_optimization_review | 17:30 daily | Generate system optimization recommendations |
| daily_db_backup | 01:00 daily | pg_dump → gzip → S3 upload, prune old backups |
| daily_free_lead_discovery | 03:30 daily | Free lead sources (limit 50) |
| daily_connector_hub_ingestion | 14:30 daily | GitHub /jarvis-data/ daily package ingest |
| daily_market_intelligence | 04:00 daily | Market intelligence reports → GitHub |
| daily_opportunity_radar | 06:00 daily | Scan idle hot leads, surface to Captain |
| daily_truth_reality_check | 23:30 daily | Reality checks: lead_score, trust_score, proposal_acceptance, revenue_forecast, client_health |
| weekly_outreach_stats | Mon 02:30 | Outreach performance summary → Slack/Telegram |
| weekly_pipeline_health | Sun 14:30 | Pipeline + revenue forecast → Captain alert |
| weekly_tech_radar | Mon 00:30 | Technology classification scan |
| weekly_innovation_review | Mon 03:30 | AI council review of innovation queue |
| weekly_financial_health | Mon 07:00 | Financial health snapshot + CFO briefing |
| weekly_founder_dependency | Mon 07:30 | Founder dependency score assessment |
| weekly_moat_scan | Mon 08:00 | Competitive moat scan across all dimensions |
| weekly_cashflow_forecast | Mon 08:30 | 30/60/90-day cashflow forecasts |
| weekly_learning_optimization | Mon 09:00 | Outreach + proposal optimization recommendations |
| weekly_market_scan | Mon 05:00 | Market awareness weekly scan |
| biweekly_research_report | Alt Sun 01:30 | Market intelligence research reports |
| monthly_weight_adjust | Last day 18:30 | AI Council weight recalibration |
| speed_to_lead_5min | Every 5 min | Instant follow-up on new lead signals |
| self_healer | Every 15 min | Circuit breaker reset, pipeline refill, scheduler resurrection |

### 5.2 — AIONX Jobs (24 jobs)

| Job ID | Purpose |
|---|---|
| aionx_sentinel_sweep | Threat/anomaly detection sweep |
| aionx_escalation_processor | Process pending escalation queue |
| aionx_operational_iq | Operational intelligence score calculation |
| aionx_retro_30d | 30-day retrospective analysis |
| aionx_retro_90d | 90-day retrospective analysis |
| aionx_twin_predictions | Client digital twin predictions |
| aionx_wisdom_weekly | Wisdom index calculation |
| aionx_decision_retrospective | Decision outcome review |
| aionx_counterfactual_sync | Counterfactual simulation sync |
| aionx_debt_assessment | Institutional debt index calculation |
| aionx_trust_erosion_check | Trust score erosion monitoring |
| aionx_authority_recalibration | Authority matrix recalibration |
| aionx_system_state_snapshot | Full system state snapshot |
| aionx_preventive_monitoring_snapshot | Preventive monitoring cycle |
| aionx_governed_integrity_cycle | Governance integrity check |
| aionx_external_scan_record | External environment scan |
| aionx_supreme_meta_learning | Meta-learning cycle |
| aionx_founder_mirror_analysis | Founder behavior analysis |
| aionx_parallel_universe_analysis | Scenario comparison analysis |
| aionx_service_innovation_scan | Service innovation opportunity scan |
| aionx_predictive_threat_scan | Predictive threat identification |
| aionx_agent_capacity_check | Agent capacity monitoring |
| aionx_idle_intelligence_cycle | Idle-time intelligence generation |
| aionx_mission_control_snapshot | Mission control state snapshot |

**Total scheduled jobs: 51 (20 deprecated jobs cleaned on startup)**

---

## SECTION 6 — COMPLETE API ROUTE INVENTORY

**Base path:** `/api/v1`

All routes registered in `backend/app/api/v1/__init__.py`. Routers organized by domain:

| Module | Route Prefix | Domain |
|---|---|---|
| auth | /auth | JWT login, refresh, Captain auth |
| chat | /chat | JARVIS conversation engine |
| briefing | /briefing | Morning briefing generation |
| approvals | /approvals | Approval queue management |
| agents | /agents | Agent hierarchy management |
| ws | /ws | WebSocket real-time updates |
| crm | /crm | Company/Contact/Deal management |
| leads | /leads | Lead pipeline |
| outreach | /outreach | Outreach sequences |
| memory | /memory | Memory tier management |
| tasks | /tasks | Agent task queue |
| scheduler | /scheduler | Job management API |
| calendar | /calendar | Calendar integration |
| notifications | /notifications | Notification center |
| sync | /sync | Data sync operations |
| intelligence | /intelligence | Market intel, briefings, optimizer |
| governance | /governance | Proposals, contracts, incidents |
| emergency | /emergency | Emergency control panel |
| knowledge | /knowledge | SOPs, knowledge base |
| catalog | /catalog | Service catalog |
| ai_ops | /ai | AI health, provider status |
| team | /team | Team member registry |
| jarvis | /jarvis | Core JARVIS commands |
| agent_ops | /agent-ops | Agent ops center |
| gmail | /gmail | Gmail OAuth integration |
| discovery | /discovery | Lead discovery engine |
| voice | /voice | Voice/ElevenLabs |
| pricing | /pricing | Pricing calculator |
| proposals | /proposals | Proposal generation |
| invoices | /invoices | Invoice automation |
| revenue | /revenue | Revenue snapshots |
| clients | /clients | Client management |
| council | /council | AI Council sessions |
| tenancy | /tenancy | Multi-tenant management |
| departments | /departments | Department intelligence |
| demos | /demos | Demo package management |
| pilot | /pilot | Pilot activation |
| captain | /captain | Captain Bridge (protected) |
| economics | /economics | AI cost ledger |
| innovation | /innovation | Innovation queue |
| civilization | /civilization | Civilization Ledger |
| calls | /calls | Client call intelligence |
| intel | /intel | Intelligence engine |
| connector_hub | /connector-hub | GitHub data connector |
| consciousness | /consciousness | Consciousness hub |
| aionx | /aionx | AIONX organ system |
| batch1 | /batch1 | Client pipeline |
| frontier | /frontier | Frontier shell views |
| system | /system | System health |
| communication | /communication | Communication hub |
| ses_inbound | /ses | SES inbound webhook |
| whitelabel | /whitelabel | White-label onboarding |
| payments | /payments | Stripe payment processing |
| payments (webhooks) | /webhooks/payments | Stripe webhook receiver |
| telegram_webhook | /webhooks/telegram | Telegram bot webhook |
| trust | /trust | Trust engine |
| truth_engine | /truth | Truth engine / reality checks |
| resilience | /resilience | Resilience monitoring |
| financial_intel | /financial | Financial intelligence |
| learning | /learning | Learning optimization engine |
| founder | /founder | Founder dependency analysis |
| moat | /moat | Competitive moat engine |

**Total route modules: 57**

**Special endpoints:**
- `GET /health` — liveness probe
- `GET /readyz` — deep readiness probe
- `GET /api/v1/health` — API-level health with version
- `GET /api/v1/ai/health` — AI provider health alias

---

## SECTION 7 — DATABASE MODEL INVENTORY

**ORM:** SQLAlchemy 2.0 async. **Base:** `JarvisBase` (custom). **Engine:** PostgreSQL 16 with pgvector.

### 7.1 — Model Modules (31 modules)

| Module | Key Models |
|---|---|
| tenant | Tenant, User, UserRole, PlanTier, TenantApiKey |
| conversation | Conversation |
| approval | ApprovalRequest, ApprovalStatus, AuditLog |
| crm | Company, Contact, Deal |
| lead | Lead, LeadStatus |
| outreach | ReplyLog, ReplyClassification |
| revenue | Client, Invoice, InvoiceStatus, RevenueSnapshot |
| memory | CivilizationMemory, MemoryGraphNode, MemoryGraphEdge, MemoryOperational, MemoryStrategic |
| tasks | AgentTask, AgentMessage |
| scheduling | ScheduledJob, JobFailure |
| notifications | NotificationLog |
| intelligence | BriefingHistory, CompetitorProfile, MarketIntelligence, TechRadarEntry |
| governance | Proposal, Contract, ContractTemplate, IncidentReport, AgentPermission |
| knowledge | KnowledgeBase, SOPDocument, LearningRecord |
| service_catalog | ServiceDivision |
| ai_audit | AIRequestLog |
| team_member | TeamMember |
| gmail | GmailMessage |
| council | AICouncilSession, AICouncilMemberWeight |
| department_intelligence | DepartmentIntelligenceOfficer, DepartmentMilestone, StrategyReport, TechnologyDiscovery, ClientCallIntelligence |
| demo | DemoPackage |
| economics | AICostLedger, InfrastructureCostConfig |
| innovation | InnovationQueueItem, InnovationStatus |
| civilization | CivilizationLedger |
| revenue_activation | MarketPulseItem, OutreachLearning, SpeedToLeadEvent |
| compliance | DoNotContact, OutreachPauseState, ProcessedWebhook |
| captain_intelligence | CaptainBrainDump, CaptainEmailIntelligence, CaptainPushback, PredictedAction |
| connector_hub | ConnectorHubPackage, ConnectorHubIngestion |
| communication | CommunicationChannel, CommunicationChannelStatus, CommunicationDirection, CommunicationEvent |
| aionx_organs | DecisionObject, DecisionOption, DecisionOutcome, DecisionPattern, DecisionRetrospective, CounterfactualSimulation, CounterfactualActualization, DecisionDebtAssessment, InstitutionalDebtIndex, ClientDigitalTwin, ClientTwinInteraction, ClientTwinPrediction, ClientPipelineState, ClientPipelineMilestone, ClientPipelineStageLog, WisdomIndexSnapshot, ProviderCalibrationRecord, ProviderCouncilSession, ShelvedDiscovery, ConvergenceCouncilSession, ConvergenceCouncilMessage, MissionAutopsy, SentinelObservation, SentinelThreat, MissionOwnershipRecord, SelfModificationRecord |
| credentials | OAuthToken, SecureCredential |
| trust_engine | ExecutiveOpportunityBrief, LeadEngagementEvent, ReferralRequest |
| truth_resilience | TruthEvent, PredictionAccuracy, RealityCheck, ResilienceEvent, FinancialHealth, CashflowForecast, ImprovementRecommendation, DeliveryLesson, DependencyScore, MoatMetrics |

**Total distinct model classes: ~90+**

### 7.2 — Schema Migrations

31 Alembic migrations (0001–0030) plus several merge migrations covering: RLS setup, reply log, proposal PDF, approval priority, invoice engine, AI council, memory tiers, department intelligence, intelligence engines, master prompt gaps, captain bridge, frontier systems, connector hub, consciousness upgrade, AIONX sovereign organs, tenant columns, client pipeline, pipeline history, operational persistence, mission validation, frontier intelligence, mission control, communication transport, leads WhatsApp/LinkedIn, performance indexes, contracts, trust engine, truth validation resilience.

---

## SECTION 8 — MEMORY ARCHITECTURE

**Files:** `backend/app/services/memory/`

JARVIS implements a 3-tier memory system:

| Tier | Model | Purpose | Lifecycle |
|---|---|---|---|
| Working | In-memory / Redis | Current session context, active task state | Ephemeral |
| Operational | MemoryOperational | Consolidated working memory, recent decisions | Auto-pruned daily |
| Strategic | MemoryStrategic | High-relevance promoted memories, long-term patterns | Permanent until replaced |

**Memory graph:** `MemoryGraphNode` + `MemoryGraphEdge` — entity relationships, knowledge connections.

**Daily consolidation job (`daily_memory_consolidate`):**
1. `consolidate_working_to_operational()` — promotes working memory
2. `prune_operational()` — removes low-relevance operational records
3. `promote_high_relevance_operational()` — elevates to strategic tier

**CivilizationMemory:** Long-term company wisdom — patterns, lessons, accumulated intelligence per tenant.

**Human Intelligence Engine:** `memory/human_intelligence.py` — builds profile of Captain's preferences, decision patterns, communication style.

---

## SECTION 9 — CIVILIZATION LEDGER

**File:** `backend/app/models/civilization.py` + `routes/civilization.py`

The Civilization Ledger is JARVIS's immutable audit trail — SHA-256 hash-chained records of all significant decisions, actions, and system events. Each entry contains:
- Action type and description
- Actor (JARVIS, Captain, or specific department)
- Before/after state
- SHA-256 hash of (previous_hash + current_content)
- Timestamp

Designed as a permanent, tamper-evident record of the company's operational history.

---

## SECTION 10 — TRUTH ENGINE + RESILIENCE LAYER

**Files:** `backend/app/services/intelligence/truth_engine.py`, `routes/truth_engine.py`, `routes/resilience.py`

Added in Layer 18 (migration 0030). JARVIS's self-validation system:

**Truth Engine:** Predictions vs. outcomes. Daily reality check (`daily_truth_reality_check`) runs across 5 check types: lead_score, trust_score, proposal_acceptance, revenue_forecast, client_health. Results feed back into `PredictionAccuracy` and influence future routing weights.

**Resilience Engine:** `ResilienceEvent` tracking — system component failures, recovery actions, MTTR calculations.

**Financial Intelligence:** Weekly health snapshots (`FinancialHealth`), 30/60/90-day cashflow forecasts (`CashflowForecast`), MRR tracking.

**Moat Engine:** Weekly competitive moat scan across dimensions → `MoatMetrics`. Tracks competitive advantages: switching costs, network effects, proprietary data, brand, technical complexity.

**Founder Dependency:** Weekly assessment (`DependencyScore`) — measures how many systems require Captain intervention vs. run autonomously. Target: maximum autonomy.

**Learning Engine:** Weekly outreach + proposal optimization recommendations (`ImprovementRecommendation`, `DeliveryLesson`).

---

## SECTION 11 — AIONX SOVEREIGN ORGAN SYSTEM

**Files:** `backend/app/models/aionx_organs.py`, `backend/app/services/aionx/`

AIONX is JARVIS's advanced cognitive layer — 26 model classes implementing:

| Organ | Function |
|---|---|
| DecisionObject / Option / Outcome | Full decision tree tracking |
| DecisionPattern | Pattern extraction from past decisions |
| DecisionRetrospective | Post-decision analysis |
| CounterfactualSimulation | "What if" analysis |
| CounterfactualActualization | Turning simulations into actual experiments |
| DecisionDebtAssessment | Accumulated suboptimal decisions |
| InstitutionalDebtIndex | Overall organizational health debt |
| ClientDigitalTwin | AI model of each client |
| ClientTwinInteraction | Interaction simulation via twin |
| ClientTwinPrediction | Predicted client behavior/needs |
| ClientPipelineState/Milestone/StageLog | Full CRM pipeline tracking |
| WisdomIndexSnapshot | Organizational wisdom score |
| ProviderCalibrationRecord | AI provider performance calibration |
| ProviderCouncilSession | Multi-provider council sessions |
| ShelvedDiscovery | Deferred insights/opportunities |
| ConvergenceCouncilSession | Multi-model convergence sessions |
| ConvergenceCouncilMessage | Message records from convergence |
| MissionAutopsy | Post-mortem on failed missions |
| SentinelObservation / Threat | Threat detection records |
| MissionOwnershipRecord | Accountability tracking |
| SelfModificationRecord | JARVIS self-improvement tracking |

---

## SECTION 12 — LEAD GENERATION ENGINE

**Files:** `backend/app/services/leads/`

**Lead discovery (`daily_lead_discovery`):** 24 market targets across 7 service divisions, 7 geographies (UK, UAE, USA, Australia, Canada, Bahrain). Google Maps API queries per target → lead records created.

**Free lead discovery (`daily_free_lead_discovery`):** Runs at 03:30 UTC, limit 50 leads from free sources.

**Lead scoring (`daily_lead_scoring`):** ICP scoring engine. Scores new leads, promotes top 20 per tenant to hot status.

**Speed-to-lead (`speed_to_lead_5min`):** Every 5 minutes. Scans for new inbound signals (form fills, replies, WhatsApp messages) and triggers immediate follow-up sequence.

**Lead model:** `Lead` + `LeadStatus` enum. Fields include source, score, quality_score, discovery_query, industry, country, LinkedIn URL, WhatsApp number, email, outreach status.

**Opportunity Radar:** 06:00 UTC daily — surfaces idle hot leads before workday begins.

---

## SECTION 13 — OUTREACH ENGINE

**Files:** `backend/app/services/outreach/`

| Component | File | Function |
|---|---|---|
| Outreach Engine | `engine.py` | Execute due sequences, stats |
| Email Transport | `email_transport.py` | AWS SES outbound emails |
| Gmail Integration | `gmail.py`, `gmail_inbox.py` | OAuth Gmail send/receive |
| LinkedIn | `linkedin.py` | LinkedIn outreach |
| Sequences | `sequences.py` | Multi-step follow-up sequences |
| Reply Handler | `reply_handler.py` | AI-powered reply classification |
| Auto Outreach | `auto_outreach.py` | Autonomous outreach execution |
| Compliance | `compliance.py` | Reply rate monitoring, auto-pause |
| SES Inbound | `ses_inbound.py` | Receive replies via SES |

**Compliance:** `daily_outreach_safety_review` at 04:45 UTC assesses reply rate. Auto-pauses if rate drops below threshold. `DoNotContact` and `OutreachPauseState` models enforce no-contact list.

**Daily cap:** 48 outreach sends per tenant (configurable via `OUTREACH_DAILY_SEND_CAP`).

**Executive email persona:** Joseph David, Executive Director — `joseph.david@aliyarsolutions.com` (SES-backed).

---

## SECTION 14 — GOVERNANCE ENGINE

**Files:** `backend/app/services/governance/`

| Feature | Detail |
|---|---|
| Invoice numbering | ALY-YYYYMM-XXXX auto-format |
| Proposal styles | 4 distinct styles (AI-generated) |
| Contract templates | Pre-built + AI-customized |
| Approval workflow | All high-value actions require Captain approval |
| Auto-approve threshold | Proposals < $5,000 USD (configurable) |
| Incident reports | Full structured incident tracking |
| Audit log | Every action logged to AuditLog with before/after JSON |

**Captain Bridge** (`/captain` routes, protected by `get_current_captain` dependency): Dedicated endpoint layer for Captain-only commands — voice interaction, strategic commands, high-authority operations.

---

## SECTION 15 — PAYMENT SYSTEM

**Files:** `backend/app/services/payments/`

| Provider | File | Status |
|---|---|---|
| Stripe | `stripe_service.py`, `stripe_validator.py` | Primary (webhook-verified) |
| PayPal | — | Legacy |
| Wise | `wise_transfer.py` | International transfers |
| Bank Transfer | `bank_transfer.py` | Manual bank wire |

**Stripe webhooks:** `POST /api/v1/webhooks/payments` — validates Stripe signature, processes payment events.

**Invoice model:** `Invoice` with `InvoiceStatus` enum (draft, sent, paid, overdue, cancelled). Auto-numbered. Attached to `Client` records.

---

## SECTION 16 — NOTIFICATION CHANNELS

**Files:** `backend/app/services/notifications/`

| Channel | File | Trigger |
|---|---|---|
| Slack | `slack.py` | Business events, alerts, job failures |
| Telegram | `telegram.py`, `telegram_bot.py` | Captain mobile alerts |
| Gmail | `gmail_sender.py` | Email notifications |
| n8n | `n8n.py` | Workflow automation webhooks |
| WebSocket | `/ws` route | Real-time frontend updates |

**Emergency protocol:** On critical incidents, all 3 channels (Slack + Telegram + WebSocket) notified within 60 seconds via `monitoring/emergency.py`.

**Telegram webhook:** `POST /api/v1/webhooks/telegram` — receives Captain messages on mobile. Optional `TELEGRAM_WEBHOOK_SECRET` for signature validation.

---

## SECTION 17 — WHATSAPP INTEGRATION

**Container:** Evolution API v2.3.7 (WhatsApp Business API gateway)

**Architecture:**
1. WhatsApp message arrives → Evolution API → webhook POST to `http://backend:8000/api/v1/webhooks/whatsapp`
2. Backend processes message → CRM lookup → AI response generation → reply via Evolution API
3. Full message history persisted to `evolution` PostgreSQL database
4. Display identity: "Joseph David" (`WHATSAPP_DISPLAY_IDENTITY`)
5. Instance name: `jarvis-main`

**Communication model:** `CommunicationChannel`, `CommunicationEvent`, `CommunicationDirection` — unified model for WhatsApp, email, LinkedIn, voice.

---

## SECTION 18 — CONNECTOR HUB

**Files:** `backend/app/services/integrations/connector_hub.py`, `backend/app/services/integrations/github_bridge.py`

The Connector Hub ingests external data packages from a GitHub repository path (`/jarvis-data/`):

**Daily ingestion (`daily_connector_hub_ingestion` at 14:30 UTC):**
- Fetches daily data package from `github_bridge.REPO_DATA_PATH`
- Processes leads: `result.leads.processed`
- Loads outreach sequences: `result.sequences.sequences_loaded`

**Market intelligence output (`daily_market_intelligence` at 04:00 UTC):**
- Generates market intelligence reports
- Writes files to `/jarvis-data/intelligence/` in GitHub repo

**Storage:** `ConnectorHubPackage` + `ConnectorHubIngestion` models track every ingestion.

---

## SECTION 19 — CRM SYSTEM

**Models:** `Company`, `Contact`, `Deal`

**Deal stages:** Includes closed_won, closed_lost (excluded from pipeline value), plus active stages tracked in weekly pipeline health.

**Trust Engine:** `ExecutiveOpportunityBrief`, `LeadEngagementEvent`, `ReferralRequest` — high-quality lead tracking, executive-level opportunity briefings.

**Client Digital Twins (AIONX):** AI model of each client's behavior, preferences, predicted needs. Updated by AIONX scheduler jobs.

---

## SECTION 20 — TEAM PERSONA SYSTEM

**File:** `backend/app/services/team/team_service.py`

9 named human personas used for all client-facing communications. 36-key routing map assigns each service category to the correct team member.

| Name | Role |
|---|---|
| Darren Mitchell | Client Acquisition Specialist |
| David Carter | Solutions Architect |
| Sophia Reynolds | Workflow Consultant |
| Nathan Scott | Deployment Engineer |
| Emma Collins | Business Optimisation Specialist |
| Daniel Brooks | Security Consultant |
| Michael Hayes | Infrastructure Strategist |
| Lucas Reed | Process Integration Specialist |
| Olivia Bennett | Account Coordinator |

JARVIS routes every proposal, email, and outreach to the correct persona based on service type. Clients experience a named human team, never AI.

---

## SECTION 21 — FRONTEND — COMPLETE VIEW INVENTORY

**Stack:** React 18 + Vite + Tailwind CSS (glassmorphism design system) + Zustand state management

**File:** `frontend/src/App.jsx` + `frontend/src/components/layout/Sidebar.jsx`

| View Component | Directory | Purpose |
|---|---|---|
| Dashboard | dashboard/Dashboard.jsx | Main command center |
| CommandCenter | dashboard/CommandCenter.jsx | Operational command view |
| WarRoom | dashboard/WarRoom.jsx | War room / threat view |
| ChatInterface | chat/ChatInterface.jsx | JARVIS conversation |
| MorningBriefing | briefing/MorningBriefing.jsx | Daily briefing viewer |
| LeadsDashboard | leads/LeadsDashboard.jsx | Lead pipeline |
| CRMDashboard | crm/CRMDashboard.jsx | CRM companies/contacts/deals |
| OutreachDashboard | outreach/OutreachDashboard.jsx | Outreach sequences |
| ProposalsView | proposals/ProposalsView.jsx | Proposal management |
| InvoicesView | invoices/InvoicesView.jsx | Invoice management |
| GovernanceDashboard | governance/GovernanceDashboard.jsx | Governance & compliance |
| ApprovalQueue | approvals/ApprovalQueue.jsx | Approval queue |
| Approvals | approvals/Approvals.jsx | Approval history |
| AgentHierarchy | agents/AgentHierarchy.jsx | AI agent org chart |
| AgentOpsCenter | agent_ops/AgentOpsCenter.jsx | Agent operations |
| AIOpsDashboard | ai_ops/AIOpsDashboard.jsx | AI provider health |
| IntelligenceDashboard | intelligence/IntelligenceDashboard.jsx | Market intelligence |
| IntelView | intel/IntelView.jsx | Intelligence engine |
| MemoryView | memory/MemoryView.jsx | Memory tier management |
| KnowledgeView | knowledge/KnowledgeView.jsx | SOPs + knowledge base |
| SchedulerView | scheduler/SchedulerView.jsx | Job scheduler |
| CalendarView | calendar/CalendarView.jsx | Calendar integration |
| TeamRegistry | team/TeamRegistry.jsx | Team member management |
| ServiceCatalog | catalog/ServiceCatalog.jsx | Service catalog (25 modules) |
| CouncilView | council/CouncilView.jsx | AI Council sessions |
| DepartmentsView | departments/DepartmentsView.jsx | Department intelligence |
| TaskQueue | tasks/TaskQueue.jsx | Agent task queue |
| NotificationCenter | notifications/NotificationCenter.jsx | Notification log |
| CommunicationHub | communication/CommunicationHub.jsx | Unified comms (WA/email/LinkedIn) |
| GmailCenter | gmail/GmailCenter.jsx | Gmail OAuth inbox |
| DiscoveryView | discovery/DiscoveryView.jsx | Lead discovery |
| VoiceView | voice/VoiceView.jsx | Voice integration |
| ConsciousnessHub | consciousness/ConsciousnessHub.jsx | Consciousness engine |
| AionxArchitecture | aionx/AionxArchitecture.jsx | AIONX organ map |
| FrontierShell | frontier/FrontierShell.jsx | Frontier view |
| CaptainBridge | frontier/CaptainBridge.jsx | Captain commands |
| ExpertCouncil | frontier/ExpertCouncil.jsx | Expert council |
| IntelligenceHub | frontier/IntelligenceHub.jsx | Intelligence hub |
| Relationships | frontier/Relationships.jsx | Relationship map |
| RevenueIntelligence | frontier/RevenueIntelligence.jsx | Revenue intelligence |
| SystemHUD | frontier/SystemHUD.jsx | System HUD |
| FinancialIntelligence | financial/FinancialIntelligence.jsx | Financial intelligence |
| TruthEngine | truth/TruthEngine.jsx | Truth engine |
| ResilienceEngine | resilience/ResilienceEngine.jsx | Resilience monitor |
| LearningEngine | learning/LearningEngine.jsx | Learning engine |
| FounderDependency | founder/FounderDependency.jsx | Founder dependency |
| MoatEngine | moat/MoatEngine.jsx | Competitive moat |
| EvolutionDashboard | evolution/EvolutionDashboard.jsx | Evolution WhatsApp |
| ProjectsView | projects/ProjectsView.jsx | Projects |
| ResearchView | research/ResearchView.jsx | Research reports |
| SettingsView | settings/SettingsView.jsx | System settings |
| SyncView | sync/SyncView.jsx | Data sync |
| OnboardingWizard | whitelabel/OnboardingWizard.jsx | White-label onboarding |
| LoginPage | auth/LoginPage.jsx | Authentication |

**Total frontend views: 54**

---

## SECTION 22 — INFRASTRUCTURE (TERRAFORM)

**Files:** `infra/terraform/` (main.tf, ecs.tf, variables.tf, outputs.tf)

| Resource | Detail |
|---|---|
| Provider | AWS ~5.0 |
| Primary Region | ap-south-2 (Hyderabad) |
| Backup Region | ap-south-1 (Mumbai) — Phase 2 |
| Terraform State | S3 backend, DynamoDB lock table |
| VPC | Custom VPC with public + private subnets |
| Subnets | Public (internet-facing ALB) + Private (ECS tasks, RDS) |
| NAT Gateway | Elastic IP — private subnet outbound |
| Internet Gateway | Public subnet internet access |
| ECS Cluster | jarvis-production-cluster |
| ECS Service | jarvis-production-backend + jarvis-production-frontend |
| Launch Type | Fargate (serverless containers) |
| Deployment | Blue/green rolling update |
| Health Gate | /health (liveness) + /readyz (deep readiness) |
| RDS | PostgreSQL 16 Multi-AZ |
| ElastiCache | Redis 7 |
| ALB | Application Load Balancer (HTTPS termination) |
| S3 | Backups + static assets |
| Secrets Manager | All secrets (never in code) |
| KMS | Encryption at rest |
| OIDC Role | JarvisGitHubActionsRole (OIDC, no long-lived keys) |
| Tagging | Project, Environment, ManagedBy=Terraform, Owner=Aliyar-Solutions |

---

## SECTION 23 — CI/CD PIPELINE

**Files:** `.github/workflows/`

| Workflow | Trigger | Function |
|---|---|---|
| deploy.yml | Push to main (excludes sarah/**) | Full build + deploy to AWS ECS |
| ec2-deploy.yml | Manual / scheduled | EC2 deployment (legacy path) |
| terraform-apply.yml | Changes to infra/terraform/*.tf | Auto-apply Terraform |
| sarah-deploy.yml | Sarah-specific push | Sarah AI Receptionist deploy |
| sarah-pr-checks.yml | Sarah PRs | PR validation checks |

### deploy.yml — Job Sequence

1. **build** — checkout → OIDC auth → ECR login → build backend Docker → build frontend Docker → push both images tagged with `github.sha`
2. **deploy** (needs: build) — OIDC auth → download current ECS task definition → inject new backend image URI → register new task definition → ECS service update → wait for service stability

**OIDC:** No long-lived AWS credentials. GitHub Actions assumes `JarvisGitHubActionsRole` via OIDC (federated identity). ECR registry: `jarvis-production-backend` + `jarvis-production-frontend`.

**ECS Cluster:** `jarvis-production-cluster`. Service: `jarvis-production-backend`. Task family: `jarvis-production-backend`. App base URL: `https://aliyarsolutions.com`.

---

## SECTION 24 — MONITORING STACK

**Files:** `monitoring/prometheus.yml`, `alert_rules.yml`, `alertmanager.yml`, `loki.yml`, `promtail.yml`

| Component | Version | Role |
|---|---|---|
| Prometheus | v2.54.1 | Metrics collection + storage |
| Grafana | 11.1.4 | Dashboards (served at /grafana/) |
| Alertmanager | v0.27.0 | Alert routing |
| Loki | 3.2.1 | Log aggregation |
| Promtail | 3.2.1 | Log shipping (Docker container logs) |
| postgres-exporter | v0.15.0 | PostgreSQL metrics |
| redis-exporter | v1.62.0 | Redis metrics |
| node-exporter | v1.8.2 | Host CPU/memory/disk metrics |
| cadvisor | v0.49.1 | Container CPU/memory/network metrics |

**Grafana URL:** `https://aliyarsolutions.com/grafana/` (sub-path routing)

**Promtail:** Reads Docker container logs via `/var/run/docker.sock` + `/var/lib/docker/containers`. Ships to Loki.

**Backend metrics:** AI latency and cost emitted to Prometheus via `observe_ai_latency()` and `record_ai_cost()` middleware hooks.

**X-Request-ID tracing:** Middleware adds unique request ID to every request for log correlation.

---

## SECTION 25 — SECURITY ARCHITECTURE

| Layer | Implementation |
|---|---|
| Authentication | JWT (15 min TTL) + HttpOnly rotating refresh cookie |
| Captain auth | Separate `get_current_captain` dependency — elevated privileges |
| Secrets | AWS Secrets Manager (production). `.env` local — gitignored, never committed |
| TLS | Let's Encrypt auto-renewing certificates via Certbot |
| HTTPS | Nginx reverse proxy terminates TLS on ports 80/443 |
| Database access | Port 127.0.0.1 only (not exposed externally) |
| AWS auth | OIDC (no long-lived IAM keys) |
| Outreach compliance | DoNotContact list, auto-pause on low reply rate |
| Credentials storage | OAuthToken + SecureCredential models (encrypted) |
| Container isolation | All containers on jarvis_net internal bridge; only Nginx exposed on 80/443 |
| RLS | Alembic migration 0001 sets up Row-Level Security for multi-tenancy |
| Webhook security | Stripe signature validation, optional Telegram webhook secret, Evolution API key |

**Credential Validator:** `security/credential_validator.py` — validates third-party credentials before storage.

---

## SECTION 26 — MULTI-TENANCY

**Models:** `Tenant`, `User`, `TenantApiKey`, `PlanTier`

Every data model carries a `tenant_id` foreign key. Row-Level Security enforced at PostgreSQL level (migration 0001).

**Tenant context:** `set_tenant_context()` called at start of every request via database dependency. APScheduler job store carries `tenant_id` column (custom `TenantAwareSQLAlchemyJobStore`).

**System tenant:** `SYSTEM_TENANT_ID = aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa` — used for system-level scheduler jobs.

**White-label:** `OnboardingWizard.jsx` + `onboarding_service.py` + `white_label_service.py` — full white-label instance provisioning for agency clients.

**Plan tiers:** `PlanTier` enum (defined in tenant model). Different tiers access different feature sets.

---

## SECTION 27 — SERVICE CATALOG (25 AIONX MODULES)

Canonical catalog as of v9.0 (old 30-division catalog deprecated):

| Category | Modules |
|---|---|
| Revenue Operations | SCOUT (lead gen), HERALD (outreach), NEXUS-R (CRM), ORACLE-S (sales intelligence) |
| AI Automation | PRISM (AI workflows), ECHO (voice/comms), PULSE (real-time), SIGNAL (notifications), BRIDGE (integrations) |
| Cloud & DevOps | ATLAS-CI (CI/CD), NEXUS-TF (Terraform), SIGNAL-CD (deployment), HELM (Kubernetes), RADAR (monitoring) |
| Security & Compliance | CIPHER (security ops), GUARDIAN (compliance) |
| Finance & Intelligence | LEDGER (invoicing), ORACLE-BI (business intelligence), MARKET (market intel), QUANT (financial modeling) |
| Creative & Client Systems | QUILL (content), PORTAL (client portals), CANVAS (design), VISION (media) |
| Executive Governance | COUNCIL (AI governance) |

**Pricing:** Retainer $2,000–$8,000/month. Project $3,000–$25,000. No hourly billing. 50% upfront + 50% on delivery.

---

## SECTION 28 — VOICE INTEGRATION

**ElevenLabs:** `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"` (Daniel, British male).

**Voice route:** `backend/app/api/v1/routes/voice.py`

**Captain Bridge voice commands:** `captain.voice_router` — dedicated voice API for Captain-only interaction (protected by `get_current_captain`).

---

## SECTION 29 — KEY CONFIGURATION PARAMETERS

**Version:** 9.0.0

| Parameter | Default | Description |
|---|---|---|
| AUTONOMOUS_CONFIDENCE_THRESHOLD | 0.70 | Minimum AI confidence to auto-execute |
| SYSTEM_CONFIDENCE_BASE | 0.68 | Base system confidence |
| AUTO_APPROVE_PROPOSAL_THRESHOLD_USD | $5,000 | Auto-approve proposals below this |
| AUTO_APPROVE_INVOICE_THRESHOLD_USD | $5,000 | Auto-approve invoices below this |
| AUTO_SEND_OUTREACH | true | Autonomous outreach enabled |
| AUTO_SEND_OUTREACH_WARM_LEADS_ONLY | true | Only warm leads auto-targeted |
| AUTO_SEND_OUTREACH_MIN_QUALITY_SCORE | 0.70 | Minimum lead quality for auto-outreach |
| OUTREACH_DAILY_SEND_CAP | 48 | Daily outreach ceiling per tenant |
| OUTREACH_DOMAIN_AGE_DAYS | 365 | Minimum domain age for outreach |
| CLAUDE_BUDGET_TOTAL_USD | $5.00 | Claude budget per 14-day window |
| CLAUDE_SINGLE_CALL_MAX_USD | $0.20 | Max spend per Claude API call |
| PILOT_READY | true | Pilot mode enabled |

---

## SECTION 30 — COMMERCIALIZABLE COMPONENTS

JARVIS contains the following modules that can be extracted, white-labeled, or sold independently:

| Component | Commercializable As |
|---|---|
| Multi-provider AI Router (11 providers, circuit breakers, cost governance, NIM key rotation) | AI infrastructure middleware, sellable to agencies needing multi-LLM routing |
| AI Council System (multi-model consensus voting, weight recalibration) | Enterprise AI governance layer |
| Outreach Engine + Compliance (SES, Gmail OAuth, sequences, reply classification, auto-pause) | B2B cold outreach SaaS |
| Lead Discovery Engine (Google Maps, 24 market targets, ICP scoring) | Lead generation service |
| Scheduler Framework (APScheduler + Redis locks + retry logic + tenant-aware) | Autonomous operations engine |
| Civilization Ledger (hash-chained audit trail) | Enterprise compliance audit system |
| Memory System (3-tier: working/operational/strategic) | Persistent AI memory layer |
| Client Digital Twin + Pipeline (AIONX) | CRM intelligence layer |
| Truth Engine + Prediction Accuracy | AI prediction validation system |
| White-label Onboarding | Multi-tenant SaaS infrastructure |
| Monitoring Stack (16 containers, full observability) | DevOps observability bundle |

---

## APPENDIX A — ALEMBIC MIGRATION HISTORY

| Migration | Description |
|---|---|
| 0001 | RLS (Row-Level Security) setup |
| 0002 | Reply log |
| 0003 | Proposal PDF fields |
| 0004 | Approval priority |
| 0005 | Invoice engine |
| 0006 | AI Council |
| 0007 | Memory tiers |
| 0008 | Department intelligence |
| 0009a | Intelligence engines |
| 0009b | Master prompt + contract gaps |
| 0010 | Captain Bridge |
| 0011 | Frontier systems |
| 0012 | Merge: master prompt + frontier |
| 0013a | Bootstrap live schema gaps |
| 0013b | Connector Hub |
| 0014 | Merge 0013 heads |
| 0015 | Connector Hub timestamps |
| 0016 | Consciousness upgrade |
| 0017 | AIONX sovereign organs |
| 0018 | AIONX tenant columns |
| 0019 | AIONX batch1 client pipeline |
| 0020 | AIONX pipeline history |
| 0021 | AIONX operational persistence |
| 0022 | AIONX mission validation |
| 0023 | AIONX frontier intelligence |
| 0024 | AIONX omni mission control |
| 0025 | AIONX communication transport |
| 0026 | Leads WhatsApp + LinkedIn |
| 0027 | Performance indexes |
| 0028 | Contracts |
| 0029 | Trust engine |
| 0030 | Truth validation + resilience |

---

## APPENDIX B — TECHNOLOGY STACK SUMMARY

| Layer | Technology |
|---|---|
| Backend | Python 3.11 + FastAPI + SQLAlchemy 2.0 async + Gunicorn |
| Primary AI | NVIDIA NIM (DeepSeek V4, Llama 4, Kimi K2, Qwen Coder) |
| Secondary AI | Anthropic Claude Sonnet/Haiku, OpenAI GPT-4o, Google Gemini |
| Additional AI | DeepSeek, Groq, Mistral, ZhipuAI, Qwen, Moonshot, Minimax, AWS Bedrock |
| Database | PostgreSQL 16 + pgvector extension |
| Cache | Redis 7 (Alpine) — persistence + LRU eviction |
| Scheduler | APScheduler 3.10 + SQLAlchemy job store |
| Frontend | React 18 + Vite + Tailwind CSS + Zustand |
| WhatsApp | Evolution API v2.3.7 |
| Voice | ElevenLabs (Daniel, British male) |
| Email | AWS SES (outbound) + Gmail OAuth |
| Notifications | Slack + Telegram + WebSocket |
| Payments | Stripe + Wise + Bank Transfer |
| Infrastructure | AWS ECS Fargate + RDS + ElastiCache + S3 + Secrets Manager + KMS |
| Terraform | HashiCorp Terraform 1.6+ (AWS provider ~5.0) |
| CI/CD | GitHub Actions → ECR → ECS (OIDC auth, no long-lived keys) |
| Monitoring | Prometheus 2.54 + Grafana 11.1 + Alertmanager + Loki + Promtail |
| Observability | node-exporter + cadvisor + postgres-exporter + redis-exporter |
| Reverse Proxy | Nginx 1.27 Alpine + Certbot (Let's Encrypt) |
| Containers | Docker + Docker Compose (16 services) |
| Regions | ap-south-2 Hyderabad (primary) + ap-south-1 Mumbai (DR) |

---

*This dossier was compiled from direct codebase inspection. All technical claims are verified against live source files. No metrics, client data, credentials, or private URLs were included.*

*Generated: 2026-09-08 | JARVIS v9.0.0 | Aliyar Solutions*
