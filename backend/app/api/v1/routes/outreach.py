from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.outreach import sequences as seq_service
from app.services.outreach import gmail as gmail_service

router = APIRouter(prefix="/outreach", tags=["Outreach"])


class SequenceIn(BaseModel):
    name: str
    target_industry: Optional[str] = "saas"
    target_country: Optional[str] = "usa"
    service_offered: Optional[str] = "AI automation"
    steps: Optional[list[dict]] = None


class EnrollIn(BaseModel):
    contact_ids: list[int]


class SendEmailIn(BaseModel):
    to_email: str
    to_name: Optional[str] = ""
    subject: str
    body: str


# ── Sequences ─────────────────────────────────────────────────────────────

@router.post("/sequences")
async def create_sequence(
    body: SequenceIn,
    background_tasks: BackgroundTasks,
    ai_generate: bool = False,
    db: AsyncSession = Depends(get_db),
):
    seq = await seq_service.create_sequence(db, body.model_dump(exclude_none=True))
    await db.commit()
    if ai_generate:
        background_tasks.add_task(
            _generate_ai_steps, seq.id,
            body.target_industry, body.target_country, body.service_offered
        )
    return {"id": seq.id, "name": seq.name, "total_steps": seq.total_steps}


async def _generate_ai_steps(seq_id: int, industry: str, country: str, service: str):
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        async with db.begin():
            await seq_service.generate_sequence_with_ai(db, industry, country, service, seq_id)


@router.post("/sequences/{sequence_id}/enroll")
async def enroll_contacts(
    sequence_id: int,
    body: EnrollIn,
    db: AsyncSession = Depends(get_db),
):
    emails = await seq_service.enroll_contacts(db, sequence_id, body.contact_ids)
    await db.commit()
    return {"enrolled": len(emails), "sequence_id": sequence_id}


@router.get("/sequences/stats")
async def sequence_stats(db: AsyncSession = Depends(get_db)):
    return await seq_service.get_sequence_stats(db)


# ── Emails ────────────────────────────────────────────────────────────────

@router.post("/emails/{email_id}/send")
async def send_queued_email(email_id: int, db: AsyncSession = Depends(get_db)):
    success = await gmail_service.send_outreach_email(db, email_id)
    await db.commit()
    return {"sent": success, "email_id": email_id}


@router.post("/emails/send-direct")
async def send_direct_email(body: SendEmailIn):
    """Send a one-off email directly via SMTP (no DB record)."""
    success, error = gmail_service.send_email_smtp(
        body.to_email, body.subject, body.body, body.to_name
    )
    if not success:
        raise HTTPException(503, f"Email failed: {error}")
    return {"sent": True, "to": body.to_email}


@router.get("/emails/pending")
async def list_pending_emails(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.outreach import OutreachEmail
    rows = (await db.execute(
        select(OutreachEmail)
        .where(OutreachEmail.status == "scheduled")
        .limit(limit)
    )).scalars().all()
    return [{
        "id": e.id, "to_email": e.to_email, "subject": e.subject,
        "step_number": e.step_number, "scheduled_at": str(e.scheduled_at),
        "sequence_id": e.sequence_id,
    } for e in rows]


@router.post("/emails/process-due")
async def process_due_emails(
    limit: int = Query(10, le=50),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    """Find and send all emails that are due now."""
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.models.outreach import OutreachEmail
    now = datetime.now(timezone.utc)
    due = (await db.execute(
        select(OutreachEmail)
        .where(OutreachEmail.status == "scheduled")
        .where(OutreachEmail.scheduled_at <= now)
        .limit(limit)
    )).scalars().all()

    sent = 0
    for email in due:
        try:
            ok = await gmail_service.send_outreach_email(db, email.id)
            if ok:
                sent += 1
        except Exception:
            pass
    await db.commit()
    return {"processed": len(due), "sent": sent}
