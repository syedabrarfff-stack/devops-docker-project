# CODEX DAILY STANDING ORDER
## Execute Every Day at 8:00 PM IST (14:30 UTC)

You are Codex running on the JARVIS EC2 instance for Aliyar Solutions.
This is your permanent daily standing instruction.
No human needs to trigger you. You run this every day automatically.
Captain (Syed Abrar) has approved this automation permanently.

---

## STEP 1 — Pull Latest from GitHub

```bash
cd /home/ubuntu/jarvis_sales_pipeline
git pull origin claude/jarvis-cans-api-integration-ZThTD --rebase
```

Expected output: Either "Already up to date." or a list of updated files.
If rebase fails, run:
```bash
git rebase --abort
git pull origin claude/jarvis-cans-api-integration-ZThTD --no-rebase
```

---

## STEP 2 — Verify New Daily Data

```bash
ls -la jarvis-data/daily/
# Find the most recent date folder
LATEST_DATE=$(ls jarvis-data/daily/ | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' | sort | tail -1)
echo "Latest data package: $LATEST_DATE"
ls -la jarvis-data/daily/$LATEST_DATE/ 2>/dev/null || echo "No data for $LATEST_DATE"
```

Verify these files exist:
- `leads.json` — required
- `sequences.json` — optional
- `decks.json` — optional
- `market_report.json` — optional

If `leads.json` is missing, log the gap but continue. JARVIS handles missing files gracefully.

---

## STEP 3 — Trigger JARVIS Connector Hub Ingestion

```bash
curl -s -X POST http://localhost:8000/api/v1/connector-hub/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "auto": true
  }' | python3 -m json.tool
```

Expected response:
```json
{
  "status": "success",
  "ingestion_id": "...",
  "leads_processed": X,
  "sequences_loaded": X,
  "date": "YYYY-MM-DD"
}
```

If 404: JARVIS may be restarting. Wait 60 seconds and retry once.
If 500: Check `/tmp/jarvis.log` for errors and report to Captain via Slack.

---

## STEP 4 — Trigger Market Intelligence Generation

```bash
curl -s -X POST http://localhost:8000/api/v1/connector-hub/intelligence \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
  }' | python3 -m json.tool
```

This generates fresh market reports and pushes them to `/jarvis-data/intelligence/`.

---

## STEP 5 — Verify Status and Report

```bash
# Check today's ingestion status
curl -s http://localhost:8000/api/v1/connector-hub/status?tenant_id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa \
  | python3 -m json.tool

# Check JARVIS outputs written
ls -la jarvis-data/outputs/
```

If Slack webhook is configured, post result:
```bash
if [ -n "$SLACK_WEBHOOK_URL" ]; then
  curl -s -X POST "$SLACK_WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"JARVIS daily pull complete — $(date '+%Y-%m-%d %H:%M UTC'). Data ingested and pipeline active.\"}"
fi
```

---

## STEP 6 — Commit JARVIS Outputs Back to GitHub

```bash
cd /home/ubuntu/jarvis_sales_pipeline
git add jarvis-data/outputs/
git add jarvis-data/intelligence/
git diff --cached --quiet || git commit -m "chore(outputs): JARVIS daily outputs $(date '+%Y-%m-%d')" && \
  git push origin claude/jarvis-cans-api-integration-ZThTD
```

This allows Claude to read what JARVIS processed on the next morning collection run.

---

## SCHEDULE AS CRON JOB

Add to crontab on EC2 (`crontab -e`):
```
# JARVIS Daily Connector Hub Pull — 8:00 PM IST (14:30 UTC)
30 14 * * * /home/ubuntu/jarvis_daily_pull.sh >> /var/log/jarvis_pull.log 2>&1
```

---

## /home/ubuntu/jarvis_daily_pull.sh

Save this as the executable shell script on EC2:

```bash
#!/bin/bash
# JARVIS Daily Pull Script
# Company: Aliyar Solutions | CEO: Syed Abrar
# Runs at 14:30 UTC (20:00 IST) daily

set -euo pipefail
LOG_PREFIX="[JARVIS-PULL $(date '+%Y-%m-%d %H:%M:%S UTC')]"
REPO_DIR="/home/ubuntu/jarvis_sales_pipeline"
JARVIS_API="http://localhost:8000"
TENANT_ID="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

echo "$LOG_PREFIX Starting daily pull..."

# Step 1: Pull from GitHub
cd "$REPO_DIR"
git pull origin claude/jarvis-cans-api-integration-ZThTD --rebase || {
    echo "$LOG_PREFIX Git pull failed, attempting reset..."
    git rebase --abort 2>/dev/null || true
    git pull origin claude/jarvis-cans-api-integration-ZThTD --no-rebase
}
echo "$LOG_PREFIX Git pull complete."

# Step 2: Wait for JARVIS API to be ready
for i in $(seq 1 5); do
    if curl -sf "$JARVIS_API/health" > /dev/null 2>&1; then
        echo "$LOG_PREFIX JARVIS API healthy."
        break
    fi
    echo "$LOG_PREFIX JARVIS API not ready (attempt $i/5)..."
    sleep 30
done

# Step 3: Trigger ingestion
INGEST_RESULT=$(curl -sf -X POST "$JARVIS_API/api/v1/connector-hub/ingest" \
    -H "Content-Type: application/json" \
    -d "{\"tenant_id\": \"$TENANT_ID\", \"auto\": true}" 2>&1) || {
    echo "$LOG_PREFIX ERROR: Ingestion trigger failed: $INGEST_RESULT"
    exit 1
}
echo "$LOG_PREFIX Ingestion triggered: $INGEST_RESULT"

# Step 4: Trigger market intelligence
curl -sf -X POST "$JARVIS_API/api/v1/connector-hub/intelligence" \
    -H "Content-Type: application/json" \
    -d "{\"tenant_id\": \"$TENANT_ID\"}" > /dev/null 2>&1 || \
    echo "$LOG_PREFIX WARNING: Intelligence trigger failed (non-fatal)"

# Step 5: Commit outputs
git add jarvis-data/outputs/ jarvis-data/intelligence/ 2>/dev/null || true
if ! git diff --cached --quiet 2>/dev/null; then
    git commit -m "chore(outputs): JARVIS daily outputs $(date '+%Y-%m-%d')" && \
        git push origin claude/jarvis-cans-api-integration-ZThTD
    echo "$LOG_PREFIX Outputs committed and pushed."
else
    echo "$LOG_PREFIX No new outputs to commit."
fi

echo "$LOG_PREFIX Daily pull complete."
```

Make it executable: `chmod +x /home/ubuntu/jarvis_daily_pull.sh`

---

## Error Handling

| Error | Action |
|---|---|
| Git pull fails | Abort rebase, pull without rebase |
| JARVIS API 404 | Wait 60s, retry once |
| JARVIS API 500 | Log error, skip ingestion, notify Slack |
| No leads.json today | Log warning, continue without leads |
| Commit fails | Log warning, continue (non-blocking) |

---

## Environment Variables Required on EC2

```
JARVIS_REPO_DATA_PATH=/home/ubuntu/jarvis_sales_pipeline/jarvis-data
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

---

## Monitoring

Check logs: `tail -f /var/log/jarvis_pull.log`
Check cron: `crontab -l`
Check JARVIS API: `curl http://localhost:8000/health`
Check last ingestion: `curl "http://localhost:8000/api/v1/connector-hub/status?tenant_id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"`

_Aliyar Solutions — JARVIS Operational Infrastructure_
