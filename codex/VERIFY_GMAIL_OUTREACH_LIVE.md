# JARVIS Outreach — Gmail Live Verification & First Send

Paste this to Codex and execute against `/opt/jarvis` on EC2.

---

## OBJECTIVE

Gmail credentials (info@aliyarsolutions.com) are already in `.env` on EC2.
Verify the outreach engine is live and trigger the first real email send.

---

## STEP 1 — Confirm Gmail credentials are loaded

```bash
grep "GMAIL_ADDRESS\|GMAIL_APP_PASSWORD" /opt/jarvis/.env
```

Expected:
```
GMAIL_ADDRESS=info@aliyarsolutions.com
GMAIL_APP_PASSWORD=<16-char app password>
```

If missing, STOP and report. Do not continue.

---

## STEP 2 — Test Gmail connection from inside the container

```bash
docker-compose -f /opt/jarvis/docker-compose.yml exec backend python3 -c "
import asyncio, sys
sys.path.insert(0, '/app')
from app.services.notifications.gmail_sender import gmail_sender
result = asyncio.run(gmail_sender.test_connection())
print('GMAIL STATUS:', result)
"
```

Expected: `GMAIL STATUS: True` or connection confirmed.

---

## STEP 3 — Send a test email to Captain

```bash
docker-compose -f /opt/jarvis/docker-compose.yml exec backend python3 -c "
import asyncio, sys
sys.path.insert(0, '/app')
from app.services.notifications.gmail_sender import gmail_sender
result = asyncio.run(gmail_sender.send_email(
    to='syedabrarbhd@gmail.com',
    subject='JARVIS Outreach Engine — Live Confirmation',
    body='Captain, the outreach engine is confirmed live. info@aliyarsolutions.com is authenticated and sending. JARVIS is operational.',
    from_name='Darren Mitchell'
))
print('SEND RESULT:', result)
"
```

Expected: `SEND RESULT:` with success. Captain receives the email at syedabrarbhd@gmail.com.

---

## STEP 4 — Check how many leads are queued for outreach

```bash
docker-compose -f /opt/jarvis/docker-compose.yml exec backend python3 -c "
import asyncio, sys
sys.path.insert(0, '/app')
from app.core.database import get_db
from app.models.lead import Lead
async def count():
    async for db in get_db():
        from sqlalchemy import select, func
        result = await db.execute(select(func.count()).where(Lead.outreach_status == 'pending'))
        count = result.scalar()
        print(f'Leads queued for outreach: {count}')
        break
asyncio.run(count())
"
```

---

## STEP 5 — Trigger outreach manually (first real send)

```bash
curl -s -X POST http://localhost:8000/api/v1/outreach/execute \
  -H "Content-Type: application/json" \
  -d '{"limit": 48, "dry_run": false}' \
  | python3 -m json.tool
```

Expected: JSON showing emails sent count, leads contacted, any errors.

---

## STEP 6 — Check outreach logs

```bash
docker-compose -f /opt/jarvis/docker-compose.yml logs backend --tail=100 | grep -i "outreach\|email\|smtp\|sent\|gmail" | tail -30
```

Look for: `sent`, `delivered`, `outreach executed` — no auth errors.

---

## STEP 7 — Verify daily scheduler is wired

```bash
curl -s http://localhost:8000/api/v1/scheduler/jobs | python3 -m json.tool | grep -A2 "outreach\|briefing\|lead_score"
```

Expected: Jobs listed with next run times. Outreach job should show today or tomorrow.

---

## STEP 8 — Check compliance cap

```bash
curl -s http://localhost:8000/api/v1/outreach/stats | python3 -m json.tool
```

Confirm: `daily_cap: 48`, `sent_today` counter visible.

---

## SUCCESS CRITERIA

- [ ] GMAIL_ADDRESS=info@aliyarsolutions.com confirmed in .env
- [ ] Gmail connection test returns True
- [ ] Test email arrives at syedabrarbhd@gmail.com
- [ ] Outreach execute returns sent count > 0 (if leads queued)
- [ ] No SMTP auth errors in logs
- [ ] Scheduler jobs confirmed running

---

## REPORT BACK

Provide:
1. Gmail connection test result
2. Whether test email was sent successfully
3. How many leads were in the outreach queue
4. How many emails were sent in Step 5
5. Any errors

The outreach engine is live. Let's confirm it and start sending.
