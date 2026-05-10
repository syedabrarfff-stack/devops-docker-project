from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.core.database import get_db
from app.models.approval import ApprovalRequest, AuditLog
from app.schemas.approval import ApprovalCreate, ApprovalDecision, ApprovalOut
from app.services.notifications.slack import notify_slack
from app.services.notifications.telegram import notify_telegram

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalOut])
async def list_approvals(status: str = "pending", db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ApprovalRequest)
        .where(ApprovalRequest.status == status)
        .order_by(ApprovalRequest.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.post("", response_model=ApprovalOut)
async def create_approval(data: ApprovalCreate, db: AsyncSession = Depends(get_db)):
    approval = ApprovalRequest(**data.model_dump())
    db.add(approval)
    await db.flush()
    await db.refresh(approval)

    # Notify Captain immediately
    msg = (
        f"🟡 *JARVIS APPROVAL REQUIRED*\n\n"
        f"*Action:* {data.title}\n"
        f"*Risk:* {data.risk_level.upper()}\n"
        f"*Summary:* {data.summary[:200]}\n\n"
        f"Open JARVIS dashboard to approve or reject."
    )
    await notify_slack(msg)
    await notify_telegram(msg)

    return approval


@router.post("/{approval_id}/decide")
async def decide_approval(
    approval_id: int,
    decision: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    approval.status = decision.status
    approval.captain_note = decision.captain_note
    approval.approved_at = datetime.utcnow()

    db.add(AuditLog(
        action=f"Approval {decision.status}: {approval.title}",
        details={"approval_id": approval_id, "decision": decision.status, "note": decision.captain_note},
    ))
    await db.flush()

    status_emoji = "✅" if decision.status == "approved" else "❌"
    msg = f"{status_emoji} *Captain {decision.status.upper()}*: {approval.title}"
    await notify_slack(msg)
    await notify_telegram(msg)

    return {"status": decision.status, "approval_id": approval_id}


@router.get("/count")
async def approval_count(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ApprovalRequest).where(ApprovalRequest.status == "pending")
    )
    return {"pending": len(result.scalars().all())}
