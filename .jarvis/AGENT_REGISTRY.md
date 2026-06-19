# JARVIS — AGENT REGISTRY
_Complete map of all AI agents, human personas, scheduled jobs, and model routing._
_Last audited: 2026-06-19_

## AI Model Router — Actual Production Routing
_File: backend/app/services/ai/router.py_

**CRITICAL:** NVIDIA NIM is the PRIMARY provider. The older "Claude-first" documentation was wrong.
- NVIDIA NIM routes DeepSeek V4, Kimi K2, Llama 4, Mistral, Qwen through a single API endpoint
- Claude is PRIMARY only for STRATEGY and SALES task types
- Anthropic is fallback for CODE, RESEARCH, REASONING, ANALYSIS, LONG_CONTEXT

### Model Performance Roles (via NVIDIA NIM unless noted)

| Model | Role | Task Types |
|-------|------|-----------|
| deepseek-v4-pro | Deep analytical work, code, math | CODE (P1), RESEARCH (P1), REASONING (P1), ANALYSIS (P1), MATH (P1) |
| kimi-k2 | Extreme long context (1M tokens), synthesis | LONG_CONTEXT (P1), RESEARCH (P2) |
| llama-4-maverick | General intelligence, multilingual | GENERAL (P1), MULTILINGUAL (P1), STRATEGY (P3), ANALYSIS (P2) |
| llama-4-scout | Lowest latency, high-throughput | FAST (P1), REALTIME (P1), SALES (P3) |
| deepseek-v4-flash | Fast + capable balance | FAST (P2), REALTIME (P2), CODE (P3) |
| mistral-medium | European languages, operational speed | FAST (P3), MULTILINGUAL (P3), REALTIME (P3) |
| llama-3-3 | 70B balanced general | FAST (P4), GENERAL (P3), REALTIME (P4) |
| qwen-coder | CJK + structured code | CODE (P2), MULTILINGUAL (P2) |
| claude-sonnet-4-6 | Executive communication, strategy | STRATEGY (P1), SALES (P1), fallback for CODE/ANALYSIS |
| claude-haiku-4-5 | Fast Anthropic fallback | CODE (P5) fallback only |
| gpt-4o | Vision/multimodal, last-resort fallback | MULTIMODAL (P1), most task types (last fallback) |
| gpt-4o-mini | Ultra-fast OpenAI | FAST (P5) last fallback |
| gemini-pro | Multimodal, vision | MULTIMODAL (P3) |
| zhipuai/glm-5-1 | CJK language specialization | MULTILINGUAL (P4) |

### Task Type → Primary Model Quick Reference

| Use This | When You Need |
|----------|--------------|
| CODE | nvidia/deepseek-v4-pro |
| STRATEGY | anthropic/claude-sonnet-4-6 |
| SALES | anthropic/claude-sonnet-4-6 |
| FAST | nvidia/llama-4-scout |
| RESEARCH | nvidia/deepseek-v4-pro |
| REASONING | nvidia/deepseek-v4-pro |
| LONG_CONTEXT | nvidia/kimi-k2 |
| ANALYSIS | nvidia/deepseek-v4-pro |
| GENERAL | nvidia/llama-4-maverick |
| MULTILINGUAL | nvidia/llama-4-maverick |
| MATH | nvidia/deepseek-v4-pro |
| REALTIME | nvidia/llama-4-scout |
| MULTIMODAL | openai/gpt-4o |

---

## Human Identity Layer — Client-Facing Team
_File: backend/app/services/team/team_service.py_
_36 service type keys mapped to named team members_

| Name | Role | Service Categories (key examples) |
|------|------|----------------------------------|
| Darren Mitchell | Client Acquisition Specialist | leads, outreach, sales, qualification, crm, demo |
| David Carter | Solutions Architect | cloud, aws, infrastructure, architecture, devops, terraform |
| Sophia Reynolds | Workflow Consultant | automation, ai_automation, workflows, integrations, process |
| Nathan Scott | Deployment Engineer | deployment, cicd, kubernetes, docker, containers |
| Emma Collins | Business Optimisation Specialist | analytics, crm_ops, revenue, reporting, kpi |
| Daniel Brooks | Security Consultant | security, compliance, vulnerability, audit, hardening |
| Michael Hayes | Infrastructure Strategist | scaling, platform, migrations, architecture_strategy |
| Lucas Reed | Process Integration Specialist | api_integration, process_automation, automation_ops |
| Olivia Bennett | Account Coordinator | onboarding, client_success, retention, reporting_ops |

**Routing:** `get_member_for_service(db, service_type)` → normalizes input (lowercase + spaces → _) → returns TeamMember
**Fallback:** "Aliyar Solutions Team" if no match

---

## Operational Agents — Scheduled Jobs
_File: backend/app/services/scheduler/_
_Engine: APScheduler 3.10 + SQLAlchemy persistent job store_

| Job ID | Schedule | Task Type | Output |
|--------|----------|-----------|--------|
| daily_morning_briefing | 07:00 UTC daily | FAST | Executive briefing → Captain (Telegram + WebSocket) |
| daily_lead_score | 02:00 UTC daily | ANALYSIS | trust_score + conversion_probability for all leads |
| weekly_outreach_stats | Monday 08:00 UTC | ANALYSIS | Outreach performance report → Captain |
| weekly_pipeline_health | Sunday 20:00 UTC | STRATEGY | Pipeline + MRR forecast → Captain |
| weekly_tech_radar_scan | Monday 06:00 UTC | RESEARCH | Technology classification (Adopt/Trial/Assess/Hold) |
| daily_optimization_review | 23:00 UTC daily | ANALYSIS | System performance recommendations → Captain |
| biweekly_research_report | Sunday 07:00 UTC | RESEARCH | Market intelligence report → Captain |

---

## AIONx Organs — Autonomous Intelligence Systems
_File: backend/app/services/aionx/ (32 files)_
_Routes: /aionx (120 endpoints), /batch1, /frontier (32 endpoints)_

| Organ | Purpose |
|-------|---------|
| Decision Engine | All significant decisions tracked with options, outcomes, patterns |
| Counterfactual Simulation | "What if" modeling for strategic decisions |
| Decision Debt Assessment | Identifies deferred/accumulating decision debt |
| Client Digital Twin | AI model of each client — predictions, interactions, pipeline state |
| Mission Autopsy | Post-mission analysis — what worked, what failed, why |
| Sentinel Layer | Real-time threat observation and classification |
| Provider Council | Multi-provider deliberation on complex decisions |
| Convergence Council | Cross-organ convergence for system-wide decisions |
| Institutional Wisdom Index | Compounding intelligence from past decisions |
| Self-Modification Records | Tracks system self-improvement actions |
| Mission Ownership | Accountability tracking for all system missions |
| Operational Persistence | Decision memory that survives restarts |

---

## Department Intelligence Officers (DIOs)
_Route: /departments (32 endpoints)_
_Each department has an AI officer for domain queries_

| DIO | Domain | Queries It Handles |
|-----|--------|--------------------|
| Engineering DIO | Code, DevOps, architecture | Code review, system design, debugging |
| Strategy DIO | Positioning, proposals | Competitive analysis, framing |
| Operations DIO | Workflow, CRM | Process optimization, CRM queries |
| Intelligence DIO | Research, trends | Market analysis, technology scanning |
| Client Success DIO | Retention, expansion | Churn risk, upsell opportunities |

---

## VS Code Multi-Model Council
_File: .continue/config.json_

| Model | Provider | Best For |
|-------|----------|----------|
| Claude Sonnet 4.6 | Anthropic | Code implementation (primary) |
| GPT-4o | OpenAI | Architecture review, cross-validation |
| Gemini Pro | Google | Research, long-context analysis |
| DeepSeek Chat | DeepSeek | Fast code generation |
| Groq Llama | Groq | Ultra-fast completions |
| NVIDIA NIM | NVIDIA | Production routing (same as backend) |

**Slash Commands:**
- `/jarvis-state` — current state + pending tasks briefing
- `/new-route` — generate FastAPI route with JARVIS conventions
- `/new-migration` — Alembic migration (next: 0030)
- `/council` — 3-perspective architectural review

---

## Agent Performance Baselines

| Metric | Target | Alert |
|--------|--------|-------|
| Proposal generation | <15s | >30s |
| Contract generation | <20s | >45s |
| Brief generation | <25s | >60s |
| Email delivery (SES) | <3s | >10s |
| Lead scoring per lead | <5s | >15s |
| AI router fallback rate | <5% | >15% |
| Circuit breaker trips/day | 0 | >3 |
| /readyz response | <500ms | >2s |

---

## Communication Routing (External Delivery)
_Email: send_outbound_email() via AWS SES_
_Telegram: POST /telegram/webhook → Captain_
_WebSocket: /ws/captain for real-time Captain updates_

| Trigger | From (persona) | To | Subject |
|---------|---------------|-----|---------|
| Invoice created | Olivia Bennett | client_email | Invoice ALY-YYYYMM-XXXX |
| Proposal generated | Matched team member | client_email | [Service] — [Company] Proposal |
| Proposal accepted | JARVIS automation | client_email | Service Agreement — [Company] |
| Client created | Olivia Bennett | client_email | Welcome to Aliyar Solutions |
| Emergency incident | JARVIS | Captain (Telegram) | JARVIS ALERT: [incident] |
| Morning briefing | JARVIS | Captain (Telegram + WS) | Daily briefing |
