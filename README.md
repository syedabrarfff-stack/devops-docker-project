# JARVIS — Aliyar Solutions

**Intelligent Automation & AI-Powered Operations Platform**

JARVIS is the operational core of Aliyar Solutions — a technology company delivering enterprise-grade software infrastructure, AI systems, cloud architecture, and digital operations globally.

---

## Overview

JARVIS is a self-compounding technology platform built on:

- **AI Intelligence Core** — 13+ AI provider router with multi-model inference (Claude, DeepSeek, GPT-4, Gemini, Groq, etc.)
- **Autonomous Operations** — 64 scheduled jobs (38 core + 26 AIONX organ jobs) orchestrating sales, leads, outreach, intelligence
- **Cloud Infrastructure** — AWS ECS Fargate, PostgreSQL, Redis, multi-region deployment
- **Memory Architecture** — Episodic, semantic, and instruction layers with knowledge graphs
- **Sovereign AIONX Organs** — Autonomous decision intelligence, digital twins, trust engines, institutional wisdom

**Status:** MVP-ready infrastructure with 40+ database tables, 47 API routers (68 endpoints), complete monitoring stack, and zero-downtime deployment configured.

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 16, Redis 7 (via Docker)

### Setup (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/syedabrarfff-stack/devops-docker-project.git
cd devops-docker-project

# 2. Copy environment template
cp .env.example .env
# Edit .env with your API keys (see Configuration section below)

# 3. Start infrastructure
docker-compose up -d

# 4. Install backend dependencies
cd backend && pip install -r requirements.txt && cd ..

# 5. Install frontend dependencies
npm install

# 6. Run database migrations
cd backend && python -m alembic upgrade head && cd ..

# 7. Start backend (in terminal 1)
cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 8. Start frontend (in terminal 2)
npm run dev
```

**Access the application:**
- Frontend: http://localhost:5173
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Grafana: http://localhost:3000 (user: admin, pass: admin)
- Prometheus: http://localhost:9090

---

## Project Structure

```
.
├── backend/                          # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── api/v1/routes/           # 47 route modules (68+ endpoints)
│   │   ├── services/                # Business logic
│   │   │   ├── ai/                  # Multi-provider AI router
│   │   │   ├── scheduler/           # APScheduler 64 jobs
│   │   │   ├── aionx/               # Sovereign organs
│   │   │   ├── leads/               # Lead discovery & scoring
│   │   │   ├── outreach/            # Email & outreach automation
│   │   │   ├── intelligence/        # Briefings, market intel
│   │   │   └── notifications/       # Email, Telegram, SMS
│   │   ├── models/                  # 40+ SQLAlchemy models
│   │   ├── core/                    # Config, database, middleware
│   │   └── main.py                  # FastAPI app
│   └── requirements.txt
│
├── frontend/                         # React 18 + Vite
│   ├── src/
│   │   ├── components/              # 18+ view components
│   │   ├── services/api.js          # Axios API helpers
│   │   ├── store/                   # Zustand global state
│   │   └── App.jsx                  # Main router
│   ├── package.json
│   └── vite.config.js
│
├── infrastructure/                   # Docker & AWS
│   ├── docker-compose.yml           # 11 services (dev)
│   ├── nginx.conf                   # Reverse proxy config
│   └── kubernetes/                  # K8s manifests (optional)
│
├── infra/terraform/                 # AWS Fargate infrastructure
│   ├── main.tf                      # VPC, ECS, RDS, Redis
│   ├── secrets.tf                   # AWS Secrets Manager
│   ├── variables.tf                 # Configuration
│   └── outputs.tf
│
├── scripts/                          # Operational scripts
│   ├── integration_test.py          # End-to-end test
│   ├── test-ai-providers.py         # AI provider verification
│   └── health_check.sh              # Production health gate
│
├── .github/workflows/
│   └── deploy.yml                   # GitHub Actions → ECR → ECS
│
├── Headquarters/                     # Headquarters documentation
│   └── STATUS.md                    # Subsystem verification status
│
├── JARVIS_SELF_KNOWLEDGE.md         # System architecture (243 lines)
├── CLAUDE.md                        # Operational directive (21KB)
└── README.md                        # This file
```

---

## Configuration

### Critical Environment Variables

**MVP-Required (Outreach & Payments):**
```bash
# Email (AWS SES)
SES_FROM_EMAIL=your-verified-sender@example.com

# Payments (Stripe)
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
STRIPE_SECRET_KEY=sk_test_xxxxx
```

**High Priority (AWS Infrastructure):**
```bash
# AWS Bedrock (AI provider fallback)
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=ap-south-2

# AWS S3 (Document storage)
AWS_S3_BUCKET=jarvis-documents-prod
```

**Intelligence & Automation:**
```bash
# GitHub (Scout network integration)
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_OWNER=your-org

# AI Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-v1-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
```

**Notifications:**
```bash
TELEGRAM_BOT_TOKEN=123456:ABCdefGHIjklmnoPQRstuvWXYZ
TELEGRAM_CHAT_ID=123456789
```

### Full Configuration

See `.env.example` for all 50+ configurable environment variables. Key categories:

1. **API Keys** — AI providers, third-party services
2. **Database** — PostgreSQL connection, Redis
3. **AWS** — Credentials, regions, buckets
4. **Email** — SES sender, SMTP fallback
5. **Payments** — Stripe keys, webhooks
6. **Notifications** — Telegram, Slack, email
7. **Application** — App version, tenant ID, debug mode

---

## Architecture

### System Layers

**Layer 1: AI Intelligence Core**
- Multi-provider router (Claude, DeepSeek, GPT-4, Gemini, Groq, Mistral, Qwen, etc.)
- Task-based routing (FAST, GENERAL, ANALYSIS, CODE, REASONING, STRATEGY, SALES, RESEARCH)
- Circuit breaker protection, rate limiting, cost tracking
- Fallback chains: 6-7 model tiers per task type

**Layer 2: Autonomous Operations**
- APScheduler with 64 registered jobs
- 38 core engine jobs (lead scoring, outreach, briefing, intelligence)
- 26 AIONX organ jobs (sentinel, decision memory, digital twins, wisdom synthesis)
- Job failure tracking with Captain escalation (>3 failures)

**Layer 3: Data & Memory**
- PostgreSQL 16 with 40+ tables across 8 domains
- Redis 7 for caching, task queues, rate limiting
- 3-tier memory architecture: episodic (short-term), semantic (long-term), instruction (permanent)
- Knowledge graphs and entity relationships

**Layer 4: Business Logic**
- Lead discovery & scoring (Apollo, Google Maps, market APIs)
- Outreach automation (email sequences, reply classification, engagement scoring)
- Proposal generation (PDF, dynamic templates, approval workflows)
- Revenue operations (invoicing, payment tracking, financial health)

**Layer 5: Intelligence Engines**
- Tech radar (emerging technology tracking)
- Market intelligence (competitive analysis, trends)
- Client digital twins (churn prediction, upsell opportunity)
- Authority matrix & governance (decision escalation, approval chains)

**Layer 6: Integration Layer**
- Email (AWS SES)
- Payments (Stripe, PayPal)
- CRM (HubSpot, Pipedrive)
- Communication (Telegram, Slack, WhatsApp)
- Data sources (Apollo, Google, custom APIs)

**Layer 7: Deployment & Monitoring**
- Docker Compose (local), AWS ECS Fargate (production)
- Blue/green deployment with health gates
- Prometheus metrics, Grafana dashboards, Loki logs
- AlertManager with Telegram notifications

---

## Core Features

### AI Operations
- **Multi-Model Inference** — Simultaneous queries across 13+ models with 14-model Council synthesis
- **Dynamic Routing** — Task type → best model, with automatic fallback on failure
- **Cost Optimization** — Per-call cost tracking, provider failover on rate limits

### Lead Generation & Scoring
- **Discovery Engine** — Lead discovery from Apollo, Google Maps, market databases
- **ICP Scoring** — Ideal Customer Profile matching with machine learning
- **Lead Enrichment** — Automatic data enrichment from 5+ sources
- **Scoring Dashboard** — Real-time lead quality visualization

### Outreach Automation
- **Email Sequences** — Templated multi-step campaigns with personalization
- **Reply Classification** — AI classification of prospect responses (interested, maybe, not interested)
- **Engagement Scoring** — Predict deal progression based on engagement
- **Speed-to-Lead** — Automated immediate responses to hot leads

### Intelligence & Insights
- **Morning Briefing** — Daily snapshot of pipeline, leads, revenue, alerts
- **Tech Radar** — Weekly emerging technology tracking
- **Market Intelligence** — Competitor monitoring, industry trends
- **Financial Health** — Cash flow forecasting, revenue analytics, burn rate tracking

### Governance & Automation
- **Approval Workflows** — Proposal → Captain approval → send/archive
- **Autonomous Actions** — Governed AI autonomy (decides proposals, escalates decisions)
- **Decision Memory** — 30/90-day retrospectives on all AI decisions
- **Institutional Wisdom** — Weekly synthesis of lessons learned, patterns

### Integrations
- **Email** — AWS SES for high-volume outreach
- **Payments** — Stripe for invoicing and subscriptions
- **CRM** — HubSpot/Pipedrive sync, lead management
- **Communication** — Telegram for Captain alerts, Slack for team notifications
- **GitHub** — Scout network data push to jarvis-data/ repository

---

## Development

### Backend Development

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Start development server
python -m uvicorn app.main:app --reload

# Database migrations
python -m alembic upgrade head
python -m alembic downgrade -1
python -m alembic revision --autogenerate -m "description"
```

**Key files:**
- `app/main.py` — FastAPI app initialization
- `app/api/v1/__init__.py` — Route registration (47 routers)
- `app/core/config.py` — Configuration management
- `app/core/database.py` — SQLAlchemy setup
- `app/services/scheduler/scheduler.py` — APScheduler jobs (71 total: 45 production + 26 AIONX)

### Frontend Development

```bash
# Install dependencies
npm install

# Development server (with hot reload)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linter
npm run lint
```

**Key files:**
- `src/App.jsx` — Main router and view registry
- `src/components/` — View components (18+ modules)
- `src/services/api.js` — Axios API helpers
- `src/store/useJarvisStore.js` — Zustand global state
- `tailwind.config.js` — Tailwind CSS configuration

### Testing

```bash
# Backend tests
cd backend && pytest -v

# Integration test (requires running backend)
python scripts/integration_test.py

# AI provider verification
python scripts/test-ai-providers.py
```

---

## Deployment

### Local (Docker Compose)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop services
docker-compose down
```

**Services running:**
- PostgreSQL 16 (port 5432)
- Redis 7 (port 6379)
- Backend FastAPI (port 8000)
- Frontend React (port 5173)
- Nginx (port 80, 443)
- Prometheus (port 9090)
- Grafana (port 3000)
- AlertManager (port 9093)
- Loki (port 3100)

### Production (AWS ECS Fargate)

```bash
# 1. Configure AWS credentials
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=ap-south-2

# 2. Deploy infrastructure
cd infra/terraform
terraform init
terraform plan
terraform apply

# 3. Push Docker image to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <ECR_URL>
docker build -t jarvis:latest .
docker tag jarvis:latest <ECR_URL>/jarvis:latest
docker push <ECR_URL>/jarvis:latest

# 4. Deploy via GitHub Actions
git push  # Triggers deploy.yml workflow
```

**Infrastructure:**
- Primary region: ap-south-2 (Hyderabad)
- DR region: ap-south-1 (Mumbai)
- Blue/green deployment with zero downtime
- Auto-rollback on health check failure

---

## Monitoring & Observability

### Health Checks

```bash
# Liveness check (quick)
curl http://localhost:8000/health

# Deep readiness check
curl http://localhost:8000/readyz

# Metrics
curl http://localhost:8000/metrics
```

### Dashboards

| Dashboard | Purpose | URL |
|---|---|---|
| Grafana | System metrics, request latency | http://localhost:3000 |
| Prometheus | Metric queries | http://localhost:9090 |
| AlertManager | Active alerts | http://localhost:9093 |

### Logs

```bash
# View backend logs
docker-compose logs -f backend

# View scheduler logs (via Loki)
# Query in Grafana: {job="scheduler"}

# View API access logs (via Loki)
# Query in Grafana: {job="api"}
```

### Alerts

Critical alerts are sent to Telegram:
- Scheduler job failures (>3 consecutive)
- AI provider timeouts (>60s)
- Database connection errors
- High error rate (>10%)
- Payment webhook failures

---

## Documentation

- **JARVIS_SELF_KNOWLEDGE.md** — Complete system architecture (243 lines)
  - 35 database tables, schema overview
  - 64 scheduler jobs with descriptions
  - Authority matrix & approval workflows
  - Team registry with 8 personas
  - AI routing map for 8 task types

- **CLAUDE.md** — Operational directive (21KB)
  - Organizational structure (Captain → JARVIS → 7 divisions)
  - Communication standards (internal vs external)
  - 30-division service catalog
  - AI routing table with fallback chains
  - Governance & financial standards

- **Headquarters/STATUS.md** — Subsystem verification (941 lines)
  - Implementation status of 40+ components
  - Production blockers and solutions
  - Phase-by-phase checklist (8 phases)

- **backend/README.md** — Backend API reference
- **frontend/README.md** — Frontend development guide
- **infrastructure/README.md** — Docker & AWS setup

---

## Troubleshooting

### Common Issues

**Backend won't start:**
```bash
# Check database connection
docker-compose logs postgres

# Check port availability
lsof -i :8000

# Reset database
cd backend && python -m alembic downgrade base
docker-compose restart postgres && sleep 5
cd backend && python -m alembic upgrade head
```

**AI provider not working:**
```bash
# Test all providers
python scripts/test-ai-providers.py

# Check API keys
echo $ANTHROPIC_API_KEY  # Should not be empty
echo $OPENROUTER_API_KEY
```

**Scheduler jobs not running:**
```bash
# Check scheduler status
curl http://localhost:8000/api/v1/scheduler/jobs

# View job logs
docker-compose logs backend | grep "Scheduler:"

# Restart scheduler
docker-compose restart backend
```

**Frontend won't connect to API:**
```bash
# Check CORS
curl -H "Origin: http://localhost:5173" http://localhost:8000/api/v1/health

# Check frontend environment
cat .env | grep REACT_APP_API_URL

# Rebuild frontend
npm run build
```

---

## Support & Contributing

### Reporting Issues

1. Check existing GitHub issues
2. Run health checks: `curl http://localhost:8000/readyz`
3. Attach logs and error details
4. Create GitHub issue with reproduction steps

### Contributing

1. Create feature branch: `git checkout -b feat/my-feature`
2. Make changes and test thoroughly
3. Commit with clear message: `git commit -m "feat: description"`
4. Push to remote: `git push -u origin feat/my-feature`
5. Open pull request for review

---

## License & Attribution

**Aliyar Solutions** — Enterprise AI Operations Platform

© 2024 Aliyar Solutions. All rights reserved.

This codebase represents the complete operational infrastructure of JARVIS — the autonomous operational intelligence core of Aliyar Solutions.

---

## Getting Help

**For API/development questions:**
- API Docs: http://localhost:8000/docs (Swagger UI)
- Architecture: See JARVIS_SELF_KNOWLEDGE.md

**For operational questions:**
- Operational Directive: See CLAUDE.md
- Status & Verification: See Headquarters/STATUS.md

**For infrastructure questions:**
- Docker setup: See infrastructure/README.md
- AWS Terraform: See infra/terraform/

---

**Last Updated:** 2024-07-02  
**Version:** 1.0.0-MVP  
**Status:** MVP-Ready (5 environment variables + 4 README files needed for full launch)
