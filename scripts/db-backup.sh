#!/bin/bash
# JARVIS nightly database backup — pg_dump → gzip → S3
# Install: cp scripts/db-backup.sh /usr/local/bin/jarvis-db-backup && chmod +x /usr/local/bin/jarvis-db-backup
# Cron:    0 2 * * * /usr/local/bin/jarvis-db-backup >> /var/log/jarvis-backup.log 2>&1
# RTO: 30min / RPO: 24h  (see docs/runbooks/BACKUP_RESTORE.md for full restore procedure)

set -e

DEPLOY_DIR="${JARVIS_DEPLOY_DIR:-/opt/jarvis}"
ENV_FILE="$DEPLOY_DIR/.env"
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
BACKUP_DIR=/tmp/jarvis-backups
S3_BUCKET="${BACKUP_S3_BUCKET:-jarvis-backups-aliyar}"
REGION="${AWS_DEFAULT_REGION:-ap-south-2}"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

# ── Load DB credentials ───────────────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
  log "ERROR: .env not found at $ENV_FILE — aborting"
  exit 1
fi

DB_NAME=$(grep -E '^POSTGRES_DB=' "$ENV_FILE" | cut -d= -f2 || echo "jarvis_db")
DB_USER=$(grep -E '^POSTGRES_USER=' "$ENV_FILE" | cut -d= -f2 || echo "jarvis_user")
DB_PASS=$(grep -E '^POSTGRES_PASSWORD=' "$ENV_FILE" | cut -d= -f2)

if [ -z "$DB_PASS" ]; then
  log "ERROR: POSTGRES_PASSWORD not found in $ENV_FILE — aborting"
  exit 1
fi

mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/jarvis_${TIMESTAMP}.sql.gz"

log "Starting backup: $BACKUP_FILE (db=$DB_NAME user=$DB_USER)"

# ── Dump via running postgres container ───────────────────────────────────────
if ! docker inspect jarvis_postgres &>/dev/null; then
  log "ERROR: jarvis_postgres container not running — aborting"
  exit 1
fi

PGPASSWORD="$DB_PASS" docker exec jarvis_postgres \
  pg_dump -U "$DB_USER" -d "$DB_NAME" -Fp --no-password \
  | gzip > "$BACKUP_FILE"

BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
log "Dump complete: $BACKUP_SIZE"

if [ ! -s "$BACKUP_FILE" ]; then
  log "ERROR: backup file is empty — aborting S3 upload"
  rm -f "$BACKUP_FILE"
  exit 1
fi

# ── Upload to S3 ──────────────────────────────────────────────────────────────
if ! command -v aws &>/dev/null; then
  log "ERROR: aws CLI not found — cannot upload to S3"
  exit 1
fi

S3_PATH="s3://${S3_BUCKET}/daily/$(basename "$BACKUP_FILE")"
aws s3 cp "$BACKUP_FILE" "$S3_PATH" \
  --region "$REGION" \
  --storage-class STANDARD_IA

# ── Verify upload ─────────────────────────────────────────────────────────────
aws s3 ls "$S3_PATH" --region "$REGION" \
  && log "BACKUP_VERIFIED: $S3_PATH ($BACKUP_SIZE)" \
  || { log "ERROR: S3 upload verification failed"; exit 1; }

# ── Cleanup local file ────────────────────────────────────────────────────────
rm -f "$BACKUP_FILE"
log "Backup complete — local file removed, S3 is source of truth."
