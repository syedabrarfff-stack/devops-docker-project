"""
JARVIS Emergency Control System — detects failures, isolates affected systems,
notifies Captain immediately, and generates incident reports.
"""
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.governance import IncidentReport

logger = logging.getLogger(__name__)

SEVERITY_LABELS = {"low": "🟡", "medium": "🟠", "high": "🔴", "critical": "🚨"}


async def declare_emergency(
    db: AsyncSession,
    title: str,
    severity: str,
    category: str,
    description: str,
    affected_systems: list[str],
    auto_detected: bool = False,
) -> dict:
    """Create an incident report and immediately notify Captain."""
    incident = IncidentReport(
        title=title,
        severity=severity,
        category=category,
        description=description,
        affected_systems=affected_systems,
        actions_taken=[],
        status="open",
        auto_detected=auto_detected,
        notified_captain=False,
    )
    db.add(incident)
    await db.flush()

    # Notify Captain through all available channels
    await _notify_captain(incident)
    incident.notified_captain = True

    return _serialize(incident)


async def _notify_captain(incident: IncidentReport) -> None:
    label = SEVERITY_LABELS.get(incident.severity, "⚠️")
    title = f"{label} JARVIS INCIDENT [{incident.severity.upper()}]: {incident.title}"
    body = (
        f"Category: {incident.category}\n"
        f"Affected: {', '.join(incident.affected_systems or [])}\n"
        f"Status: {incident.status}\n\n"
        f"{incident.description}"
    )
    try:
        from app.core.config import settings
        from app.services.notifications.slack import notify_system_event
        await notify_system_event(title, body, level=incident.severity)
    except Exception as e:
        logger.warning(f"Slack incident notify failed: {e}")

    try:
        from app.core.config import settings
        from app.services.notifications.telegram import send_telegram_message
        if settings.TELEGRAM_CHAT_ID and settings.TELEGRAM_BOT_TOKEN:
            msg = f"{title}\n\n{body}"
            await send_telegram_message(str(settings.TELEGRAM_CHAT_ID), msg)
    except Exception as e:
        logger.warning(f"Telegram incident notify failed: {e}")

    try:
        from app.api.v1.routes.ws import broadcast_notification
        await broadcast_notification(
            title=title,
            body=body,
            level=incident.severity,
            category="system",
            reference=str(incident.id),
        )
    except Exception as e:
        logger.warning(f"WS incident notify failed: {e}")


async def resolve_incident(db: AsyncSession, incident_id: int, actions_taken: list[str]) -> bool:
    result = await db.execute(select(IncidentReport).where(IncidentReport.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        return False
    incident.status = "resolved"
    incident.actions_taken = actions_taken
    incident.resolved_at = datetime.now(timezone.utc)
    return True


async def add_action(db: AsyncSession, incident_id: int, action: str) -> bool:
    result = await db.execute(select(IncidentReport).where(IncidentReport.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        return False
    actions = list(incident.actions_taken or [])
    actions.append(f"[{datetime.now(timezone.utc).strftime('%H:%M UTC')}] {action}")
    incident.actions_taken = actions
    return True


async def get_incidents(db: AsyncSession, status: str | None = None, limit: int = 50,
                        tenant_id=None) -> list[dict]:
    from app.core.config import settings as _cfg
    import uuid as _uuid
    _tid = tenant_id
    if _tid is None and _cfg.JARVIS_DEFAULT_TENANT_ID:
        try:
            _tid = _uuid.UUID(str(_cfg.JARVIS_DEFAULT_TENANT_ID))
        except (ValueError, AttributeError):
            pass
    q = select(IncidentReport).order_by(IncidentReport.created_at.desc()).limit(limit)
    if _tid is not None:
        q = q.where(IncidentReport.tenant_id == _tid)
    if status:
        q = q.where(IncidentReport.status == status)
    result = await db.execute(q)
    return [_serialize(i) for i in result.scalars().all()]


async def check_system_health() -> dict:
    """Quick health probe — returns status of each major subsystem."""
    checks = {}

    # AI router
    try:
        from app.services.ai.router import ai_router
        providers = ai_router.available_providers()
        checks["ai_router"] = {"status": "ok" if providers else "degraded", "providers": len(providers)}
    except Exception as e:
        checks["ai_router"] = {"status": "error", "error": str(e)}

    # Scheduler
    try:
        from app.services.scheduler.scheduler import get_scheduler
        sched = get_scheduler()
        checks["scheduler"] = {"status": "ok" if sched.running else "stopped", "jobs": len(sched.get_jobs())}
    except Exception as e:
        checks["scheduler"] = {"status": "error", "error": str(e)}

    # Database (lightweight)
    try:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            await db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "error": str(e)}

    overall = "ok"
    if any(v.get("status") == "error" for v in checks.values()):
        overall = "degraded"
    if sum(1 for v in checks.values() if v.get("status") == "error") >= 2:
        overall = "critical"

    return {"overall": overall, "subsystems": checks, "checked_at": datetime.now(timezone.utc).isoformat()}


def _serialize(i: IncidentReport) -> dict:
    return {
        "id": i.id,
        "title": i.title,
        "severity": i.severity,
        "category": i.category,
        "description": i.description,
        "affected_systems": i.affected_systems or [],
        "actions_taken": i.actions_taken or [],
        "status": i.status,
        "auto_detected": i.auto_detected,
        "notified_captain": i.notified_captain,
        "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }
