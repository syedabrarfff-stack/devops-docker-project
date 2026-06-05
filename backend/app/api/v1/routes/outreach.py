from __future__ import annotations

from typing import Optional
from uuid import UUID

from datetime import UTC, datetime
from urllib.parse import unquote

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
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
    limit: int = 48
    autonomy_stage: str = "outreach_emails"


class RegeneratePendingIn(BaseModel):
    tenant_id: Optional[UUID] = None
    limit: int = 100


class PrepareCampaignIn(BaseModel):
    tenant_id: Optional[UUID] = None
    limit: int = 25
    min_score: float = 80


class SpeedToLeadTriggerIn(BaseModel):
    tenant_id: Optional[UUID] = None
    lookback_minutes: int = 5


class ResumeOutreachIn(BaseModel):
    tenant_id: Optional[UUID] = None
    reason: str = "Captain resumed outreach after review."


class QualificationApplyIn(BaseModel):
    tenant_id: Optional[UUID] = None
    limit: int = 500


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


@router.get("/engine-status")
async def outreach_engine_status(request: Request, tenant_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func, select
    from app.core.database import set_tenant_context
    from app.models.approval import ApprovalRequest, ApprovalStatus
    from app.models.lead import Lead
    from app.models.outreach import FollowUpQueue, FollowUpStatus, OutreachLog, OutreachStatus
    from app.services.intelligence.jarvis_authority import get_authority_level, requires_captain_approval
    from app.services.outreach.compliance import outreach_compliance

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    await set_tenant_context(db, str(resolved_tenant_id))
    gmail = await gmail_service.gmail_delivery_status(db, validate_smtp=True)
    cap = await outreach_compliance.daily_send_cap_status(db, resolved_tenant_id)

    total_leads = await db.scalar(
        select(func.count()).select_from(Lead).where(Lead.tenant_id == resolved_tenant_id)
    ) or 0
    leads_with_email = await db.scalar(
        select(func.count()).select_from(Lead).where(
            Lead.tenant_id == resolved_tenant_id,
            (Lead.email.is_not(None)) | (Lead.contact_email.is_not(None)),
        )
    ) or 0
    pending_followups = await db.scalar(
        select(func.count()).select_from(FollowUpQueue).where(
            FollowUpQueue.tenant_id == resolved_tenant_id,
            FollowUpQueue.status == FollowUpStatus.PENDING,
        )
    ) or 0
    sent_today = int(cap.get("sent_today") or 0)
    sent_total = await db.scalar(
        select(func.count()).select_from(OutreachLog).where(
            OutreachLog.tenant_id == resolved_tenant_id,
            OutreachLog.status == OutreachStatus.SENT,
        )
    ) or 0
    pending_approvals = await db.scalar(
        select(func.count()).select_from(ApprovalRequest).where(
            ApprovalRequest.tenant_id == resolved_tenant_id,
            ApprovalRequest.status == ApprovalStatus.PENDING,
        )
    ) or 0

    action_type = "outreach_emails"
    blockers: list[str] = []
    if gmail["send_mode"] != "live":
        blockers.append(gmail["validation_error"] or "Gmail is not live.")
    if await outreach_compliance.is_outreach_paused(db, resolved_tenant_id):
        blockers.append("Outreach is paused.")
    if not cap["allowed"]:
        blockers.append("Daily send cap reached.")
    if int(pending_followups) <= 0:
        blockers.append("No pending follow-up emails are queued.")
    if int(leads_with_email) <= 0:
        blockers.append("No leads with email addresses are available.")

    return {
        "status": "ready" if not blockers else "blocked",
        "tenant_id": str(resolved_tenant_id),
        "authority": {
            "action_type": action_type,
            "level": get_authority_level(action_type),
            "requires_captain_approval": requires_captain_approval(action_type),
        },
        "gmail": gmail,
        "daily_cap": cap,
        "queue": {
            "pending_followups": int(pending_followups),
            "sent_today": sent_today,
            "remaining_today": max(0, int(cap.get("cap") or 0) - sent_today),
            "sent_total": int(sent_total),
            "pending_approvals": int(pending_approvals),
        },
        "leads": {
            "total": int(total_leads),
            "with_email": int(leads_with_email),
        },
        "blockers": blockers,
        "next_action": (
            "Connect Gmail OAuth or clear Google WebLoginRequired, then run POST /api/v1/outreach/execute."
            if gmail["send_mode"] != "live"
            else "Run POST /api/v1/outreach/execute to send due outreach under the 48/day cap."
        ),
    }


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


@router.post("/prepare-campaign")
async def prepare_campaign(
    request: Request,
    body: PrepareCampaignIn = Body(default_factory=PrepareCampaignIn),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.core.database import set_tenant_context
    from app.models.lead import Lead, LeadStatus
    from app.models.outreach import FollowUpQueue, FollowUpStatus

    resolved_tenant_id = _resolve_tenant_id(request, body.tenant_id)
    await set_tenant_context(db, str(resolved_tenant_id))
    limit = max(1, min(int(body.limit or 25), 100))
    rows = (
        await db.execute(
            select(Lead)
            .where(
                Lead.tenant_id == resolved_tenant_id,
                Lead.outreach_eligible.is_(True),
                Lead.status.in_([LeadStatus.NEW, LeadStatus.NURTURE]),
                ((Lead.email.is_not(None)) | (Lead.contact_email.is_not(None))),
                Lead.score >= float(body.min_score or 80),
            )
            .order_by(Lead.score.desc(), Lead.created_at.asc())
            .limit(limit)
        )
    ).scalars().all()

    queued = 0
    skipped: list[dict] = []
    for lead in rows:
        existing = await db.scalar(
            select(FollowUpQueue.id)
            .where(
                FollowUpQueue.tenant_id == resolved_tenant_id,
                FollowUpQueue.lead_id == lead.id,
                FollowUpQueue.status == FollowUpStatus.PENDING,
            )
            .limit(1)
        )
        if existing:
            skipped.append({"lead_id": str(lead.id), "company": lead.company_name or lead.company, "reason": "already_pending"})
            continue
        try:
            await outreach_engine.queue_sequence(lead.id, resolved_tenant_id)
            queued_now = await db.scalar(
                select(FollowUpQueue.id)
                .where(
                    FollowUpQueue.tenant_id == resolved_tenant_id,
                    FollowUpQueue.lead_id == lead.id,
                    FollowUpQueue.status == FollowUpStatus.PENDING,
                )
                .limit(1)
            )
            if queued_now:
                queued += 1
            else:
                skipped.append({
                    "lead_id": str(lead.id),
                    "company": lead.company_name or lead.company,
                    "reason": "not_qualified_or_not_queued",
                })
        except Exception as exc:
            skipped.append({"lead_id": str(lead.id), "company": lead.company_name or lead.company, "reason": str(exc)[:180]})

    await db.commit()
    return {
        "tenant_id": str(resolved_tenant_id),
        "candidates_seen": len(rows),
        "queued_leads": queued,
        "skipped": skipped,
        "next_action": "Connect Gmail OAuth, then run /api/v1/outreach/execute when engine-status is ready. Leads below 80 stay behind Captain review.",
    }


@router.post("/speed-to-lead/trigger")
async def trigger_speed_to_lead(
    request: Request,
    body: SpeedToLeadTriggerIn = Body(default_factory=SpeedToLeadTriggerIn),
):
    from app.services.revenue_activation.speed_to_lead import speed_to_lead_engine

    resolved_tenant_id = _resolve_tenant_id(request, body.tenant_id)
    return await speed_to_lead_engine.trigger(
        resolved_tenant_id,
        lookback_minutes=body.lookback_minutes,
    )


@router.get("/track/open/{outreach_id}.gif")
async def track_email_open(outreach_id: UUID, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.outreach import EmailTracking, OutreachLog, OutreachStatus

    now = datetime.now(UTC)
    outreach = await db.scalar(select(OutreachLog).where(OutreachLog.id == outreach_id))
    if outreach:
        tracking = await db.scalar(select(EmailTracking).where(EmailTracking.outreach_id == outreach.id))
        if not tracking:
            tracking = EmailTracking(tenant_id=outreach.tenant_id, outreach_id=outreach.id)
            db.add(tracking)
        tracking.opened_at = tracking.opened_at or now
        if outreach.status not in (OutreachStatus.REPLIED, OutreachStatus.CLICKED):
            outreach.status = OutreachStatus.OPENED
    return Response(content=_TRANSPARENT_GIF, media_type="image/gif")


@router.get("/track/click/{outreach_id}")
async def track_email_click(outreach_id: UUID, url: str = Query(...), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.outreach import EmailTracking, OutreachLog, OutreachStatus

    destination = unquote(url or "").strip()
    if not destination.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid redirect URL")
    now = datetime.now(UTC)
    outreach = await db.scalar(select(OutreachLog).where(OutreachLog.id == outreach_id))
    if outreach:
        tracking = await db.scalar(select(EmailTracking).where(EmailTracking.outreach_id == outreach.id))
        if not tracking:
            tracking = EmailTracking(tenant_id=outreach.tenant_id, outreach_id=outreach.id)
            db.add(tracking)
        tracking.clicked_at = tracking.clicked_at or now
        if outreach.status != OutreachStatus.REPLIED:
            outreach.status = OutreachStatus.CLICKED
    return RedirectResponse(destination, status_code=302)


@router.get("/unsubscribe")
async def unsubscribe_from_outreach(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    from app.core.database import set_tenant_context
    from app.services.outreach.compliance import outreach_compliance

    resolved_tenant_id = _resolve_tenant_id(request, None)
    try:
        email = outreach_compliance.email_from_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid unsubscribe token") from exc
    await set_tenant_context(db, str(resolved_tenant_id))
    await outreach_compliance.add_do_not_contact(
        db,
        resolved_tenant_id,
        email,
        reason="unsubscribe_link",
        source="one_click_unsubscribe",
        notes="Recipient used the one-click unsubscribe link.",
    )
    return {
        "unsubscribed": True,
        "message": "This email address has been removed from Aliyar Solutions outreach.",
    }


@router.post("/resume")
async def resume_outreach(request: Request, body: ResumeOutreachIn = Body(default_factory=ResumeOutreachIn), db: AsyncSession = Depends(get_db)):
    from app.core.database import set_tenant_context
    from app.services.outreach.compliance import outreach_compliance

    resolved_tenant_id = _resolve_tenant_id(request, body.tenant_id)
    await set_tenant_context(db, str(resolved_tenant_id))
    return await outreach_compliance.resume_outreach(db, resolved_tenant_id, reason=body.reason)


@router.get("/compliance/status")
async def outreach_compliance_status(request: Request, tenant_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func, select
    from app.core.database import set_tenant_context
    from app.models.compliance import DoNotContact
    from app.services.outreach.compliance import outreach_compliance

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    await set_tenant_context(db, str(resolved_tenant_id))
    dnc_count = await db.scalar(
        select(func.count()).select_from(DoNotContact).where(DoNotContact.tenant_id == resolved_tenant_id)
    ) or 0
    cap = await outreach_compliance.daily_send_cap_status(db, resolved_tenant_id)
    return {
        "tenant_id": str(resolved_tenant_id),
        "do_not_contact_count": int(dnc_count),
        "outreach_paused": await outreach_compliance.is_outreach_paused(db, resolved_tenant_id),
        "daily_send_cap": cap,
        "current_daily_cap": outreach_compliance.current_daily_cap(),
    }


@router.post("/compliance/review")
async def run_outreach_safety_review(request: Request, tenant_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db)):
    from app.core.database import set_tenant_context
    from app.services.outreach.compliance import outreach_compliance

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    await set_tenant_context(db, str(resolved_tenant_id))
    result = await outreach_compliance.assess_reply_rate_pause(db, resolved_tenant_id)
    return {"tenant_id": str(resolved_tenant_id), **result}


@router.post("/qualification/apply")
async def apply_qualification_thresholds(
    request: Request,
    body: QualificationApplyIn = Body(default_factory=QualificationApplyIn),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.core.database import set_tenant_context
    from app.models.lead import Lead
    from app.services.outreach.compliance import outreach_compliance

    resolved_tenant_id = _resolve_tenant_id(request, body.tenant_id)
    await set_tenant_context(db, str(resolved_tenant_id))
    leads = (
        await db.execute(
            select(Lead)
            .where(Lead.tenant_id == resolved_tenant_id)
            .order_by(Lead.created_at.desc())
            .limit(max(1, min(body.limit, 2000)))
        )
    ).scalars().all()
    counts = {"needs_enrichment": 0, "review_required": 0, "auto_approved": 0, "captain_approved": 0}
    for lead in leads:
        result = await outreach_compliance.qualification_status(db, resolved_tenant_id, lead)
        lead.qualification_status = result["status"]
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    return {"tenant_id": str(resolved_tenant_id), "processed": len(leads), "counts": counts}


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


@router.get("/logs")
async def list_outreach_logs(
    request: Request,
    tenant_id: Optional[UUID] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import desc, select

    from app.core.database import set_tenant_context
    from app.models.lead import Lead
    from app.models.outreach import OutreachLog

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    await set_tenant_context(db, str(resolved_tenant_id))
    rows = (
        await db.execute(
            select(OutreachLog, Lead)
            .outerjoin(Lead, Lead.id == OutreachLog.lead_id)
            .where(OutreachLog.tenant_id == resolved_tenant_id)
            .order_by(desc(OutreachLog.created_at))
            .limit(limit)
        )
    ).all()
    logs = []
    for log, lead in rows:
        channel = log.channel.value if hasattr(log.channel, "value") else log.channel
        status = log.status.value if hasattr(log.status, "value") else log.status
        company = None
        if lead:
            company = lead.company_name or lead.company
            if not company and lead.email and "@" in lead.email:
                company = lead.email.split("@", 1)[1]
        logs.append({
            "id": str(log.id),
            "lead_id": str(log.lead_id) if log.lead_id else None,
            "company": company,
            "contact_name": lead.contact_name if lead else None,
            "to_email": lead.email if lead else None,
            "channel": channel,
            "subject": log.subject,
            "body_text": log.body_text,
            "persona": log.sent_from_persona,
            "status": status,
            "sequence_step": log.sequence_step,
            "skip_reason": log.skip_reason,
            "sent_at": log.sent_at.isoformat() if log.sent_at else None,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    return {"tenant_id": str(resolved_tenant_id), "count": len(logs), "logs": logs}


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
async def send_direct_email(body: SendEmailIn, request: Request, db: AsyncSession = Depends(get_db)):
    from app.core.database import set_tenant_context
    from app.services.outreach.compliance import outreach_compliance

    resolved_tenant_id = _resolve_tenant_id(request, None)
    await set_tenant_context(db, str(resolved_tenant_id))
    if await outreach_compliance.is_outreach_paused(db, resolved_tenant_id):
        raise HTTPException(status_code=409, detail="Outreach is paused. Resume outreach before sending direct mail.")
    if await outreach_compliance.is_do_not_contact(db, resolved_tenant_id, body.to_email):
        raise HTTPException(status_code=409, detail="Recipient is on the do-not-contact list.")
    cap = await outreach_compliance.daily_send_cap_status(db, resolved_tenant_id)
    if not cap["allowed"]:
        raise HTTPException(status_code=409, detail={"reason": "daily_send_cap_reached", **cap})
    body_with_footer = outreach_compliance.append_footer(body.body, body.to_email)
    success, error, method = await gmail_service.send_client_email(
        db,
        body.to_email,
        body.subject,
        body_with_footer,
        body.to_name,
    )
    if not success:
        raise HTTPException(503, f"Email failed: {error}")
    return {"sent": True, "to": body.to_email, "method": method}


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


_TRANSPARENT_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
    b"\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"
    b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)
