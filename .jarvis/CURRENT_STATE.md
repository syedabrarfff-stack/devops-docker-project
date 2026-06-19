# JARVIS — CURRENT STATE
_Last updated: 2026-06-19 | Update this file at the start and end of every session._

## Company
- **Name:** Aliyar Solutions
- **CEO:** Syed Abrar (Captain)
- **Stage:** Pre-revenue / Building to first 10 clients
- **Revenue Target:** $10,000–$30,000/month (Phase 2)

## System Status
- **Primary Branch:** `claude/jarvis-cans-api-integration-ZThTD`
- **Repository:** `syedabrarfff-stack/devops-docker-project`
- **Backend:** FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16
- **Frontend:** React 18 + Vite + Tailwind CSS (glassmorphism)
- **Migrations:** 0029 migrations applied (latest: 0029_trust_engine)
- **Docker:** Redis 7 + PostgreSQL 16 (pgvector) + Backend + Frontend + Nginx + Prometheus + Grafana
- **AWS:** ECS Fargate — ap-south-2 (primary) | ap-south-1 (DR)
- **AWS Account:** 824232273953
- **Terraform State:** S3 bucket `jarvis-terraform-state-824232273953`
- **Default Tenant:** `794d9b02-2dd6-49f0-b5c1-9f7c0b3af4b1`

## What Is Running
- [ ] Docker local stack (run `docker compose up -d` to start)
- [ ] AWS ECS (pending: Captain must apply Terraform + push to trigger deploy)
- [ ] Alembic migrations applied to production DB

## What Was Just Built (this session)
1. Rate limiting on all high-risk endpoints (slowapi + Redis)
2. JWT auth on all Captain-only routes + WebSocket
3. N+1 query eliminated in revenue clients endpoint
4. Auto-delivery: invoices, proposals, demos, client welcome email
5. Full contract system: model + migration + AI generator + routes + auto-trigger
6. Trust Engine: Executive Opportunity Briefs, engagement scoring, referral engine
7. Proposal enhanced with Cost of Inaction + outcomes framing
8. VS Code HQ: workspace file, memory system, multi-model council

## Blockers Requiring Captain Action
- [ ] IAM: Attach AdministratorAccess to `JarvisGitHubActionsRole`
- [ ] Terraform apply (51 AWS resources pending)
- [ ] DNS: Point `aliyarsolutions.com` CNAME → ALB DNS
- [ ] Set `STRIPE_WEBHOOK_SECRET` in .env
- [ ] Merge PR → triggers ECS deploy
- [ ] Post-deploy: Register Telegram webhook URL
