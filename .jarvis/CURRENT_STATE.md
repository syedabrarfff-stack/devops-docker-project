# JARVIS — CURRENT STATE
_Last updated: 2026-06-19 | Update this file at the start and end of every session._

## Company
- **Name:** Aliyar Solutions
- **CEO:** Syed Abrar (Captain)
- **Stage:** Pre-revenue / Infrastructure complete / Acquisition phase
- **Revenue Target:** $10,000–$30,000/month (Phase 2)

## System Status
- **Primary Branch:** `claude/jarvis-cans-api-integration-ZThTD`
- **Repository:** `syedabrarfff-stack/devops-docker-project`
- **PR:** #1 (open, draft) — accumulating all feature commits

## Tech Stack
- **Backend:** FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16 (pgvector)
- **Frontend:** React 18 + Vite + Tailwind CSS (glassmorphism)
- **AI Router:** 11 providers — NVIDIA NIM (primary), Anthropic, OpenAI, Google, DeepSeek, Groq, Mistral, ZhipuAI, Qwen, Moonshot, MiniMax
- **Queue/Cache:** Redis 7
- **Migrations:** 29 complete (latest: 0029_trust_engine)
- **Routes:** 57 modules, ~411 endpoints
- **Models:** 35 SQLAlchemy model files
- **Services:** 36 service directories, ~202 Python files

## What Is Running
- [ ] Docker local stack (run: `cd infrastructure && docker compose up -d`)
- [ ] AWS ECS (PENDING — Captain must apply Terraform + merge PR)
- [ ] Alembic migrations on production DB (pending deploy)

## VS Code HQ Status — COMPLETE
- [x] 11 `.jarvis/` memory files (permanent model-independent knowledge)
- [x] `jarvis.code-workspace` (7 named sidebar groups)
- [x] `.vscode/tasks.json` (16 one-click operations)
- [x] `.vscode/extensions.json` (15 recommended extensions)
- [x] `.continue/config.json` (4-model council + slash commands)

## What Was Built (Cumulative)

### Security Layer (commits 1–9)
- Rate limiting on all high-risk endpoints (slowapi + Redis)
- JWT auth on all Captain-only routes + WebSocket
- N+1 query eliminated in revenue clients endpoint
- Unbounded SELECT caps on 4 tables
- Input validation (Pydantic Field max_length on 80+ inputs)
- 15 composite DB performance indexes (migration 0027)
- Async I/O for boto3 SSM and filesystem ops
- NGINX: HSTS + Content-Security-Policy

### Revenue Automation Layer
- Invoices: auto-email to client on creation via SES
- Proposals: auto-email full content to client
- Demos: auto-email PDF URL if prospect_email provided
- Clients: auto welcome/onboarding email on creation
- Contracts: auto-generate on proposal "accepted" + auto-email
- Full contract system: model + migration 0028 + AI generator + routes

### Trust Engine (migration 0029)
- Executive Opportunity Briefs: AI-generated per lead
- Engagement scoring: event weights → trust_score (0-100)
- Conversion probability: 0-100, threshold 40 → ready_for_proposal
- Referral engine: testimonial + referral + case_study concurrent generation
- Routes: POST /trust/briefs/generate, POST /trust/engagement, GET /trust/score/{lead_id}, POST /trust/referrals/generate

### VS Code HQ (commit fd8b96b)
- Model-independent memory system (.jarvis/ directory)
- jarvis.code-workspace with 7 named sidebar groups
- .vscode/tasks.json — 16 operational shortcuts
- .continue/config.json — 4-model council with JARVIS system prompts

## Blockers Requiring Captain Action

| Action | Impact | Priority |
|--------|--------|---------|
| Attach AdministratorAccess to JarvisGitHubActionsRole in IAM | CI/CD cannot push to ECR | CRITICAL |
| `terraform apply` (51 AWS resources pending) | No production infrastructure | CRITICAL |
| DNS: CNAME aliyarsolutions.com → ALB DNS | Production URL won't resolve | CRITICAL |
| Merge PR #1 → triggers ECS blue/green deploy | Backend not live | CRITICAL |
| Set STRIPE_WEBHOOK_SECRET in AWS Secrets Manager | Payments won't confirm | HIGH |
| SES sandbox → production access | Emails stuck in sandbox | HIGH |
| Register Telegram webhook URL (post-deploy) | Captain won't receive alerts | HIGH |

## Key File Locations

| What | Where |
|------|-------|
| API routes | backend/app/api/v1/routes/ |
| Route registration | backend/app/api/v1/__init__.py |
| AI router + routing table | backend/app/services/ai/router.py |
| AI providers | backend/app/services/ai/providers/ |
| Models | backend/app/models/ |
| Model registration | backend/app/models/__init__.py |
| Migrations | backend/alembic/versions/ |
| Governance docs gen | backend/app/services/governance/document_gen.py |
| Trust Engine services | backend/app/services/trust/ |
| Team member routing | backend/app/services/team/team_service.py |
| Frontend components | frontend/src/components/ |
| Frontend state | frontend/src/store/useJarvisStore.js |
| Frontend API helpers | frontend/src/services/api.js |
| Docker compose | infrastructure/docker-compose.yml |
| Terraform | infra/terraform/ |
| CI/CD | .github/workflows/deploy.yml |
| Monitoring | monitoring/ |
| Grafana dashboards | infrastructure/grafana/ |
| Operational scripts | scripts/ |
| Memory system | .jarvis/ |
| VS Code config | .vscode/ |
| Continue council | .continue/config.json |

## Local Development Quick Start
```bash
cd infrastructure
docker compose up -d              # Start all services
docker compose logs -f backend    # Watch backend logs
docker compose exec backend alembic upgrade head   # Run migrations
curl http://localhost:8000/health  # Verify running
curl http://localhost:8000/readyz  # Verify DB + Redis
```

## AWS Reference
- Account: 824232273953
- Primary region: ap-south-2 (Hyderabad)
- DR region: ap-south-1 (Mumbai) — planned
- Terraform state: s3://jarvis-terraform-state-824232273953/production/terraform.tfstate
- State lock: DynamoDB table jarvis-terraform-locks
- GitHub Actions role: JarvisGitHubActionsRole (OIDC)
- Default tenant: 794d9b02-2dd6-49f0-b5c1-9f7c0b3af4b1
