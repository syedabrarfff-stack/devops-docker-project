# JARVIS API INVENTORY — COMPLETE
_57 route modules | ~411 endpoints | Last audited: 2026-06-19_
_Base URL: https://api.aliyarsolutions.com/api/v1 (prod) | http://localhost:8000/api/v1 (local)_
_All routes registered in: backend/app/api/v1/__init__.py_

## Authentication
- POST /auth/login → JWT token (role: captain) — uses CAPTAIN_USERNAME / CAPTAIN_PASSWORD env vars
- GET  /auth/me → current user info
- Captain routes: `Authorization: Bearer <token>` header required
- WebSocket captain: `?token=<jwt>` query param (browsers can't send headers)

---

## Core AI & Communication

| Module | File | Prefix | Endpoints | Notes |
|--------|------|--------|-----------|-------|
| Chat | chat.py | /chat | 4 | POST / (60/min rate limit) |
| Briefing | briefing.py | /briefing | 5 | GET /morning-ai (JWT), POST /generate (JWT) |
| Council | council.py | /council | 4 | POST /convene (20/min), GET /sessions |
| AI Ops | ai_ops.py | /ai | 11 | GET /health, /providers, /costs |
| WebSocket | ws.py | /ws | — | GET /ws (public), /ws/captain (JWT + ?token=) |
| Consciousness | consciousness.py | /consciousness | 33 | JARVIS self-awareness introspection layer |

---

## CRM & Sales Pipeline

| Module | File | Prefix | Endpoints | Notes |
|--------|------|--------|-----------|-------|
| Leads | leads.py | /leads | 11 | CRUD + pipeline + scoring |
| CRM | crm.py | /crm | 16 | Companies, Contacts, Deals |
| Discovery | discovery.py | /discovery | 8 | POST /run (20/min), POST /free-sources (20/min) |
| Outreach | outreach.py | /outreach | 23 | POST /execute (10/min), /sequences, POST /enroll (30/min) |
| Sync | sync.py | /sync | 5 | POST /apollo (5/min) — Apollo.io import |
| Demos | demos.py | /demos | 3 | POST /generate + auto-email if prospect_email provided |
| Trust | trust.py | /trust | 6 | POST /briefs/generate, POST /engagement, GET /score/{lead_id}, POST /referrals/generate |
| Calls | calls.py | /calls | 3 | Voice call room management |
| Communication | communication.py | (root) | 9 | Multi-channel communication events |
| Intel | intel.py | /intel | 1 | Market intelligence queries |

---

## Governance & Revenue

| Module | File | Prefix | Endpoints | Notes |
|--------|------|--------|-----------|-------|
| Governance | governance.py | /governance | 19 | Proposals, Contracts, Permissions, Incidents |
| Proposals | proposals.py | /proposals | 3 | POST /generate (30/min) |
| Invoices | invoices.py | /invoices | 4 | CRUD |
| Revenue | revenue.py | /revenue | 10 | GET /clients, /mrr, /pipeline |
| Clients | clients.py | /clients | 5 | CRUD + auto welcome email on create |
| Payments | payments.py | /payments | 4 | Stripe links + /webhook handler (2 routers) |
| Pricing | pricing.py | /pricing | 2 | Service pricing matrix |
| Economics | economics.py | /economics | 1 | AI cost ledger, infrastructure costs |
| Whitelabel | whitelabel.py | /whitelabel | 13 | White-label client onboarding |
| Pilot | pilot.py | /pilot | 2 | Pilot program management |

---

## AI Intelligence Layer

| Module | File | Prefix | Endpoints | Notes |
|--------|------|--------|-----------|-------|
| Intelligence | intelligence.py | /intelligence | 33 | Tech radar, market research, optimizer |
| AIONx | aionx.py | /aionx | 120 | Decisions, digital twins, mission control, threats |
| AIONX Batch 1 | batch1.py | /batch1 | 6 | Batch1 client pipeline orchestration |
| Frontier | frontier.py | (root) | 32 | Frontier intelligence cascade, threats scan |
| Departments | departments.py | /departments | 32 | Department intelligence officers |
| Innovation | innovation.py | /innovation | 5 | Innovation queue, status tracking |
| Civilization | civilization.py | /civilization | 3 | Civilization ledger operations |
| Memory | memory.py | /memory | 11 | Operational + strategic memory graphs |
| Knowledge | knowledge.py | /knowledge | 7 | SOPs, learnings, KB |
| Connector Hub | connector_hub.py | /connector-hub | 6 | External data ingestion packages |

---

## Infrastructure & Operations

| Module | File | Prefix | Endpoints | Notes |
|--------|------|--------|-----------|-------|
| System | system.py | /system | 2 | GET /hud (JWT), POST /self-heal (JWT) |
| Captain | captain.py | /captain | 15 | All JWT-locked at router level (2 routers) |
| Scheduler | scheduler.py | /scheduler | 8 | Cron/interval/oneshot jobs (JWT) |
| Approvals | approvals.py | /approvals | 7 | Captain approval queue + audit trail |
| Emergency | emergency.py | /emergency | 6 | POST /incidents (JWT), POST /alert (JWT) |
| Notifications | notifications.py | /notifications | 6 | History, channels |
| Agents | agents.py | /agents | 5 | Agent registry |
| Agent Ops | agent_ops.py | /agent-ops | 8 | Agent lifecycle operations |
| Calendar | calendar.py | /calendar | 5 | Calendar sync + scheduling |
| Tasks | tasks.py | /tasks | 10 | Task queue management |
| Tenancy | tenancy.py | /tenancy | 4 | Tenant management |
| Team | team.py | /team | 7 | Team member management |
| Catalog | catalog.py | /catalog | 8 | 30-division service catalog |
| Jarvis | jarvis.py | /jarvis | 17 | Core JARVIS system ops + HUD |

---

## Integrations & External

| Module | File | Prefix | Endpoints | Notes |
|--------|------|--------|-----------|-------|
| Gmail | gmail.py | /gmail | 7 | OAuth + message management |
| SES Inbound | ses_inbound.py | (root) | 2 | POST /ses_inbound — SES reply handling |
| Telegram | telegram_webhook.py | /telegram | 2 | POST /webhook — bot handler |
| Voice | voice.py | /voice | 2 | Voice call integration |

---

## Health Probes (registered at app root, not /api/v1)
- GET /health — liveness (ECS gate 1)
- GET /readyz — deep readiness: DB + Redis check (ECS gate 2)
- GET /api/v1/health — API-prefixed alias

---

## AI Provider Routing — COMPLETE TABLE
_File: backend/app/services/ai/router.py_
_**NVIDIA NIM is the PRIMARY provider for most task types** — not Anthropic_

### 15 Task Types

| Task Type | Primary Model | Full Chain (in order) |
|-----------|--------------|----------------------|
| CODE | nvidia/deepseek-v4-pro | → nvidia/qwen-coder → nvidia/deepseek-v4-flash → nvidia/llama-4-maverick → anthropic/claude-haiku → openai/gpt-4o |
| RESEARCH | nvidia/deepseek-v4-pro | → nvidia/kimi-k2 → nvidia/llama-4-maverick → nvidia/deepseek-v4-flash → anthropic/claude-sonnet |
| REASONING | nvidia/deepseek-v4-pro | → nvidia/llama-4-maverick → nvidia/kimi-k2 → anthropic/claude-sonnet |
| FAST | nvidia/llama-4-scout | → nvidia/deepseek-v4-flash → nvidia/mistral-medium → nvidia/llama-3-3 → openai/gpt-4o-mini |
| LONG_CONTEXT | nvidia/kimi-k2 | → nvidia/llama-4-maverick → nvidia/deepseek-v4-pro → anthropic/claude-sonnet → openai/gpt-4o |
| MULTILINGUAL | nvidia/llama-4-maverick | → nvidia/qwen-coder → nvidia/mistral-medium → zhipuai/glm-5-1 → openai/gpt-4o |
| MATH | nvidia/deepseek-v4-pro | → nvidia/llama-4-maverick → nvidia/deepseek-v4-flash → openai/gpt-4o |
| GENERAL | nvidia/llama-4-maverick | → nvidia/llama-4-scout → nvidia/llama-3-3 → nvidia/mistral-medium → nvidia/deepseek-v4-flash |
| ANALYSIS | nvidia/deepseek-v4-pro | → nvidia/llama-4-maverick → nvidia/kimi-k2 → anthropic/claude-sonnet → openai/gpt-4o |
| STRATEGY | anthropic/claude-sonnet | → nvidia/deepseek-v4-pro → nvidia/llama-4-maverick → nvidia/kimi-k2 |
| SALES | anthropic/claude-sonnet | → nvidia/llama-4-maverick → nvidia/llama-4-scout → nvidia/deepseek-v4-pro → nvidia/mistral-medium |
| MULTIMODAL | openai/gpt-4o | → nvidia/llama-4-maverick → google/gemini-pro |
| REALTIME | nvidia/llama-4-scout | → nvidia/deepseek-v4-flash → nvidia/mistral-medium → nvidia/llama-3-3 |

### Provider Registry (11 providers)

| Provider | Env Key | Models |
|----------|---------|--------|
| NVIDIA NIM | NVIDIA_API_KEY | deepseek-v4-pro, kimi-k2, llama-4-maverick, llama-4-scout, deepseek-v4-flash, mistral-medium, llama-3-3, qwen-coder |
| Anthropic | ANTHROPIC_API_KEY | claude-sonnet-4-6 (claude-sonnet), claude-haiku-4-5 (claude-haiku) |
| OpenAI | OPENAI_API_KEY | gpt-4o, gpt-4o-mini |
| Google | GOOGLE_API_KEY | gemini-pro |
| DeepSeek | DEEPSEEK_API_KEY | deepseek-chat, deepseek-coder |
| Groq | GROQ_API_KEY | llama-3-3 (direct, not via NIM) |
| Mistral | MISTRAL_API_KEY | mistral-medium (direct) |
| ZhipuAI | ZHIPUAI_API_KEY | glm-5-1 |
| Qwen | (via extra_providers.py) | qwen models |
| Moonshot | MOONSHOT_API_KEY | moonshot models |
| MiniMax | MINIMAX_API_KEY | minimax models |
| AWS Bedrock | USE_AWS + AWS creds | claude via Bedrock |

### Circuit Breaker
- 5 consecutive failures → provider circuit OPEN for 60 seconds
- Cost tracked per call, per provider, per task type
- Files: cost_tracker.py, cost_governance.py, health_monitor.py

### Auto-Detection
- `detect_task_type(prompt)` in router.py auto-classifies prompts
- Matches keywords → selects appropriate task type
- Fallback: GENERAL

---

## Migration Chain (current: 0029)
0001 RLS → 0002 reply_log → 0003 proposal_pdf → 0004 approval_priority → 0005 invoice_engine → 0006 ai_council → 0007 memory_tiers → 0008 department_intelligence → 0009 intelligence_engines → 0010 captain_bridge → 0011 frontier_systems → 0012 merge → 0013 bootstrap/connector_hub → 0014 merge → 0015 timestamps → 0016 consciousness → 0017 aionx_sovereign → 0018 aionx_tenant → 0019 batch1_pipeline → 0020 pipeline_history → 0021 operational_persistence → 0022 mission_validation → 0023 frontier_intelligence → 0024 omni_mission → 0025 communication → 0026 leads_channels → 0027 performance_indexes → 0028 contracts → **0029 trust_engine**

Next migration will be: **0030_[name].py** with down_revision = '0029_trust_engine'
