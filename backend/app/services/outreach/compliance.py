from __future__ import annotations

import base64
import hashlib
import hmac
import uuid
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.core.config import settings
from app.models.approval import ApprovalRequest, ApprovalStatus, AuditLog
from app.models.compliance import DoNotContact, OutreachPauseState
from app.models.lead import Lead
from app.models.outreach import OutreachLog, OutreachStatus, ReplyLog

COUNTRY_TIMEZONES = {
    "usa": "America/New_York",
    "united states": "America/New_York",
    "uk": "Europe/London",
    "united kingdom": "Europe/London",
    "england": "Europe/London",
    "uae": "Asia/Dubai",
    "united arab emirates": "Asia/Dubai",
    "bahrain": "Asia/Bahrain",
    "canada": "America/Toronto",
    "australia": "Australia/Sydney",
    "india": "Asia/Kolkata",
    "europe": "Europe/Paris",
}

OPT_OUT_TERMS = (
    "unsubscribe",
    "remove me",
    "do not contact",
    "don't contact",
    "please don't email",
    "please do not email",
    "stop emailing",
    "stop email",
    "stop contacting",
    "not interested",
    "no thanks",
)


class OutreachComplianceService:
    def unsubscribe_token(self, email: str) -> str:
        normalized = normalize_email(email)
        payload = base64.urlsafe_b64encode(normalized.encode("utf-8")).decode("ascii").rstrip("=")
        signature = hmac.new(_secret(), payload.encode("ascii"), hashlib.sha256).hexdigest()[:24]
        return f"{payload}.{signature}"

    def email_from_token(self, token: str) -> str:
        try:
            payload, signature = token.split(".", 1)
            expected = hmac.new(_secret(), payload.encode("ascii"), hashlib.sha256).hexdigest()[:24]
            if not hmac.compare_digest(signature, expected):
                raise ValueError("Invalid unsubscribe token")
            padded = payload + ("=" * (-len(payload) % 4))
            return normalize_email(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        except Exception as exc:
            raise ValueError("Invalid unsubscribe token") from exc

    async def add_do_not_contact(
        self,
        session,
        tenant_id: uuid.UUID,
        email: str,
        *,
        reason: str = "unsubscribe",
        source: str = "outreach",
        notes: str | None = None,
    ) -> DoNotContact:
        normalized = normalize_email(email)
        if not normalized:
            raise ValueError("email is required for do-not-contact records")
        existing = await session.scalar(
            select(DoNotContact).where(
                DoNotContact.tenant_id == tenant_id,
                DoNotContact.email == normalized,
            )
        )
        token = self.unsubscribe_token(normalized)
        if existing:
            existing.reason = reason or existing.reason
            existing.source = source or existing.source
            existing.notes = notes or existing.notes
            existing.token = token
            existing.confirmed_at = existing.confirmed_at or datetime.now(UTC)
            record = existing
        else:
            record = DoNotContact(
                tenant_id=tenant_id,
                email=normalized,
                reason=reason,
                source=source,
                notes=notes,
                token=token,
                confirmed_at=datetime.now(UTC),
            )
            session.add(record)
            await session.flush()
        session.add(
            AuditLog(
                tenant_id=tenant_id,
                action="do_not_contact_added",
                entity_type="do_not_contact",
                entity_id=record.id,
                actor="OutreachComplianceService",
                details={"email": normalized, "reason": reason, "source": source},
                after_json={"email": normalized, "reason": reason, "source": source},
            )
        )
        return record

    async def is_do_not_contact(self, session, tenant_id: uuid.UUID, email: str | None) -> bool:
        normalized = normalize_email(email)
        if not normalized:
            return False
        existing = await session.scalar(
            select(DoNotContact.id).where(
                DoNotContact.tenant_id == tenant_id,
                DoNotContact.email == normalized,
            )
        )
        return bool(existing)

    async def safety_gate(
        self,
        session,
        tenant_id: uuid.UUID,
        lead: Lead,
        recipient_email: str | None,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or datetime.now(UTC)
        recipient_email = normalize_email(recipient_email)
        if not recipient_email:
            return {"allowed": False, "reason": "missing_email"}
        if await self.is_outreach_paused(session, tenant_id):
            return {"allowed": False, "reason": "outreach_paused"}
        if await self.is_do_not_contact(session, tenant_id, recipient_email):
            return {"allowed": False, "reason": "do_not_contact"}

        qualification = await self.qualification_status(session, tenant_id, lead)
        lead.qualification_status = qualification["status"]
        if not qualification["allowed"]:
            return qualification

        window = self.send_window(lead, now)
        if not window["allowed"]:
            return window

        cap = await self.daily_send_cap_status(session, tenant_id, now)
        if not cap["allowed"]:
            return cap

        return {
            "allowed": True,
            "reason": "allowed",
            "timezone": lead.timezone or infer_timezone(lead.country),
            "daily_cap": cap,
        }

    async def qualification_status(self, session, tenant_id: uuid.UUID, lead: Lead) -> dict[str, Any]:
        score = float(lead.score or 0.0)
        approved = await self._has_approved_outreach_review(session, tenant_id, lead.id)
        if score < 65:
            return {
                "allowed": False,
                "reason": "needs_enrichment",
                "status": "needs_enrichment",
                "score": score,
            }
        if score < 80 and not approved:
            await self._queue_qualification_review(session, tenant_id, lead)
            return {
                "allowed": False,
                "reason": "qualification_review_required",
                "status": "review_required",
                "score": score,
            }
        return {
            "allowed": True,
            "reason": "qualified",
            "status": "auto_approved" if score >= 80 else "captain_approved",
            "score": score,
        }

    def send_window(self, lead: Lead, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now(UTC)
        timezone_name = lead.timezone or infer_timezone(lead.country)
        lead.timezone = timezone_name
        try:
            zone = ZoneInfo(timezone_name)
        except Exception:
            zone = ZoneInfo("UTC")
            timezone_name = "UTC"
        local_now = now.astimezone(zone)
        start = time(8, 30)
        end = time(17, 30)
        weekday = local_now.weekday() < 5
        if weekday and start <= local_now.time() <= end:
            return {"allowed": True, "reason": "inside_send_window", "timezone": timezone_name}

        next_local = local_now
        while True:
            if next_local.weekday() < 5 and next_local.time() < start:
                candidate = datetime.combine(next_local.date(), start, tzinfo=zone)
                break
            next_local = (next_local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            if next_local.weekday() < 5:
                candidate = datetime.combine(next_local.date(), start, tzinfo=zone)
                break
        return {
            "allowed": False,
            "reason": "outside_send_window",
            "timezone": timezone_name,
            "reschedule_at": candidate.astimezone(UTC),
            "local_time": local_now.isoformat(),
        }

    async def daily_send_cap_status(self, session, tenant_id: uuid.UUID, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now(UTC)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        sent = await session.scalar(
            select(func.count()).select_from(OutreachLog).where(
                OutreachLog.tenant_id == tenant_id,
                OutreachLog.status == OutreachStatus.SENT,
                OutreachLog.sent_at >= day_start,
            )
        ) or 0
        cap = self.current_daily_cap()
        if int(sent) >= cap:
            next_day = (day_start + timedelta(days=1)).replace(hour=8, minute=30)
            return {
                "allowed": False,
                "reason": "daily_send_cap_reached",
                "sent_today": int(sent),
                "cap": cap,
                "reschedule_at": next_day,
            }
        return {"allowed": True, "sent_today": int(sent), "cap": cap}

    def current_daily_cap(self) -> int:
        configured_cap = max(1, int(settings.OUTREACH_DAILY_SEND_CAP or 50))
        domain_age_days = max(0, int(settings.OUTREACH_DOMAIN_AGE_DAYS or 0))
        if domain_age_days < 14:
            return min(configured_cap, 20)
        if domain_age_days < 28:
            return min(configured_cap, 35)
        return min(configured_cap, 50)

    async def is_outreach_paused(self, session, tenant_id: uuid.UUID) -> bool:
        if settings.OUTREACH_PAUSED:
            return True
        state = await session.scalar(
            select(OutreachPauseState).where(
                OutreachPauseState.tenant_id == tenant_id,
                OutreachPauseState.scope == "global",
            )
        )
        return bool(state and state.paused)

    async def resume_outreach(self, session, tenant_id: uuid.UUID, *, reason: str, actor: str = "Captain") -> dict:
        state = await session.scalar(
            select(OutreachPauseState).where(
                OutreachPauseState.tenant_id == tenant_id,
                OutreachPauseState.scope == "global",
            )
        )
        if not state:
            state = OutreachPauseState(
                tenant_id=tenant_id,
                scope="global",
                paused=False,
                reason=reason,
                resumed_by=actor,
                resumed_at=datetime.now(UTC),
            )
            session.add(state)
            await session.flush()
        else:
            state.paused = False
            state.reason = reason
            state.resumed_by = actor
            state.resumed_at = datetime.now(UTC)
        session.add(
            AuditLog(
                tenant_id=tenant_id,
                action="outreach_resumed",
                entity_type="outreach_pause_state",
                entity_id=state.id,
                actor=actor,
                details={"reason": reason},
                after_json={"paused": False, "reason": reason},
            )
        )
        return {"resumed": True, "reason": reason}

    async def pause_outreach(self, session, tenant_id: uuid.UUID, *, reason: str, actor: str = "JARVIS") -> dict:
        state = await session.scalar(
            select(OutreachPauseState).where(
                OutreachPauseState.tenant_id == tenant_id,
                OutreachPauseState.scope == "global",
            )
        )
        if not state:
            state = OutreachPauseState(
                tenant_id=tenant_id,
                scope="global",
                paused=True,
                reason=reason,
                paused_by=actor,
            )
            session.add(state)
            await session.flush()
        else:
            state.paused = True
            state.reason = reason
            state.paused_by = actor
            state.resumed_by = None
            state.resumed_at = None
        session.add(
            AuditLog(
                tenant_id=tenant_id,
                action="outreach_paused",
                entity_type="outreach_pause_state",
                entity_id=state.id,
                actor=actor,
                details={"reason": reason},
                after_json={"paused": True, "reason": reason},
            )
        )
        return {"paused": True, "reason": reason}

    async def assess_reply_rate_pause(
        self,
        session,
        tenant_id: uuid.UUID,
        *,
        lookback_days: int = 7,
        min_sent: int = 25,
        min_reply_rate: float = 0.01,
    ) -> dict[str, Any]:
        since = datetime.now(UTC) - timedelta(days=max(1, int(lookback_days)))
        sent = await session.scalar(
            select(func.count()).select_from(OutreachLog).where(
                OutreachLog.tenant_id == tenant_id,
                OutreachLog.status == OutreachStatus.SENT,
                OutreachLog.sent_at >= since,
            )
        ) or 0
        replies = await session.scalar(
            select(func.count()).select_from(ReplyLog).where(
                ReplyLog.tenant_id == tenant_id,
                ReplyLog.processed_at >= since,
            )
        ) or 0
        sent_count = int(sent)
        reply_count = int(replies)
        reply_rate = round(reply_count / sent_count, 4) if sent_count else 0.0
        should_pause = sent_count >= min_sent and reply_rate < min_reply_rate
        result = {
            "sent": sent_count,
            "replies": reply_count,
            "reply_rate": reply_rate,
            "min_reply_rate": min_reply_rate,
            "lookback_days": lookback_days,
            "paused": False,
        }
        if should_pause:
            await self.pause_outreach(
                session,
                tenant_id,
                reason=(
                    f"Reply rate {reply_rate:.2%} is below the {min_reply_rate:.2%} floor "
                    f"after {sent_count} sends in {lookback_days} days."
                ),
                actor="OutreachSafetyMonitor",
            )
            result["paused"] = True
        else:
            session.add(
                AuditLog(
                    tenant_id=tenant_id,
                    action="outreach_reply_rate_checked",
                    entity_type="outreach_pause_state",
                    actor="OutreachSafetyMonitor",
                    details=result,
                    after_json=result,
                )
            )
        return result

    def append_footer(self, body_text: str, recipient_email: str) -> str:
        token = self.unsubscribe_token(recipient_email)
        base = settings.APP_BASE_URL.rstrip("/") if settings.APP_BASE_URL else ""
        unsubscribe_url = f"{base}/api/v1/outreach/unsubscribe?token={token}" if base else ""
        footer = (
            "\n\n--\n"
            f"{settings.COMPANY_PHYSICAL_ADDRESS}\n"
            f"Unsubscribe: {unsubscribe_url}"
        )
        if "unsubscribe:" in (body_text or "").lower():
            return body_text or ""
        return f"{body_text or ''}{footer}"

    def has_opt_out_intent(self, text: str) -> bool:
        lowered = f" {(text or '').lower()} "
        return any(term in lowered for term in OPT_OUT_TERMS)

    async def _has_approved_outreach_review(self, session, tenant_id: uuid.UUID, lead_id: uuid.UUID) -> bool:
        existing = await session.scalar(
            select(ApprovalRequest.id).where(
                ApprovalRequest.tenant_id == tenant_id,
                ApprovalRequest.action_type == "outreach_enrollment_review",
                ApprovalRequest.status == ApprovalStatus.APPROVED,
                ApprovalRequest.payload["lead_id"].as_string() == str(lead_id),
            )
        )
        return bool(existing)

    async def _queue_qualification_review(self, session, tenant_id: uuid.UUID, lead: Lead) -> None:
        existing = await session.scalar(
            select(ApprovalRequest.id).where(
                ApprovalRequest.tenant_id == tenant_id,
                ApprovalRequest.action_type == "outreach_enrollment_review",
                ApprovalRequest.status == ApprovalStatus.PENDING,
                ApprovalRequest.payload["lead_id"].as_string() == str(lead.id),
            )
        )
        if existing:
            return
        session.add(
            ApprovalRequest(
                tenant_id=tenant_id,
                action_type="outreach_enrollment_review",
                title=f"Review outreach enrollment: {lead.company_name or lead.company or lead.email}",
                summary=(
                    f"Lead score is {float(lead.score or 0.0):.1f}. "
                    "Batch 4 threshold requires Captain approval for scores 65-79."
                ),
                priority=3,
                risk_level="MEDIUM",
                status=ApprovalStatus.PENDING,
                raised_by="OutreachComplianceService",
                payload={
                    "lead_id": str(lead.id),
                    "company": lead.company_name or lead.company,
                    "score": float(lead.score or 0.0),
                    "threshold": "65-79_review_required",
                },
            )
        )


def normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def infer_timezone(country: str | None) -> str:
    key = (country or "").strip().lower()
    return COUNTRY_TIMEZONES.get(key, "UTC")


def _secret() -> bytes:
    return (settings.SECRET_KEY or "jarvis").encode("utf-8")


outreach_compliance = OutreachComplianceService()
