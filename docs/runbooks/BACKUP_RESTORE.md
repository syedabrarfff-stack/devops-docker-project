# Database Backup & Restore Runbook — Aliyar Solutions / JARVIS

## Strategy

| Metric | Target |
|--------|--------|
| RPO (Recovery Point Objective) | 24 hours |
| RTO (Recovery Time Objective) | 30 minutes |
| Backup method | `pg_dump` → gzip → S3 |
| Backup frequency | Nightly at 02:00 UTC |
| Retention | 30 days (S3 Lifecycle policy) |
| Encryption | S3 SSE-S3 (server-side, automatic) |

---

## Backup Script

Located at `scripts/db-backup.sh` — installed as a cron job on EC2.

```bash
#!/bin/bash
# /opt/jarvis/scripts/db-backup.sh
# Runs nightly via cron: 0 2 * * * /opt/jarvis/scripts/db-backup.sh >> /var/log/jarvis-backup.log 2>&1

set -e

DEPLOY_DIR=/opt/jarvis
ENV_FILE="$DEPLOY_DIR/.env"
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
BACKUP_DIR=/tmp/jarvis-backups
S3_BUCKET="${BACKUP_S3_BUCKET:-jarvis-backups-aliyar}"
REGION="${AWS_DEFAULT_REGION:-ap-south-2}"

# Load DB credentials from .env
DB_HOST=$(grep ^DB_HOST "$ENV_FILE" | cut -d= -f2 || echo "localhost")
DB_PORT=$(grep ^DB_PORT "$ENV_FILE" | cut -d= -f2 || echo "5432")
DB_NAME=$(grep ^POSTGRES_DB "$ENV_FILE" | cut -d= -f2 || echo "jarvis_db")
DB_USER=$(grep ^POSTGRES_USER "$ENV_FILE" | cut -d= -f2 || echo "jarvis_user")
DB_PASS=$(grep ^POSTGRES_PASSWORD "$ENV_FILE" | cut -d= -f2)

mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/jarvis_${TIMESTAMP}.sql.gz"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting backup: $BACKUP_FILE"

# Dump via running postgres container
PGPASSWORD="$DB_PASS" docker exec jarvis_postgres \
  pg_dump -U "$DB_USER" -d "$DB_NAME" -Fp --no-password \
  | gzip > "$BACKUP_FILE"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Dump complete: $(du -sh "$BACKUP_FILE" | cut -f1)"

# Upload to S3
aws s3 cp "$BACKUP_FILE" \
  "s3://${S3_BUCKET}/daily/$(basename "$BACKUP_FILE")" \
  --region "$REGION" \
  --storage-class STANDARD_IA

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Uploaded to s3://${S3_BUCKET}/daily/"

# Verify upload
aws s3 ls "s3://${S3_BUCKET}/daily/$(basename "$BACKUP_FILE")" --region "$REGION" \
  && echo "BACKUP_VERIFIED" || echo "BACKUP_UPLOAD_CHECK_FAILED"

# Cleanup local file (S3 is source of truth)
rm -f "$BACKUP_FILE"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Backup complete."
```

---

## Installing the Cron Job on EC2

```bash
# SSH or SSM into EC2

# Copy backup script
cp /opt/jarvis/scripts/db-backup.sh /usr/local/bin/jarvis-db-backup
chmod +x /usr/local/bin/jarvis-db-backup

# Install cron job (runs at 02:00 UTC nightly)
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/jarvis-db-backup >> /var/log/jarvis-backup.log 2>&1") | crontab -

# Verify
crontab -l
```

---

## S3 Bucket Setup

Create the S3 bucket with a 30-day lifecycle rule:

```bash
REGION=ap-south-2
BUCKET=jarvis-backups-aliyar

# Create bucket
aws s3api create-bucket \
  --bucket "$BUCKET" \
  --region "$REGION" \
  --create-bucket-configuration LocationConstraint="$REGION"

# Block all public access
aws s3api put-public-access-block \
  --bucket "$BUCKET" \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket "$BUCKET" \
  --versioning-configuration Status=Enabled

# 30-day expiry lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket "$BUCKET" \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "expire-backups-30d",
      "Status": "Enabled",
      "Filter": {"Prefix": "daily/"},
      "Expiration": {"Days": 30}
    }]
  }'

# IAM: EC2 instance role needs s3:PutObject + s3:GetObject on this bucket
```

---

## Restore Procedure

**Target RTO: 30 minutes from decision to healthy system.**

### Step 1 — Identify the backup to restore (5 min)

```bash
aws s3 ls s3://jarvis-backups-aliyar/daily/ --region ap-south-2 | sort | tail -10
# Pick the most recent file, e.g.: jarvis_20260703_020001.sql.gz
```

### Step 2 — Download the backup (2 min)

```bash
aws s3 cp s3://jarvis-backups-aliyar/daily/jarvis_20260703_020001.sql.gz \
  /tmp/restore.sql.gz --region ap-south-2
```

### Step 3 — Stop backend, restore DB (15 min)

```bash
cd /opt/jarvis/infrastructure

# Stop backend to prevent writes during restore
docker-compose -p jarvis stop backend

# Drop and recreate the database
docker exec jarvis_postgres psql -U jarvis_user -c "DROP DATABASE IF EXISTS jarvis_db;"
docker exec jarvis_postgres psql -U jarvis_user -c "CREATE DATABASE jarvis_db;"

# Restore
gunzip -c /tmp/restore.sql.gz | docker exec -i jarvis_postgres \
  psql -U jarvis_user -d jarvis_db

echo "Restore complete"
```

### Step 4 — Run migrations to apply any schema changes since backup (3 min)

```bash
docker-compose -p jarvis start backend
sleep 20
docker-compose -p jarvis exec -T backend alembic upgrade head
```

### Step 5 — Verify health (5 min)

```bash
curl -sf http://localhost:8000/health | python3 -m json.tool
curl -sf http://localhost:8000/readyz | python3 -m json.tool
echo "RESTORE COMPLETE"
```

---

## Testing the Backup (Monthly)

Run this on the first Sunday of each month:

```bash
# Download latest backup into a test container
docker run --rm -e POSTGRES_PASSWORD=test -e POSTGRES_DB=test_jarvis \
  -d --name pg_restore_test postgres:16

docker exec pg_restore_test psql -U postgres -c "CREATE DATABASE test_jarvis;"

aws s3 cp "$(aws s3 ls s3://jarvis-backups-aliyar/daily/ --region ap-south-2 \
  | sort | tail -1 | awk '{print "s3://jarvis-backups-aliyar/daily/"$4}')" \
  /tmp/test_restore.sql.gz --region ap-south-2

gunzip -c /tmp/test_restore.sql.gz | docker exec -i pg_restore_test \
  psql -U postgres -d test_jarvis

# Verify row counts on critical tables
docker exec pg_restore_test psql -U postgres -d test_jarvis \
  -c "SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 20;"

docker stop pg_restore_test
echo "BACKUP_TEST_COMPLETE"
```

---

## Monitoring

- Backup log: `/var/log/jarvis-backup.log` on EC2
- Alert: If no `BACKUP_VERIFIED` in the log by 02:30 UTC, Captain is notified by the `self_healer` job (every 15min)
- S3 console: `s3://jarvis-backups-aliyar/daily/`
