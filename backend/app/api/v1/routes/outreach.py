from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.outreach import gmail as gmail_service
from app.services.outreach import sequences as seq_service
from app.services.outreach.engine import outreach_engine

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


class ExecuteOutreachIn(BaseModel):
    tenant_id: Optional[UUID] = None
    limit: int = 25
    autonomy_stage: str = "outreach_emails"


class RegeneratePendingIn(BaseModel):
    tenant_id: Optional[UUID] = None
    limit: int = 100


class LinkedInSendIn(BaseModel):
    lead_id: UUID
    message_type: int = 1
    tenant_id: Optional[UUID] = None


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
            _generate_ai_steps,
            seq.id,
            body.target_industry,
            body.target_country,
            body.service_offered,
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


@router.post("/queue/{lead_id}")
async def queue_lead_outreach(lead_id: UUID, request: Request, tenant_id: Optional[UUID] = None):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    await outreach_engine.queue_sequence(lead_id, resolved_tenant_id)
    return {"queued": True, "lead_id": str(lead_id), "tenant_id": str(resolved_tenant_id)}


@router.post("/execute")
async def execute_outreach(request: Request, body: ExecuteOutreachIn = Body(default_factory=ExecuteOutreachIn)):
    resolved_tenant_id = _resolve_tenant_id(request, body.tenant_id)
    sent = await outreach_engine.execute_due_outreach(
        resolved_tenant_id,
        limit=body.limit,
        autonomy_stage=body.autonomy_stage,
    )
    return {"sent": sent, "tenant_id": str(resolved_tenant_id)}


@router.post("/regenerate-pending")
async def regenerate_pending_outreach(
    request: Request,
    body: RegeneratePendingIn = Body(default_factory=RegeneratePendingIn),
):
    resolved_tenant_id = _resolve_tenant_id(request, body.tenant_id)
    result = await outreach_engine.regenerate_pending_sequences(
        resolved_tenant_id,
        limit=body.limit,
    )
    return {**result, "tenant_id": str(resolved_tenant_id)}


@router.post("/linkedin/send")
async def prepare_linkedin_outreach(request: Request, body: LinkedInSendIn):
    from app.services.outreach.linkedin import linkedin_outreach_service

    resolved_tenant_id = _resolve_tenant_id(request, body.tenant_id)
    try:
        return await linkedin_outreach_service.prepare_message(
            resolved_tenant_id,
            body.lead_id,
            body.message_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/stats")
async def outreach_stats(request: Request, tenant_id: Optional[UUID] = None):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await outreach_engine.stats(resolved_tenant_id)


@router.post("/emails/{email_id}/send")
async def send_queued_email(email_id: int, db: AsyncSession = Depends(get_db)):
    success = await gmail_service.send_outreach_email(db, email_id)
    await db.commit()
    return {"sent": success, "email_id": email_id}


@router.post("/emails/send-direct")
async def send_direct_email(body: SendEmailIn):
    success, error = gmail_service.send_email_smtp(
        body.to_email,
        body.subject,
        body.body,
        body.to_name,
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

    rows = (
        await db.execute(
            select(OutreachEmail)
            .where(OutreachEmail.status == "scheduled")
            .limit(limit)
        )
    ).scalars().all()
    return [
        {
            "id": email.id,
            "to_email": email.to_email,
            "subject": email.subject,
            "step_number": email.step_number,
            "scheduled_at": str(email.scheduled_at),
            "sequence_id": email.sequence_id,
        }
        for email in rows
    ]


@router.post("/emails/process-due")
async def process_due_emails(
    limit: int = Query(10, le=50),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.models.outreach import OutreachEmail

    now = datetime.now(timezone.utc)
    due = (
        await db.execute(
            select(OutreachEmail)
            .where(OutreachEmail.status == "scheduled")
            .where(OutreachEmail.scheduled_at <= now)
            .limit(limit)
        )
    ).scalars().all()

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


def _resolve_tenant_id(request: Request, explicit_tenant_id: Optional[UUID]) -> UUID:
    from app.core.config import settings

    tenant_id = (
        explicit_tenant_id
        or getattr(request.state, "tenant_id", None)
        or request.headers.get("X-Tenant-ID")
        or settings.JARVIS_DEFAULT_TENANT_ID
    )
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    try:
        return UUID(str(tenant_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="tenant_id must be a valid UUID") from exc
