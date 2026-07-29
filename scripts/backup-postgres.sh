#!/bin/bash
# JARVIS Phase 1 PostgreSQL Backup Script
# Automated nightly backup to S3 with integrity verification
# Usage: ./backup-postgres.sh [target_bucket]

set -euo pipefail

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/jarvis"
DB_CONTAINER="jarvis_postgres"
DB_NAME="${POSTGRES_DB:-jarvis}"
DB_USER="${POSTGRES_USER:-jarvis}"
S3_BUCKET="${1:-jarvis-backups-prod}"
S3_REGION="${AWS_REGION:-ap-south-2}"
BACKUP_RETENTION_DAYS=30
LOG_FILE="/var/log/jarvis-backup.log"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "=== JARVIS PostgreSQL Backup Started ==="

# Step 1: Dump database
BACKUP_FILE="$BACKUP_DIR/jarvis_db_${TIMESTAMP}.sql.gz"
log "Creating backup: $BACKUP_FILE"

if docker exec "$DB_CONTAINER" pg_dump \
    -U "$DB_USER" \
    "$DB_NAME" \
    --format=plain \
    --compress=9 \
    --verbose 2>"${BACKUP_DIR}/dump_${TIMESTAMP}.log" > "$BACKUP_FILE"; then
    log "✓ Database dump successful"
else
    log "✗ Database dump failed"
    exit 1
fi

# Step 2: Calculate checksum
CHECKSUM=$(sha256sum "$BACKUP_FILE" | awk '{print $1}')
CHECKSUM_FILE="${BACKUP_FILE}.sha256"
echo "$CHECKSUM  $(basename $BACKUP_FILE)" > "$CHECKSUM_FILE"
log "✓ Checksum: $CHECKSUM"

# Step 3: Upload to S3
log "Uploading to S3: s3://$S3_BUCKET/$TIMESTAMP/"

if aws s3 cp "$BACKUP_FILE" "s3://$S3_BUCKET/$TIMESTAMP/$(basename $BACKUP_FILE)" \
    --region "$S3_REGION" \
    --sse AES256 \
    --storage-class STANDARD_IA; then
    log "✓ S3 upload successful"
else
    log "✗ S3 upload failed"
    exit 1
fi

# Also upload checksum
if aws s3 cp "$CHECKSUM_FILE" "s3://$S3_BUCKET/$TIMESTAMP/$(basename $CHECKSUM_FILE)" \
    --region "$S3_REGION" \
    --sse AES256; then
    log "✓ Checksum uploaded"
else
    log "⚠ Checksum upload failed (non-fatal)"
fi

# Step 4: Verify backup integrity (restore test)
log "Verifying backup integrity..."
TEST_DB="jarvis_backup_test_${TIMESTAMP}"

if docker exec "$DB_CONTAINER" createdb -U "$DB_USER" "$TEST_DB" 2>/dev/null; then
    if gunzip -c "$BACKUP_FILE" | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$TEST_DB" >/dev/null 2>&1; then
        log "✓ Backup verification successful (restore test passed)"
        docker exec "$DB_CONTAINER" dropdb -U "$DB_USER" "$TEST_DB" 2>/dev/null || true
    else
        log "✗ Backup verification failed (restore test failed)"
        docker exec "$DB_CONTAINER" dropdb -U "$DB_USER" "$TEST_DB" 2>/dev/null || true
        exit 1
    fi
else
    log "⚠ Could not verify backup (test database creation failed)"
fi

# Step 5: Cleanup old local backups (keep last 5)
log "Cleaning up old backups (retention: $BACKUP_RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "jarvis_db_*.sql.gz" -mtime +$BACKUP_RETENTION_DAYS -delete

# Step 6: Record backup metadata
METADATA_FILE="$BACKUP_DIR/backups.log"
echo "$(date -Iseconds) | $TIMESTAMP | $(basename $BACKUP_FILE) | $(du -h $BACKUP_FILE | awk '{print $1}') | $CHECKSUM" >> "$METADATA_FILE"

log "=== JARVIS PostgreSQL Backup Completed Successfully ==="
log "Backup size: $(du -h $BACKUP_FILE | awk '{print $1}')"
log "Next backup: $(date -d '+1 day' '+%Y-%m-%d %H:%M:%S')"
