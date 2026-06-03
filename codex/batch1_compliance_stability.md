# JARVIS CODEX BATCH 1 — COMPLIANCE + STABILITY
## Build this FIRST before any other batch

---

## CONTEXT

You are working on the LIVE JARVIS system on EC2.
- App directory: `/home/ubuntu/jarvis_sales_pipeline/`
- Stack: FastAPI + SQLAlchemy async + PostgreSQL + Redis + APScheduler
- Deploy command: `docker-compose up -d --build jarvis_app`
- Never touch `.env`
- Run migrations: `docker-compose exec jarvis_app alembic upgrade head`

This batch covers:
- Email Compliance Engine (CAN-SPAM / GDPR)
- Timezone-aware outreach gating
- Lead qualification routing (65/45 thresholds)
- Reply rate auto-pause
- GDPR erasure endpoint
- Proposal auto-follow-up sequences
- Distributed Redis job locking on ALL APScheduler jobs
- Dead letter queue with Telegram alerts
- Daily database backup (pg_dump → local + optional S3)
- Graceful AI degradation (raw data fallback when all providers fail)
- Webhook idempotency layer
- Loss reason tracking on archived deals

---

## STEP 1 — DATABASE MIGRATION

Create file: `alembic/versions/0009_compliance_stability.py`

```python
"""compliance and stability tables

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade():
    # Email compliance
    op.create_table('dnc_list',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(320), nullable=False, unique=True),
        sa.Column('reason', sa.String(255)),
        sa.Column('added_by', sa.String(100), default='system'),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_dnc_list_email', 'dnc_list', ['email'])

    op.create_table('unsubscribes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(320), nullable=False),
        sa.Column('sequence_id', sa.Integer()),
        sa.Column('campaign_name', sa.String(255)),
        sa.Column('unsubscribed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_unsubscribes_email', 'unsubscribes', ['email'])

    op.create_table('gdpr_erasures',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('original_contact_id_hash', sa.String(64)),
        sa.Column('original_email_hash', sa.String(64)),
        sa.Column('erased_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('requestor_note', sa.Text()),
        sa.Column('erased_by', sa.String(100)),
    )

    op.create_table('outreach_daily_caps',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('sender_domain', sa.String(255), nullable=False),
        sa.Column('send_date', sa.Date(), nullable=False),
        sa.Column('send_count', sa.Integer(), default=0),
    )
    op.create_unique_constraint('uq_daily_cap', 'outreach_daily_caps', ['sender_domain', 'send_date'])

    # Stability
    op.create_table('dead_letter_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('job_name', sa.String(255), nullable=False),
        sa.Column('error_message', sa.Text()),
        sa.Column('error_traceback', sa.Text()),
        sa.Column('payload', JSONB),
        sa.Column('attempt_count', sa.Integer(), default=1),
        sa.Column('failed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('resolved', sa.Boolean(), default=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
    )

    op.create_table('processed_webhooks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('webhook_id', sa.String(255), nullable=False),
        sa.Column('source', sa.String(100)),
        sa.Column('payload_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_processed_webhooks_hash', 'processed_webhooks', ['payload_hash'])

    op.create_table('backup_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('backup_file', sa.String(500)),
        sa.Column('backup_size_mb', sa.Float()),
        sa.Column('duration_seconds', sa.Float()),
        sa.Column('s3_uploaded', sa.Boolean(), default=False),
        sa.Column('success', sa.Boolean(), default=True),
        sa.Column('error_message', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Loss reasons on proposals/leads
    try:
        op.add_column('proposals', sa.Column('loss_reason', sa.String(100)))
        op.add_column('proposals', sa.Column('loss_reason_detail', sa.Text()))
        op.add_column('proposals', sa.Column('lost_to_competitor', sa.String(255)))
    except Exception:
        pass  # column may already exist

    try:
        op.add_column('leads', sa.Column('disqualification_reason', sa.String(255)))
        op.add_column('leads', sa.Column('review_queue', sa.Boolean(), default=False))
    except Exception:
        pass


def downgrade():
    op.drop_table('backup_log')
    op.drop_table('processed_webhooks')
    op.drop_table('dead_letter_jobs')
    op.drop_table('outreach_daily_caps')
    op.drop_table('gdpr_erasures')
    op.drop_table('unsubscribes')
    op.drop_table('dnc_list')
```

---

## STEP 2 — EMAIL COMPLIANCE ENGINE

Create file: `app/services/outreach/compliance.py`

```python
"""Email compliance: CAN-SPAM, GDPR, timezone gating, send caps."""
import hashlib
import logging
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

logger = logging.getLogger(__name__)

DAILY_SEND_CAP = 50
SEND_WINDOW_START = 8.5   # 08:30 local time
SEND_WINDOW_END = 17.5    # 17:30 local time
ALLOWED_DAYS = {0, 1, 2, 3, 4}  # Mon-Fri


async def is_contact_eligible(db: AsyncSession, contact_id: int, contact_email: str,
                               contact_timezone: str = "UTC") -> tuple[bool, str]:
    """Returns (eligible, reason). Reason is empty string if eligible."""
    # Check GDPR erasure
    email_hash = hashlib.sha256(contact_email.lower().encode()).hexdigest()
    erased = (await db.execute(
        text("SELECT id FROM gdpr_erasures WHERE original_email_hash = :h"),
        {"h": email_hash}
    )).scalar_one_or_none()
    if erased:
        return False, "gdpr_erased"

    # Check DNC list
    dnc = (await db.execute(
        text("SELECT id FROM dnc_list WHERE email = :e"),
        {"e": contact_email.lower()}
    )).scalar_one_or_none()
    if dnc:
        return False, "dnc_list"

    # Check unsubscribes
    unsub = (await db.execute(
        text("SELECT id FROM unsubscribes WHERE email = :e"),
        {"e": contact_email.lower()}
    )).scalar_one_or_none()
    if unsub:
        return False, "unsubscribed"

    # Timezone window check
    try:
        tz = ZoneInfo(contact_timezone)
        local_now = datetime.now(tz)
        hour_decimal = local_now.hour + local_now.minute / 60
        if local_now.weekday() not in ALLOWED_DAYS:
            return False, "weekend"
        if not (SEND_WINDOW_START <= hour_decimal <= SEND_WINDOW_END):
            return False, f"outside_hours_{local_now.strftime('%H:%M')}_local"
    except Exception:
        pass  # Unknown timezone — allow but log

    # Daily send cap check
    today = date.today()
    # Extract domain from sender email (use aliyarsolutions.com as default)
    sender_domain = "aliyarsolutions.com"
    result = (await db.execute(
        text("SELECT send_count FROM outreach_daily_caps WHERE sender_domain=:d AND send_date=:dt"),
        {"d": sender_domain, "dt": today}
    )).scalar_one_or_none()
    if result and result >= DAILY_SEND_CAP:
        return False, f"daily_cap_reached_{result}"

    return True, ""


async def increment_daily_cap(db: AsyncSession, sender_domain: str = "aliyarsolutions.com"):
    today = date.today()
    await db.execute(text("""
        INSERT INTO outreach_daily_caps (sender_domain, send_date, send_count)
        VALUES (:d, :dt, 1)
        ON CONFLICT ON CONSTRAINT uq_daily_cap
        DO UPDATE SET send_count = outreach_daily_caps.send_count + 1
    """), {"d": sender_domain, "dt": today})


async def add_to_dnc(db: AsyncSession, email: str, reason: str, added_by: str = "system"):
    await db.execute(text("""
        INSERT INTO dnc_list (email, reason, added_by)
        VALUES (:e, :r, :b)
        ON CONFLICT (email) DO NOTHING
    """), {"e": email.lower(), "r": reason, "b": added_by})
    await db.commit()
    logger.info(f"Added {email} to DNC list: {reason}")


async def process_unsubscribe(db: AsyncSession, email: str, sequence_id: int = None):
    await db.execute(text("""
        INSERT INTO unsubscribes (email, sequence_id)
        VALUES (:e, :s)
    """), {"e": email.lower(), "s": sequence_id})
    await db.commit()
    logger.info(f"Unsubscribe processed: {email}")


async def gdpr_erase_contact(db: AsyncSession, contact_id: int, requestor_note: str = ""):
    """Wipe all PII from contact, keep anonymized record for audit."""
    # Get current contact email for hashing
    result = (await db.execute(
        text("SELECT email, name FROM leads WHERE id = :id LIMIT 1"),
        {"id": contact_id}
    )).fetchone()

    if result:
        email_hash = hashlib.sha256((result[0] or "").lower().encode()).hexdigest()
        id_hash = hashlib.sha256(str(contact_id).encode()).hexdigest()

        # Insert erasure record
        await db.execute(text("""
            INSERT INTO gdpr_erasures (original_contact_id_hash, original_email_hash, requestor_note, erased_by)
            VALUES (:id_hash, :email_hash, :note, 'captain_gdpr_request')
        """), {"id_hash": id_hash, "email_hash": email_hash, "note": requestor_note})

        # Wipe PII from leads table (adjust column names to match your actual schema)
        await db.execute(text("""
            UPDATE leads SET
                email = 'gdpr-erased@removed.invalid',
                name = 'GDPR Erased',
                phone = NULL,
                linkedin_url = NULL,
                notes = '[GDPR ERASED]'
            WHERE id = :id
        """), {"id": contact_id})

        await db.commit()
        logger.info(f"GDPR erasure complete for contact {contact_id}")
        return True
    return False


def build_compliant_footer() -> str:
    return (
        "\n\n---\n"
        "Aliyar Solutions | Technology & Automation\n"
        "To unsubscribe from future emails, reply with STOP\n"
        "or email privacy@aliyarsolutions.com\n"
        "Aliyar Solutions, International Business Centre"
    )
```

---

## STEP 3 — ADD COMPLIANCE CHECK TO OUTREACH SEND FLOW

In your outreach sending logic (wherever emails are dispatched), wrap with:

```python
from app.services.outreach.compliance import is_contact_eligible, increment_daily_cap, build_compliant_footer

# Before sending each email:
eligible, reason = await is_contact_eligible(db, contact.id, contact.email, 
                                              getattr(contact, 'timezone', 'UTC'))
if not eligible:
    logger.info(f"Skipping email to {contact.email}: {reason}")
    # Update scheduled email status
    email_record.status = 'skipped'
    email_record.skip_reason = reason
    continue

# Append compliant footer to body
email_body = email_body + build_compliant_footer()

# After successful send:
await increment_daily_cap(db)
```

Add `skip_reason` column to your outreach_log / emails table if it doesn't exist.

---

## STEP 4 — ADD COMPLIANCE API ROUTES

In your main `app.py` or routes file, add:

```python
@app.post("/api/v1/outreach/unsubscribe")
async def unsubscribe(data: dict, db=Depends(get_db)):
    """Public endpoint — called from email footer link."""
    email = data.get("email", "").strip()
    if not email:
        raise HTTPException(400, "email required")
    from app.services.outreach.compliance import process_unsubscribe
    await process_unsubscribe(db, email, data.get("sequence_id"))
    return {"status": "unsubscribed", "message": "You have been removed from our mailing list."}


@app.post("/api/v1/outreach/dnc/add")
async def add_dnc(data: dict, db=Depends(get_db)):
    """Add email to Do Not Contact list."""
    from app.services.outreach.compliance import add_to_dnc
    await add_to_dnc(db, data["email"], data.get("reason", "manual"), data.get("added_by", "captain"))
    return {"status": "added_to_dnc"}


@app.delete("/api/v1/contacts/{contact_id}/gdpr-erase")
async def gdpr_erase(contact_id: int, data: dict = {}, db=Depends(get_db)):
    """GDPR right-to-erasure — wipes all PII."""
    from app.services.outreach.compliance import gdpr_erase_contact
    success = await gdpr_erase_contact(db, contact_id, data.get("note", ""))
    if not success:
        raise HTTPException(404, "Contact not found")
    return {"status": "erased", "contact_id": contact_id}
```

---

## STEP 5 — LEAD QUALIFICATION THRESHOLDS

Find your lead scoring function. After computing `score`, add routing:

```python
async def route_lead_after_scoring(db: AsyncSession, lead_id: int, score: int):
    """Route lead based on score threshold."""
    if score >= 65:
        # Auto-enroll in matching outreach sequence
        await auto_enroll_lead(db, lead_id)
        await db.execute(text(
            "UPDATE leads SET outreach_eligible=true, status='auto_enrolled' WHERE id=:id"
        ), {"id": lead_id})
        logger.info(f"Lead {lead_id} score {score} — auto-enrolled in outreach")

    elif 45 <= score < 65:
        # Add to Captain review queue
        await db.execute(text("""
            INSERT INTO jarvis_captain_queue (item_type, item_id, priority, title, description, status)
            VALUES ('lead_review', :id, 'normal', 
                    'Lead Needs Review (Score: ' || :score || ')',
                    'Score in review zone — manual decision required', 'pending')
            ON CONFLICT DO NOTHING
        """), {"id": lead_id, "score": score})
        await db.execute(text(
            "UPDATE leads SET review_queue=true WHERE id=:id"
        ), {"id": lead_id})
        logger.info(f"Lead {lead_id} score {score} — added to Captain review queue")

    else:
        # Store only, no outreach
        await db.execute(text(
            "UPDATE leads SET outreach_eligible=false, disqualification_reason='score_below_threshold' WHERE id=:id"
        ), {"id": lead_id})
        logger.info(f"Lead {lead_id} score {score} — below threshold, stored only")
```

Add `outreach_eligible` boolean column to leads table if missing.

---

## STEP 6 — REPLY RATE AUTO-PAUSE

Create file: `app/services/outreach/performance_monitor.py`

```python
"""Monitor outreach performance and auto-pause underperforming sequences."""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
REPLY_RATE_THRESHOLD = 1.5  # percent
EVALUATION_DAYS = 7


async def check_and_pause_sequences(db: AsyncSession):
    """Run daily at 23:30 UTC. Pause sequences with reply rate below threshold."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=EVALUATION_DAYS)

    # Get all active sequences with enough volume to evaluate
    sequences = (await db.execute(text("""
        SELECT id, name, emails_sent, replies_received
        FROM outreach_sequences
        WHERE status = 'active'
        AND emails_sent >= 20
        AND created_at < :cutoff
    """), {"cutoff": cutoff})).fetchall()

    paused = []
    for seq in sequences:
        seq_id, name, sent, replies = seq
        if sent == 0:
            continue
        reply_rate = (replies / sent) * 100
        if reply_rate < REPLY_RATE_THRESHOLD:
            # Pause sequence
            await db.execute(text("""
                UPDATE outreach_sequences 
                SET status='paused', updated_at=NOW()
                WHERE id = :id
            """), {"id": seq_id})
            paused.append({"id": seq_id, "name": name, "rate": round(reply_rate, 2), "sent": sent})
            logger.warning(f"Sequence '{name}' paused — reply rate {reply_rate:.2f}% below {REPLY_RATE_THRESHOLD}%")

    if paused:
        await db.commit()
        # Send Telegram alert
        try:
            from app.services.notifications import send_telegram
            msg = "⚠️ *JARVIS Outreach Alert*\n\n"
            for p in paused:
                msg += f"Sequence *{p['name']}* paused\n"
                msg += f"Reply rate: {p['rate']}% ({p['sent']} emails sent)\n"
                msg += f"Threshold: {REPLY_RATE_THRESHOLD}%\n\n"
            msg += "Review sequences at /outreach dashboard."
            await send_telegram(msg)
        except Exception as e:
            logger.error(f"Telegram alert failed: {e}")

    return paused
```

Register as APScheduler job (daily at 23:30 UTC):
```python
scheduler.add_job(
    check_and_pause_sequences_job,
    'cron', hour=23, minute=30,
    id='reply_rate_monitor',
    replace_existing=True
)
```

---

## STEP 7 — PROPOSAL AUTO-FOLLOW-UP

In your proposal service, after a proposal is created with status `sent`:

```python
async def schedule_proposal_followup(db: AsyncSession, proposal_id: int, client_name: str, client_email: str):
    """Create 4 follow-up tasks at Day 3, 7, 14, 21."""
    from datetime import datetime, timezone, timedelta
    
    followup_schedule = [
        (3,  "Gentle check-in — confirm proposal received"),
        (7,  "Value reinforcement — share relevant case study"),
        (14, "Address possible objections — offer demo call"),
        (21, "Final follow-up — decision or close loop"),
    ]
    
    now = datetime.now(timezone.utc)
    for days, description in followup_schedule:
        scheduled_at = now + timedelta(days=days)
        await db.execute(text("""
            INSERT INTO jarvis_tasks (title, description, task_type, priority, 
                                      status, scheduled_at, metadata)
            VALUES (:title, :desc, 'proposal_followup', 'high', 'scheduled', :at, :meta)
        """), {
            "title": f"Follow-up: {client_name} — Day {days}",
            "desc": description,
            "at": scheduled_at,
            "meta": f'{{"proposal_id": {proposal_id}, "client_email": "{client_email}", "day": {days}}}'
        })
    
    await db.commit()
    logger.info(f"Scheduled 4 follow-up tasks for proposal {proposal_id}")
```

Call `schedule_proposal_followup()` immediately after every proposal is sent.

---

## STEP 8 — DISTRIBUTED JOB LOCKING

Create file: `app/services/scheduler/job_lock.py`

```python
"""Redis-based distributed locking for APScheduler jobs."""
import logging
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)


async def with_job_lock(job_name: str, fn, timeout_seconds: int = 300):
    """Execute fn only if this job isn't already running (Redis lock)."""
    try:
        import redis.asyncio as aioredis
        import os
        redis_url = os.getenv("REDIS_URL", "redis://jarvis_redis:6379/0")
        r = aioredis.from_url(redis_url, decode_responses=True)
        
        lock_key = f"jarvis:job_lock:{job_name}"
        acquired = await r.set(lock_key, "1", nx=True, ex=timeout_seconds)
        
        if not acquired:
            logger.info(f"[LOCK] Job '{job_name}' already running — skipping this execution")
            await r.aclose()
            return None
        
        try:
            result = await fn()
            return result
        finally:
            await r.delete(lock_key)
            await r.aclose()
    except Exception as e:
        logger.error(f"[LOCK] Lock mechanism failed for {job_name}: {e}")
        # If Redis fails, run the job anyway (fail-open)
        return await fn()


def locked_job(job_name: str, timeout: int = 300):
    """Decorator for APScheduler job functions."""
    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            return await with_job_lock(job_name, lambda: fn(*args, **kwargs), timeout)
        return wrapper
    return decorator
```

Apply to ALL scheduled jobs. Example:
```python
from app.services.scheduler.job_lock import locked_job

@locked_job("morning_briefing", timeout=600)
async def run_morning_briefing():
    # existing code

@locked_job("lead_scorer", timeout=300)
async def run_lead_scoring():
    # existing code
```

Apply `@locked_job` decorator to every job in your scheduler setup.

---

## STEP 9 — DEAD LETTER QUEUE

Create file: `app/services/scheduler/dead_letter.py`

```python
"""Dead letter queue — capture failed jobs with retry logic."""
import logging
import asyncio
import traceback
from datetime import datetime, timezone
from functools import wraps

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [300, 900, 2700]  # 5min, 15min, 45min


async def _write_dead_letter(job_name: str, error: Exception, payload: dict, attempt: int, db_url: str):
    try:
        import asyncpg
        conn = await asyncpg.connect(db_url)
        await conn.execute("""
            INSERT INTO dead_letter_jobs (job_name, error_message, error_traceback, payload, attempt_count)
            VALUES ($1, $2, $3, $4::jsonb, $5)
        """, job_name, str(error), traceback.format_exc(), str(payload), attempt)
        await conn.close()
    except Exception as e:
        logger.error(f"Failed to write dead letter: {e}")


async def resilient_job(job_name: str, fn, payload: dict = None, db_url: str = None):
    """Run fn with retry logic. On final failure, write to dead_letter_jobs and alert Captain."""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = await fn()
            if attempt > 1:
                logger.info(f"[DLQ] Job '{job_name}' succeeded on attempt {attempt}")
            return result
        except Exception as e:
            last_error = e
            logger.error(f"[DLQ] Job '{job_name}' attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAYS[attempt - 1]
                logger.info(f"[DLQ] Retrying '{job_name}' in {delay}s")
                await asyncio.sleep(delay)

    # All retries exhausted
    logger.critical(f"[DLQ] Job '{job_name}' failed after {MAX_RETRIES} attempts")
    if db_url:
        await _write_dead_letter(job_name, last_error, payload or {}, MAX_RETRIES, db_url)
    
    # Telegram alert
    try:
        from app.services.notifications import send_telegram
        msg = (f"🔴 *JARVIS Job Failed*\n\n"
               f"Job: `{job_name}`\n"
               f"Error: `{str(last_error)[:200]}`\n"
               f"Attempts: {MAX_RETRIES}\n"
               f"Action required: check `/api/v1/system/dead-letters`")
        await send_telegram(msg)
    except Exception:
        pass

    raise last_error
```

Add API endpoint to view dead letter queue:
```python
@app.get("/api/v1/system/dead-letters")
async def get_dead_letters(db=Depends(get_db)):
    rows = await db.execute(text(
        "SELECT * FROM dead_letter_jobs WHERE resolved=false ORDER BY failed_at DESC LIMIT 50"
    ))
    return {"dead_letters": [dict(r) for r in rows.fetchall()]}

@app.post("/api/v1/system/dead-letters/{id}/resolve")
async def resolve_dead_letter(id: int, db=Depends(get_db)):
    await db.execute(text(
        "UPDATE dead_letter_jobs SET resolved=true, resolved_at=NOW() WHERE id=:id"
    ), {"id": id})
    await db.commit()
    return {"status": "resolved"}
```

---

## STEP 10 — DAILY DATABASE BACKUP

Create file: `app/services/system/backup.py`

```python
"""Daily pg_dump backup with optional S3 upload."""
import os
import logging
import asyncio
import subprocess
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def run_daily_backup():
    """Run at 01:00 UTC. Dump PostgreSQL to file, optionally upload to S3."""
    start = datetime.now(timezone.utc)
    date_str = start.strftime("%Y%m%d_%H%M%S")
    backup_dir = "/tmp/jarvis_backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    # Keep only last 7 local backups
    _cleanup_old_backups(backup_dir, keep=7)
    
    backup_file = f"{backup_dir}/jarvis_backup_{date_str}.sql"
    db_url = os.getenv("DATABASE_URL", "")
    
    # Extract connection params
    # Expected format: postgresql+asyncpg://user:pass@host:port/dbname
    # Convert to pg_dump format
    pg_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")
    
    try:
        proc = subprocess.run(
            ["pg_dump", pg_url, "-f", backup_file, "--no-password"],
            capture_output=True, text=True, timeout=300
        )
        
        if proc.returncode != 0:
            raise Exception(f"pg_dump failed: {proc.stderr}")
        
        file_size_mb = os.path.getsize(backup_file) / (1024 * 1024)
        duration = (datetime.now(timezone.utc) - start).total_seconds()
        
        s3_uploaded = False
        s3_bucket = os.getenv("BACKUP_S3_BUCKET", "")
        if s3_bucket:
            try:
                import boto3
                s3 = boto3.client("s3")
                s3_key = f"daily/jarvis_backup_{date_str}.sql"
                s3.upload_file(backup_file, s3_bucket, s3_key)
                s3_uploaded = True
                logger.info(f"Backup uploaded to s3://{s3_bucket}/{s3_key}")
            except Exception as e:
                logger.warning(f"S3 upload failed (keeping local): {e}")
        
        logger.info(f"Backup complete: {file_size_mb:.1f}MB in {duration:.1f}s — {backup_file}")
        return {"success": True, "file": backup_file, "size_mb": file_size_mb, 
                "duration_s": duration, "s3_uploaded": s3_uploaded}

    except Exception as e:
        logger.error(f"Backup failed: {e}")
        try:
            from app.services.notifications import send_telegram
            await send_telegram(f"🔴 *JARVIS Backup Failed*\n\nError: `{str(e)[:300]}`\nTime: {start.isoformat()}")
        except Exception:
            pass
        return {"success": False, "error": str(e)}


def _cleanup_old_backups(backup_dir: str, keep: int = 7):
    import glob
    files = sorted(glob.glob(f"{backup_dir}/jarvis_backup_*.sql"))
    for old_file in files[:-keep]:
        try:
            os.remove(old_file)
            logger.info(f"Deleted old backup: {old_file}")
        except Exception:
            pass
```

Register as APScheduler job (daily at 01:00 UTC):
```python
scheduler.add_job(
    run_daily_backup_job,
    'cron', hour=1, minute=0,
    id='daily_backup',
    replace_existing=True
)
```

---

## STEP 11 — GRACEFUL AI DEGRADATION

In your AI router / wherever you call AI providers, add a degradation wrapper:

```python
import os

_degraded_mode = False


def is_degraded() -> bool:
    return _degraded_mode


def set_degraded(degraded: bool):
    global _degraded_mode
    if degraded != _degraded_mode:
        _degraded_mode = degraded
        logger.warning(f"AI mode changed: {'DEGRADED' if degraded else 'NORMAL'}")


async def ai_with_fallback(fn, fallback_fn, job_name: str = ""):
    """Try AI call; if it fails, return raw data fallback."""
    try:
        result = await fn()
        set_degraded(False)
        return result, False  # (result, is_degraded)
    except Exception as e:
        logger.error(f"AI call failed for '{job_name}': {e}")
        set_degraded(True)
        try:
            from app.services.notifications import send_telegram
            await send_telegram(
                f"⚠️ *JARVIS AI Layer Degraded*\n\n"
                f"All providers failed for: `{job_name}`\n"
                f"Error: `{str(e)[:200]}`\n"
                f"System running on cached intelligence."
            )
        except Exception:
            pass
        fallback = await fallback_fn()
        return fallback, True  # (result, is_degraded)
```

In every route response, add `"ai_degraded": is_degraded()` to the response.

---

## STEP 12 — WEBHOOK IDEMPOTENCY

In every webhook handler, add at the top:

```python
import hashlib
import json

async def is_duplicate_webhook(db: AsyncSession, payload: dict, source: str) -> bool:
    payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    existing = (await db.execute(text(
        "SELECT id FROM processed_webhooks WHERE payload_hash = :h"
    ), {"h": payload_hash})).scalar_one_or_none()
    
    if existing:
        return True
    
    # Record as processed
    await db.execute(text("""
        INSERT INTO processed_webhooks (webhook_id, source, payload_hash)
        VALUES (:wid, :src, :h)
    """), {
        "wid": payload.get("id", payload_hash[:16]),
        "src": source,
        "h": payload_hash
    })
    return False
```

Usage in webhook routes:
```python
@app.post("/api/v1/webhooks/hubspot")
async def hubspot_webhook(request: Request, db=Depends(get_db)):
    payload = await request.json()
    if await is_duplicate_webhook(db, payload, "hubspot"):
        return {"status": "duplicate", "skipped": True}
    # process webhook...
```

---

## STEP 13 — DEPLOY AND VERIFY

```bash
cd /home/ubuntu/jarvis_sales_pipeline

# Run migration
docker-compose exec jarvis_app alembic upgrade head

# Rebuild
docker-compose up -d --build jarvis_app

# Wait for startup
sleep 15

# Verify health
curl -s http://localhost:8000/health | python3 -m json.tool

# Test compliance endpoints
curl -s -X POST http://localhost:8000/api/v1/outreach/dnc/add \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","reason":"manual_test"}' | python3 -m json.tool

curl -s http://localhost:8000/api/v1/system/dead-letters | python3 -m json.tool

# Commit
git add -A
git commit -m "feat(batch1): compliance engine, stability layer, job locking, backup"
git push origin main
```

---

## VERIFICATION CHECKLIST

- [ ] Migration 0009 applied — all new tables exist
- [ ] `/api/v1/outreach/unsubscribe` returns 200
- [ ] `/api/v1/outreach/dnc/add` returns 200
- [ ] `/api/v1/contacts/{id}/gdpr-erase` returns 200
- [ ] `/api/v1/system/dead-letters` returns JSON with empty list
- [ ] Daily backup job registered in APScheduler
- [ ] Reply rate monitor job registered in APScheduler
- [ ] All existing scheduler jobs wrapped with `@locked_job`
- [ ] Compliance check runs before every outreach email
- [ ] Footer appended to all outgoing emails

**Batch 1 complete. Proceed to Batch 2.**
