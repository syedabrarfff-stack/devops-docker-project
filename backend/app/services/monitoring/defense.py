from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import ApprovalRequest
from app.models.governance import IncidentReport
from app.models.notifications import NotificationLog
from app.models.outreach import OutreachEmail
from app.services.contacts.sync import validate_apollo_access
from app.services.operations.capabilities import credential_status
from app.services.storage.secure import get_credential


async def run_defense_scan(db: AsyncSession, create_notification: bool = False) -> dict[str, Any]:
    """
    Read-only defensive production scan.

    This layer can detect and report reliability/security risks automatically.
    It does not delete data, alter infrastructure, rotate secrets, or send client
    messages. Those actions stay behind Captain approval.
    """
    now = datetime.now(timezone.utc)
    findings: list[dict[str, Any]] = []

    await _check_system_health(findings)
    await _check_ai_router(findings)
    await _check_credentials(db, findings)
    await _check_revenue_integrations(db, findings)
    await _check_approval_queue(db, findings, now)
    await _check_open_incidents(db, findings)

    severity_order = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    max_severity = max((severity_order.get(item["severity"], 0) for item in findings), default=0)
    threat_level = next(k for k, v in severity_order.items() if v == max_severity)
    if max_severity == 0:
        threat_level = "secure"

    summary = _summary(threat_level, findings)
    if create_notification and findings:
        db.add(NotificationLog(
            channel="dashboard",
            title="JARVIS defensive production scan",
            body=summary,
            level="warning" if max_severity >= 2 else "info",
            category="security",
            reference="defense_scan",
            delivered=True,
            metadata_={"threat_level": threat_level, "findings": findings[:20]},
        ))
        await db.flush()

    return {
        "checked_at": now.isoformat(),
        "threat_level": threat_level,
        "summary": summary,
        "findings": findings,
        "authority": {
            "automatic": [
                "reporting",
                "health checks",
                "non-destructive diagnostics",
                "approval queue risk detection",
            ],
            "requires_captain_approval": [
                "client-facing sends",
                "payments",
                "credential rotation",
                "infrastructure deletion",
                "database destructive changes",
            ],
        },
    }


async def _check_system_health(findings: list[dict[str, Any]]) -> None:
    try:
        from app.services.monitoring.emergency import check_system_health

        health = await check_system_health()
        if health.get("overall") not in ("ok", "secure"):
            findings.append(_finding(
                "system_health",
                "high" if health.get("overall") == "critical" else "medium",
                "System health is degraded.",
                health,
                "Inspect failing subsystem and keep production traffic on known healthy services.",
            ))
    except Exception as exc:
        findings.append(_finding(
            "system_health",
            "high",
            "System health scan failed.",
            {"error": str(exc)},
            "Check backend logs and health endpoints.",
        ))


async def _check_ai_router(findings: list[dict[str, Any]]) -> None:
    try:
        from app.services.ai.router import ai_router

        providers = ai_router.get_provider_status()
        available = [name for name, status in providers.items() if status.get("available")]
        if not available:
            findings.append(_finding(
                "ai_router",
                "high",
                "No AI providers are currently available.",
                {"providers": providers},
                "Enable at least one provider before relying on autonomous analysis.",
            ))
        elif "bedrock" in providers and not providers["bedrock"].get("available"):
            findings.append(_finding(
                "aws_bedrock",
                "low",
                "AWS Bedrock provider is installed but not enabled.",
                {"available_providers": available},
                "Set AWS_BEDROCK_ENABLED=true and confirm Bedrock model access when ready.",
            ))
    except Exception as exc:
        findings.append(_finding("ai_router", "medium", "AI router status failed.", {"error": str(exc)}, "Review provider imports and configuration."))


async def _check_credentials(db: AsyncSession, findings: list[dict[str, Any]]) -> None:
    creds = await credential_status(db)
    by_key = {row["key"]: row for row in creds}

    if by_key.get("ANTHROPIC_API_KEY", {}).get("configured"):
        findings.append(_finding(
            "anthropic_policy",
            "medium",
            "Anthropic/Claude key is configured even though Captain requested it disabled for now.",
            {},
            "Remove or disable ANTHROPIC_API_KEY until Captain explicitly re-enables it.",
        ))

    gmail_password = await get_credential(db, "GMAIL_APP_PASSWORD")
    clean_password = (gmail_password or "").replace(" ", "").strip()
    gmail_sender_ready = (
        by_key.get("GMAIL_ADDRESS", {}).get("configured")
        or by_key.get("GMAIL_USER", {}).get("configured")
        or by_key.get("EMAIL_USER", {}).get("configured")
    )
    if gmail_sender_ready and not (clean_password.isascii() and len(clean_password) == 16):
        findings.append(_finding(
            "gmail_smtp",
            "medium",
            "Gmail sender exists, but the app password is not a valid 16-character ASCII app password.",
            {"password_shape": "invalid"},
            "Replace GMAIL_APP_PASSWORD with a Google app password before approving outreach sends.",
        ))

    if by_key.get("AWS_ACCESS_KEY_ID", {}).get("configured") and not by_key.get("AWS_SECRET_ACCESS_KEY", {}).get("configured"):
        findings.append(_finding(
            "aws_credentials",
            "medium",
            "AWS access key is present without the matching secret.",
            {},
            "Store the matching AWS_SECRET_ACCESS_KEY or use an EC2 IAM role.",
        ))


async def _check_revenue_integrations(db: AsyncSession, findings: list[dict[str, Any]]) -> None:
    apollo_ok, apollo_message = await validate_apollo_access(db)
    if not apollo_ok:
        findings.append(_finding(
            "apollo_access",
            "medium",
            "Apollo live lead discovery is blocked.",
            {"message": apollo_message},
            "Upgrade/enable Apollo API search access or switch discovery to Google Places/n8n until Apollo is ready.",
        ))


async def _check_approval_queue(db: AsyncSession, findings: list[dict[str, Any]], now: datetime) -> None:
    pending = (await db.execute(
        select(func.count(ApprovalRequest.id)).where(ApprovalRequest.status == "pending")
    )).scalar_one() or 0
    stale = (await db.execute(
        select(func.count(ApprovalRequest.id))
        .where(ApprovalRequest.status == "pending")
        .where(ApprovalRequest.created_at < now - timedelta(hours=24))
    )).scalar_one() or 0
    draft_emails = (await db.execute(
        select(func.count(OutreachEmail.id)).where(OutreachEmail.status == "draft")
    )).scalar_one() or 0

    if pending > 10 or stale:
        findings.append(_finding(
            "approval_queue",
            "medium",
            "Approval queue needs attention.",
            {"pending": int(pending), "stale_24h": int(stale), "draft_emails": int(draft_emails)},
            "Review stale approvals so safe revenue actions do not pile up.",
        ))


async def _check_open_incidents(db: AsyncSession, findings: list[dict[str, Any]]) -> None:
    incidents = (await db.execute(
        select(IncidentReport)
        .where(IncidentReport.status.in_(["open", "investigating", "escalated"]))
        .order_by(desc(IncidentReport.created_at))
        .limit(5)
    )).scalars().all()
    critical = [item for item in incidents if item.severity == "critical"]
    if critical:
        findings.append(_finding(
            "open_incidents",
            "critical",
            "Critical incidents are still open.",
            {"incident_ids": [item.id for item in critical]},
            "Resolve or escalate critical incidents before making risky production changes.",
        ))


def _finding(category: str, severity: str, message: str, evidence: dict[str, Any], recommendation: str) -> dict[str, Any]:
    return {
        "category": category,
        "severity": severity,
        "message": message,
        "evidence": evidence,
        "recommendation": recommendation,
    }


def _summary(threat_level: str, findings: list[dict[str, Any]]) -> str:
    if not findings:
        return "System secure. No production blockers detected by the defensive scan."
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding["severity"]] = counts.get(finding["severity"], 0) + 1
    parts = ", ".join(f"{count} {severity}" for severity, count in sorted(counts.items()))
    return f"Defensive scan completed. Threat level: {threat_level}. Findings: {parts}."
