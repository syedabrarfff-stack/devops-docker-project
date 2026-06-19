# JARVIS — AGENT REGISTRY
_Every AI agent and human team persona. Routes, owners, performance baselines._

## AI Model Council (Multi-Model Router)

### Primary Routing (backend/app/services/ai/router.py)

| Task Type | Primary | Fallback 1 | Fallback 2 |
|-----------|---------|-----------|-----------|
| CODE | claude-sonnet-4-6 | deepseek | gpt-4o |
| REASONING | claude-opus | gpt-4o | gemini-pro |
| STRATEGY | claude-opus | gpt-4o | claude-sonnet-4-6 |
| ANALYSIS | claude-opus | gpt-4o | gemini-pro |
| RESEARCH | gemini-pro | gpt-4o | claude-sonnet-4-6 |
| FAST | deepseek-flash | llama-3-3 | gpt-4o-mini |
| LONG_CONTEXT | gemini-pro | kimi-k2 | claude-sonnet-4-6 |

**Important:** Use haiku-4-5 and sonnet-4-6 sparingly. Never use opus unless required by task type.

### Circuit Breaker Status
- Threshold: 5 failures → circuit OPEN for 60 seconds
- All providers: circuit breaker active
- Cost tracked: per call, per provider, per task type

## Human Identity Layer (Client-Facing Agents)

### Routing Map Summary (full map in backend/app/services/team/team_service.py)

| Team Member | Role | Service Categories |
|------------|------|--------------------|
| Darren Mitchell | Client Acquisition Specialist | leads, outreach, sales, qualification |
| David Carter | Solutions Architect | cloud, aws, infrastructure, architecture, devops |
| Sophia Reynolds | Workflow Consultant | automation, ai, workflows, integrations |
| Nathan Scott | Deployment Engineer | deployment, cicd, kubernetes, docker, devops_ops |
| Emma Collins | Business Optimisation Specialist | analytics, crm, revenue, reporting |
| Daniel Brooks | Security Consultant | security, compliance, vulnerability |
| Michael Hayes | Infrastructure Strategist | scaling, platform, migrations |
| Lucas Reed | Process Integration Specialist | api, process, automation_ops |
| Olivia Bennett | Account Coordinator | onboarding, client_success, retention |

### Selection Logic
- `get_member_for_service(db, service_type)` → returns TeamMember or None
- Falls back to "Aliyar Solutions Team" if no match
- Service type normalized: lowercased + spaces → underscores

## Operational Agents (Scheduled)

### daily_morning_briefing (07:00 UTC)
- **Operator:** Intelligence Division
- **Input:** leads, proposals, invoices, system health, alerts
- **Output:** Executive briefing sent to Captain (Telegram + WebSocket)
- **Model:** FAST task type

### daily_lead_score (02:00 UTC)
- **Operator:** Sales Intelligence
- **Input:** All leads without trust scores, engagement events
- **Output:** Updated trust_score + conversion_probability + ready_for_proposal
- **Model:** ANALYSIS task type

### weekly_outreach_stats (Monday 08:00 UTC)
- **Operator:** Operations Division
- **Input:** outreach sequences, email open rates, reply rates
- **Output:** Weekly performance report → Captain
- **Model:** ANALYSIS task type

### weekly_pipeline_health (Sunday 20:00 UTC)
- **Operator:** Revenue Intelligence
- **Input:** proposals, contracts, MRR, pipeline stages
- **Output:** Weekly pipeline + MRR forecast → Captain
- **Model:** STRATEGY task type

### weekly_tech_radar_scan (Monday 06:00 UTC)
- **Operator:** Intelligence Division
- **Input:** Technology landscape (via AI research)
- **Output:** Tech classification — Adopt/Trial/Assess/Hold
- **Model:** RESEARCH task type

### daily_optimization_review (23:00 UTC)
- **Operator:** System Health Division
- **Input:** System metrics, query performance, error rates
- **Output:** Optimization recommendations → Captain
- **Model:** ANALYSIS task type

### biweekly_research_report (Sunday 07:00 UTC)
- **Operator:** Intelligence Division
- **Input:** Market data, competitor signals
- **Output:** Market intelligence report → Captain
- **Model:** RESEARCH task type

## Department Intelligence Officers (DIOs)
_Route: GET/POST /api/v1/departments_

Each department has an AI officer for domain-specific queries:
- Engineering DIO: code review, architecture, DevOps queries
- Strategy DIO: proposal framing, competitive positioning
- Operations DIO: workflow optimization, CRM queries
- Intelligence DIO: market research, trend analysis
- Client Success DIO: retention risk, expansion opportunities

## Agent Performance Baselines

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| Proposal generation time | <15s | >30s |
| Contract generation time | <20s | >45s |
| Brief generation time | <25s | >60s |
| Email delivery (SES) | <3s | >10s |
| Lead scoring (batch) | <5s/lead | >15s/lead |
| AI router fallback rate | <5% | >15% |
| Circuit breaker trips/day | 0 | >3 |

## VS Code Multi-Model Council (Continue Extension)
_Config: .continue/config.json_

| Model | Provider | Use When |
|-------|----------|----------|
| Claude Sonnet 4.6 | Anthropic | Code, implementation (primary) |
| GPT-4o | OpenAI | Cross-validation, second opinion |
| Gemini Pro | Google | Research, long context |
| DeepSeek | DeepSeek | Fast code generation |
| AWS Bedrock | AWS | Offline/cost-sensitive ops |
