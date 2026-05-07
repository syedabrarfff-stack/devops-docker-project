# JARVIS — Aliyar Solutions AI Operating System
## Master Executive Directive (Permanent Configuration)

---

## Identity

**System:** JARVIS — Executive Operational Intelligence Infrastructure
**Company:** Aliyar Solutions
**Founder & CEO:** Syed Abrar ("Captain" in all internal references)
**Mission:** Global AI-powered technology operations company. Not a freelancer. A scalable, premium, autonomous AI agency.

---

## Codebase Overview

| Layer | Stack |
|---|---|
| Backend | FastAPI + SQLAlchemy 2.0 async + PostgreSQL |
| AI Layer | Multi-provider router: Claude, GPT-4o, Gemini, DeepSeek, Groq, Mistral, Moonshot, ZhipuAI, Qwen, MiniMax, NVIDIA |
| Scheduler | APScheduler 3.10 + SQLAlchemy job store (persistent) |
| Frontend | React 18 + Vite + Tailwind CSS glassmorphism |
| State | Zustand |
| Infrastructure | AWS ECS Fargate + Terraform (ap-south-2 primary, ap-south-1 backup) |
| CI/CD | GitHub Actions → ECR → ECS blue/green |
| Payments | PayPal (initial), Stripe/Wise (future) |

---

## Directory Structure

```
backend/
  app/
    api/v1/routes/          # All API route modules
    core/                   # config.py, database.py
    models/                 # SQLAlchemy models
    services/
      ai/                   # Multi-provider AI router + providers
      catalog/              # Service catalog (30 divisions)
      governance/           # Invoices, proposals, contracts
      intelligence/         # Tech radar, optimizer, research
      knowledge/            # SOPs, learnings, knowledge base
      monitoring/           # Emergency control, health checks
      scheduler/            # APScheduler engine

frontend/
  src/
    components/             # One folder per view (dashboard, chat, crm, ...)
    services/api.js         # All axios API helpers
    store/useJarvisStore.js # Zustand global state

infra/terraform/            # VPC, ECS, RDS, Redis, ALB, Secrets Manager, S3
infrastructure/             # docker-compose.prod.yml, nginx config
.github/workflows/          # deploy.yml — CI/CD pipeline
```

---

## Absolute Branding Rules

**INTERNAL (Captain-only):** JARVIS may reference its own AI architecture freely.

**EXTERNAL (client-facing output — proposals, emails, contracts, reports):**
- NEVER use: "AI agent", "bot", "GPT", "Claude", "autonomous", "machine-generated", "prompt"
- ALWAYS use: "Aliyar Solutions Team", "Our Engineering Team", "Our Operations Team", "Our Strategy Team"
- Clients must feel they are dealing with a premium international technology company

---

## Service Catalog (30 Divisions)

| Group | Services |
|---|---|
| Sales & Marketing | AI Lead Generation, AI Outreach, AI Sales Systems, CRM Automation |
| AI Automation | AI Appointment Booking, AI Voice Receptionist, Business Workflow Automation, Executive Automation |
| Cloud & DevOps | DevOps Infrastructure, AWS Architecture, Docker, CI/CD, Jenkins, Terraform, Ansible, Kubernetes, Monitoring & Logging, SaaS Deployment |
| Security | Cybersecurity Operations, Vulnerability Assessment |
| Content & Media | AI Content Automation, YouTube Automation, Social Media Management, Graphic Design, Video Editing |
| Digital Products | Website Development, Client Portal Systems, Operational Dashboards |
| Intelligence & Analytics | AI Research Operations, Business Intelligence Analytics |

---

## Active Scheduled Jobs (APScheduler)

| Job | Schedule | Purpose |
|---|---|---|
| daily_morning_briefing | 07:00 daily | Captain morning brief |
| daily_lead_score | 02:00 daily | Score all new leads |
| weekly_outreach_stats | Monday 08:00 | Outreach performance |
| weekly_pipeline_health | Sunday 20:00 | CRM pipeline check |
| weekly_tech_radar_scan | Monday 06:00 | AI technology classification |
| daily_optimization_review | 23:00 daily | System recommendations |
| biweekly_research_report | Sunday 07:00 | Market research generation |

---

## AI Task Routing

| Task Type | Primary | Fallback 1 | Fallback 2 |
|---|---|---|---|
| CODE | claude-sonnet | deepseek | gpt-4o |
| REASONING | claude-opus | gpt-4o | gemini-pro |
| STRATEGY | claude-opus | gpt-4o | claude-sonnet |
| ANALYSIS | claude-opus | gpt-4o | gemini-pro |
| RESEARCH | gemini-pro | gpt-4o | claude-sonnet |
| FAST | deepseek-flash | llama-3-3 | gpt-4o-mini |
| LONG_CONTEXT | gemini-pro | kimi-k2 | claude-sonnet |

---

## Governance Rules

- All invoices: auto-numbered `ALY-YYYYMM-XXXX`
- All proposals: AI-generated, Captain approval before sending
- All contracts: AI-generated, Captain approval before signing
- High-risk agent permissions: require Captain review
- Emergency incidents: auto-notify Captain via Slack + Telegram + WebSocket

---

## Development Conventions

- **Branch:** `claude/jarvis-cans-api-integration-ZThTD`
- **No `debug=True` in production**
- **All new routes:** add to `backend/app/api/v1/__init__.py`
- **All new views:** add to `frontend/src/App.jsx` VIEWS map + Sidebar.jsx NAV
- **All new API calls:** add helpers to `frontend/src/services/api.js`
- **All new models:** import in `backend/app/core/database.py` Base imports
- **Commit format:** `feat(phase-N): short description`
- **Never commit secrets** — all keys go in `.env` (gitignored)

---

## Infrastructure Notes

- Captain's laptop is for development, testing, approvals, and monitoring ONLY
- Production runs 24/7 on AWS ECS Fargate — independent of laptop uptime
- Primary: `ap-south-2` (Hyderabad) | Backup: `ap-south-1` (Mumbai)
- `docker compose -f infrastructure/docker-compose.prod.yml up -d` for local production testing
- `terraform plan/apply` in `infra/terraform/` for AWS infrastructure changes

---

*This file is the master reference for all JARVIS development sessions.*
*All changes must align with the Aliyar Solutions Master Executive Directive.*
