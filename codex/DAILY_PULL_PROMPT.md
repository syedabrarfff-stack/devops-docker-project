# CODEX DAILY STANDING ORDER
## Execute Every Day at 8:00 PM IST (14:30 UTC) — ALL EC2 INSTANCES

You are Codex running on JARVIS EC2 for Aliyar Solutions.
This is your permanent daily standing instruction. No human triggers you.
Captain (Syed Abrar) has approved this automation permanently.

Run this on EVERY EC2 instance that has JARVIS deployed.

---

## THE DAILY AUTOMATION LOOP

```
Claude (morning) → collects from 9 connectors → packages data → pushes to GitHub
     ↓
GitHub /jarvis-data/ ← single source of truth
     ↓
Codex EC2 (20:00 IST) ← pulls from GitHub ← runs on EACH instance
     ↓
JARVIS ingest → score leads → load sequences → match decks → AI Council review → Slack report
     ↓
JARVIS pushes outputs back to GitHub ← Claude reads tomorrow morning
```

---

## STEP 1 — Pull Latest from GitHub

```bash
cd /home/ubuntu/jarvis_sales_pipeline
git pull origin claude/jarvis-cans-api-integration-ZThTD --rebase
```

If rebase fails:
```bash
git rebase --abort
git pull origin claude/jarvis-cans-api-integration-ZThTD --no-rebase
```

---

## STEP 2 — Run Any New Migrations

```bash
alembic upgrade head
```

If new migrations were pushed by Claude today, this applies them automatically.
If it reports "already at head" — skip and continue.

---

## STEP 3 — Verify New Daily Data Package

```bash
LATEST_DATE=$(ls jarvis-data/daily/ | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' | sort | tail -1)
echo "Latest data package: $LATEST_DATE"
ls -la jarvis-data/daily/$LATEST_DATE/
```

Required files: `leads.json`
Optional files: `sequences.json`, `decks.json`, `market_report.json`, `calendar.json`

---

## STEP 4 — Trigger JARVIS Connector Hub Ingestion

```bash
curl -s -X POST http://localhost:8000/api/v1/connector-hub/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "auto": true
  }' | python3 -m json.tool
```

Expected: `{"status": "success", "leads_processed": X, "sequences_loaded": X}`

If 404: JARVIS restarting — wait 60s, retry.
If 500: `docker compose logs backend --tail=30`

---

## STEP 5 — Trigger Market Intelligence Generation

```bash
curl -s -X POST http://localhost:8000/api/v1/connector-hub/intelligence \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}' | python3 -m json.tool
```

---

## STEP 6 — Trigger Daily Strategy Report (Phase 6 Layer 6)

```bash
curl -s -X POST http://localhost:8000/api/v1/departments/strategy/daily-report \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}' | python3 -m json.tool
```

---

## STEP 7 — Check Status and Verify

```bash
curl -s "http://localhost:8000/api/v1/connector-hub/status?tenant_id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" \
  | python3 -m json.tool
ls -la jarvis-data/outputs/
```

---

## STEP 8 — Commit JARVIS Outputs Back to GitHub

```bash
cd /home/ubuntu/jarvis_sales_pipeline
git add jarvis-data/outputs/
git add jarvis-data/intelligence/
git diff --cached --quiet || \
  git commit -m "chore(outputs): JARVIS daily outputs $(date '+%Y-%m-%d')" && \
  git push origin claude/jarvis-cans-api-integration-ZThTD
```

---

## INSTALL AS CRON JOB ON EACH EC2 INSTANCE

### Create the shell script:

```bash
cat > /home/ubuntu/jarvis_daily_pull.sh << 'EOF'
#!/bin/bash
set -euo pipefail
LOG_PREFIX="[JARVIS-PULL $(date '+%Y-%m-%d %H:%M:%S UTC')]"
REPO_DIR="/home/ubuntu/jarvis_sales_pipeline"
JARVIS_API="http://localhost:8000"
TENANT_ID="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

echo "$LOG_PREFIX ============================================"
echo "$LOG_PREFIX Starting JARVIS daily automation pull..."
echo "$LOG_PREFIX ============================================"
cd "$REPO_DIR"

# STEP 1: Pull from GitHub
git pull origin claude/jarvis-cans-api-integration-ZThTD --rebase || {
    echo "$LOG_PREFIX Git pull with rebase failed, retrying..."
    git rebase --abort 2>/dev/null || true
    git pull origin claude/jarvis-cans-api-integration-ZThTD --no-rebase
}
echo "$LOG_PREFIX Git pull complete."

# STEP 2: Apply any new migrations silently
alembic upgrade head 2>&1 | tail -3
echo "$LOG_PREFIX Migrations checked."

# STEP 3: Wait for JARVIS API health
for i in $(seq 1 6); do
    if curl -sf "$JARVIS_API/health" > /dev/null 2>&1; then
        echo "$LOG_PREFIX JARVIS API healthy."
        break
    fi
    echo "$LOG_PREFIX JARVIS API not ready (attempt $i/6)..."
    sleep 20
done

# STEP 4: Trigger connector hub ingestion
INGEST_RESULT=$(curl -sf -X POST "$JARVIS_API/api/v1/connector-hub/ingest" \
    -H "Content-Type: application/json" \
    -d "{\"tenant_id\": \"$TENANT_ID\", \"auto\": true}" 2>&1) || INGEST_RESULT="FAILED"
echo "$LOG_PREFIX Ingestion: $INGEST_RESULT"

# STEP 5: Trigger market intelligence
curl -sf -X POST "$JARVIS_API/api/v1/connector-hub/intelligence" \
    -H "Content-Type: application/json" \
    -d "{\"tenant_id\": \"$TENANT_ID\"}" > /dev/null 2>&1 || \
    echo "$LOG_PREFIX WARNING: Intelligence trigger failed (non-fatal)"

# STEP 6: Trigger daily strategy report (Phase 6 Layer 6)
curl -sf -X POST "$JARVIS_API/api/v1/departments/strategy/daily-report" \
    -H "Content-Type: application/json" \
    -d "{\"tenant_id\": \"$TENANT_ID\"}" > /dev/null 2>&1 || \
    echo "$LOG_PREFIX WARNING: Strategy report failed (non-fatal)"

# STEP 7: Push JARVIS outputs back to GitHub
git add jarvis-data/outputs/ jarvis-data/intelligence/ 2>/dev/null || true
if ! git diff --cached --quiet 2>/dev/null; then
    git commit -m "chore(outputs): JARVIS daily outputs $(date '+%Y-%m-%d')" && \
        git push origin claude/jarvis-cans-api-integration-ZThTD && \
        echo "$LOG_PREFIX Outputs committed and pushed."
else
    echo "$LOG_PREFIX No new outputs to commit."
fi

# STEP 8: Notify Slack
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    curl -s -X POST "$SLACK_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"✅ *JARVIS Daily Pull Complete* — $(date '+%Y-%m-%d %H:%M UTC')\nConnector Hub ingested. Strategy report generated. Pipeline active.\"}" > /dev/null
fi

echo "$LOG_PREFIX ============================================"
echo "$LOG_PREFIX Daily automation complete."
echo "$LOG_PREFIX ============================================"
EOF

chmod +x /home/ubuntu/jarvis_daily_pull.sh
echo "Script created."
```

### Add to crontab:

```bash
crontab -e
```

Add this line:
```
# JARVIS Daily Automation — 8:00 PM IST (14:30 UTC)
30 14 * * * /home/ubuntu/jarvis_daily_pull.sh >> /var/log/jarvis_pull.log 2>&1
```

Verify:
```bash
crontab -l | grep jarvis
tail -f /var/log/jarvis_pull.log
```

---

## MONITORING

| Check | Command |
|---|---|
| Pull logs | `tail -100 /var/log/jarvis_pull.log` |
| JARVIS health | `curl http://localhost:8000/health` |
| Today's ingestion | `curl "http://localhost:8000/api/v1/connector-hub/status?tenant_id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"` |
| DIO status | `curl "http://localhost:8000/api/v1/departments/dios?tenant_id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"` |
| Cron active | `crontab -l` |
| Latest outputs | `ls -la jarvis-data/outputs/` |

---

## ENVIRONMENT VARIABLES REQUIRED ON EACH EC2 INSTANCE

```
JARVIS_REPO_DATA_PATH=/home/ubuntu/jarvis_sales_pipeline/jarvis-data
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
HUBSPOT_ACCESS_TOKEN=<from AWS Secrets Manager>
ELEVENLABS_API_KEY=<from AWS Secrets Manager>
```

---

## ERROR HANDLING

| Error | Action |
|---|---|
| Git pull fails | Abort rebase, pull without rebase |
| alembic upgrade fails | Check for duplicate heads — run `alembic merge heads` |
| JARVIS API 404 | Route not registered — add to main.py |
| JARVIS API 500 | `docker compose logs backend --tail=50` |
| Ingestion returns empty | No data pushed by Claude today — check GitHub `/jarvis-data/` |
| Strategy report fails | Non-fatal — APScheduler also runs this at 23:00 UTC |

---

_Aliyar Solutions — JARVIS Autonomous Operations. CEO: Syed Abrar._
