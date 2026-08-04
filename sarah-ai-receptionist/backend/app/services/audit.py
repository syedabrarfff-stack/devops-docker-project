"""
HIPAA audit trail — records every access to patient PHI.

Call write_audit_log() from any route that reads or writes patient-identifying
data (call transcripts, appointments, patient records, clinic settings). This
is the only thing that makes AuditLog more than a table nobody writes to.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


async def write_audit_log(
    db: AsyncSession,
    *,
    clinic_id: str,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    user_id: str | None = None,
    ip_address: str | None = None,
    details: dict | None = None,
) -> None:
    """Best-effort: a failed audit write must never block the underlying request."""
    try:
        db.add(
            AuditLog(
                clinic_id=clinic_id,
                user_id=user_id,
                actor=actor,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                details=details or {},
            )
        )
        await db.flush()
    except Exception as e:
        logger.error(f"Failed to write audit log ({action} {resource_type}/{resource_id}): {e}")
