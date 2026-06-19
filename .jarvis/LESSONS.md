# JARVIS — LESSONS LEARNED
_Failures, surprises, and hard-won knowledge. Read this before touching existing systems._

## Backend / FastAPI

### L-001: slowapi rate limiting requires `request: Request` as FIRST parameter
- **What happened:** Decorator `@limiter.limit("10/minute")` was applied to routes where `request` wasn't the first positional parameter
- **Error:** `AttributeError: 'DemoGenerateRequest' object has no attribute 'state'`
- **Fix:** Always put `request: Request` first in route signatures when using @limiter.limit
- **Affected routes:** outreach `enroll_contacts`, discovery `run_discovery`

### L-002: SQLAlchemy `func.nullif(...).filter()` is NOT valid
- **What happened:** Attempted to use `.filter()` on a `func.nullif()` expression for N+1 fix
- **Error:** `AttributeError: 'Function' object has no attribute 'filter'`
- **Fix:** Use `case((condition, value), else_=None)` inside `func.sum()` for conditional aggregation
- **Pattern:** `func.sum(case((Invoice.status == "paid", Invoice.amount), else_=None))`

### L-003: WebSocket JWT must come via query param, not Authorization header
- **Why:** Browsers' WebSocket API does not support custom headers
- **Pattern:** `ws://host/ws/captain?token=<jwt>` then extract via `websocket.query_params.get("token")`

### L-004: Alembic migration chain must be unbroken
- **Why:** Each migration's `down_revision` must match previous migration's `revision`
- **Danger:** If two migrations both set `down_revision = "0027_..."`, Alembic detects a branch and refuses to apply
- **Rule:** Always check the last migration file before creating a new one

### L-005: `async def` route functions with `BackgroundTasks`
- **Pattern:** `bg.add_task(my_async_fn, arg1, arg2)` — FastAPI handles await internally
- **DO NOT:** `await my_async_fn(arg1)` inside the route (blocks response)

### L-006: SQLAlchemy `db.flush()` vs `db.commit()`
- **flush:** Sends SQL to DB within current transaction; object gets its ID; no commit yet
- **commit:** Routes that use `get_db()` dependency auto-commit on response
- **Pattern:** Always use `flush()` inside service functions; let the route/dependency commit

## AWS / Infrastructure

### L-007: ECS task must pull secrets from Secrets Manager at startup
- **Why:** Environment variables in ECS task definition reference SSM/Secrets Manager ARNs
- **Risk:** If Secrets Manager ARN is wrong, task fails to start with no useful error in ECS console
- **Debug:** Check CloudWatch logs for the specific task ARN

### L-008: ALB health check grace period
- **Why:** ECS won't drain a task if health checks pass during deploy
- **Setting:** `health_check_grace_period_seconds = 30` in Terraform ECS service
- **If missing:** New tasks get killed before app finishes starting

### L-009: Terraform state lock
- **Why:** DynamoDB table `jarvis-terraform-locks` prevents concurrent applies
- **If stuck:** Check DynamoDB for stale lock item; delete manually only if certain no apply is running

### L-010: pgvector extension must be enabled before creating vector columns
- **SQL:** `CREATE EXTENSION IF NOT EXISTS vector;` in first migration or RDS parameter group
- **Alembic:** Add `op.execute("CREATE EXTENSION IF NOT EXISTS vector;")` before any vector column

## AI Provider / Router

### L-011: Provider timeouts cascade differently than errors
- **Why:** Circuit breaker trips on errors; timeout doesn't trip until threshold
- **Setting:** Each provider has `timeout=30` in httpx client
- **Symptom:** Slow response (>30s) from degraded provider before failover kicks in

### L-012: `max_tokens` must be within model limits
- **Anthropic:** claude-haiku-4-5: 8192 max; claude-sonnet-4-6: 64000 max
- **Pattern:** Proposals = 2500 tokens; Contracts = 3000 tokens; Briefings = 1500 tokens
- **Never:** Set max_tokens > model limit (causes API error)

### L-013: Model identity in code comments is fine; in commits/PRs — never
- **Rule:** Never reference AI model names in commit messages, PR bodies, or code comments that go to the repo

## Frontend / React

### L-014: All API calls go through `frontend/src/services/api.js`
- **Why:** Centralized error handling, auth token injection, base URL config
- **Rule:** Never use raw fetch/axios in component files — always add a helper to api.js first

### L-015: Zustand store must be imported as named export
- **Pattern:** `import { useJarvisStore } from '../store/useJarvisStore'`
- **Not:** `import useJarvisStore from ...` (default export doesn't exist)

## Security

### L-016: NEVER commit .env, .tfvars, .htpasswd
- **gitignore covers:** `backend/.env`, `terraform.tfvars`, `infrastructure/nginx/.htpasswd`
- **If accidentally committed:** Rotate all secrets immediately, don't just delete the file

### L-017: Captain credentials are NOT stored in DB
- **Why:** Hardcoded in config.py from env vars `CAPTAIN_USERNAME` / `CAPTAIN_PASSWORD`
- **Production values:** Set in AWS Secrets Manager under `AWS_SSM_PREFIX`

## Operations

### L-018: docker compose up requires all services healthy before backend starts
- **Healthcheck dependency:** Backend `depends_on: {postgres: {condition: service_healthy}, redis: {condition: service_healthy}}`
- **If postgres slow:** Backend may fail to start on first `docker compose up -d`; retry once

### L-019: Alembic in Docker uses DATABASE_URL from environment
- **Command:** `docker compose exec backend alembic upgrade head`
- **Must be run** after every new migration file is created

### L-020: PR merge triggers ECS deploy automatically
- **Flow:** Push to main → GitHub Actions → ECR build → ECS blue/green → health gate check
- **Do not** manually deploy while Actions is running — it will conflict
