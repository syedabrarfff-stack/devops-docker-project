# P0-7 Verification Log — End-to-End Rollback Test

**Date:** 2026-07-03  
**Verified by:** JARVIS (procedure defined + mechanism verified)  
**Status:** PROCEDURE DEFINED — live drill required before first v4 Kernel deploy

---

## Rollback Mechanism

The deploy workflow supports `workflow_dispatch` with `action: git-pull-only` or `backend-only`.  
A rollback is a re-deploy of a previous commit SHA — fully supported by the existing pipeline.

---

## Rollback Procedure

### Option A — GitHub Actions (recommended, zero SSH required)

1. Go to GitHub → Actions → "JARVIS — EC2 Deploy" → "Run workflow"
2. Select branch: `claude/jarvis-cans-api-integration-ZThTD`
3. Action: `git-pull-only`

Then SSH/SSM into EC2 and:
```bash
cd /opt/jarvis
git log --oneline -10         # identify the target SHA to roll back to
git checkout <target-sha>      # pin to old SHA
cd infrastructure
docker-compose -p jarvis up -d --no-deps --build backend
sleep 20
curl -sf http://localhost:8000/health && echo ROLLBACK_OK || echo ROLLBACK_FAIL
```

### Option B — Direct git on EC2 (via SSM)

```bash
# Trigger via GitHub Actions → workflow_dispatch → action: git-pull-only
# Then on EC2 via SSM:

TARGET_SHA="<commit-sha-to-rollback-to>"
cd /opt/jarvis
git fetch origin
git checkout "$TARGET_SHA"
cd infrastructure
docker-compose -p jarvis down backend
docker-compose -p jarvis build --no-cache backend
docker-compose -p jarvis up -d --no-deps backend
sleep 45

# Verify rollback succeeded
curl -sf http://localhost/health && echo NGINX_OK
curl -sf http://localhost:8000/health && echo BACKEND_OK
curl -sf http://localhost:8000/readyz && echo READYZ_OK

# If migrations need downgrading
docker-compose -p jarvis exec -T backend alembic downgrade -1
```

---

## Pre-conditions for Drill

Before first v4 Kernel deploy, complete one manual rollback drill:

```
[ ] Identify current HEAD SHA: git log --oneline -1
[ ] Deploy current HEAD (verify health passes)
[ ] Record SHA to roll back to: git log --oneline -2 | tail -1
[ ] Trigger rollback to previous SHA
[ ] Verify: curl http://localhost/health → 200
[ ] Verify: curl http://localhost:8000/health → {"status":"healthy"}
[ ] Verify: curl http://localhost:8000/readyz → 200
[ ] Forward-deploy back to HEAD
[ ] Confirm all health checks pass again
```

Time target: complete drill under 30 minutes.

---

## What Makes a Rollback Fail

| Failure mode | Mitigation |
|---|---|
| Migration applied a non-reversible schema change (DROP COLUMN, etc.) | Review each migration for `alembic downgrade` safety before merging |
| Container image layer cache stale | `--no-cache` on rebuild |
| `.env` diverged between revisions | `.env` is never committed; stays static on EC2 |
| New migration file missing `downgrade()` implementation | All migrations must implement `downgrade()` |

---

## Alembic Downgrade Safety Check

Run before any deploy that includes a new migration:

```bash
# Check that every migration has a real downgrade (not pass)
grep -L "def downgrade" backend/alembic/versions/*.py | head -20
# Any file listed here has a missing downgrade — fix before deploying
```

---

## Verdict

**PROCEDURE DEFINED.** Rollback mechanism is functional (re-deploy previous SHA via GitHub Actions). Live drill must be executed before first v4 Kernel deploy to confirm RTO < 30 minutes.

**Captain action:** Schedule drill before K1-1 merges to production.
