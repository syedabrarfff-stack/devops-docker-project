"""K1-3 (part 2): JARVIS Policy Engine — Authority Matrix interceptor.

Every autonomous action passes through this engine before execution.
The Policy Engine:
  1. Looks up the operation in the Authority Matrix
  2. AUTO → log and permit
  3. ASK_CAPTAIN → log, halt execution, surface to Captain via Telegram, wait
  4. NEVER → log, raise PolicyViolationError, do not execute
  5. Records every check to the Audit Logger

The Policy Engine is the single choke point for all autonomous behaviour.
It makes "no hidden automation" enforceable.

Usage:
    engine = PolicyEngine(db_session)
    decision = await engine.check("db.add_column", actor="health_aggregator",
                                  resource_id=some_uuid, details={"column": "..."})
    if decision.permitted:
        # proceed
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.kernel.authority_matrix import AuthorityTier, lookup_tier, lookup
from app.services.kernel.audit_logger import AuditLogger

log = logging.getLogger(__name__)


class PolicyViolationError(Exception):
    """Raised when a NEVER-tier operation is attempted."""


@dataclass
class PolicyDecision:
    operation: str
    tier: AuthorityTier
    permitted: bool             # True for AUTO; False for ASK_CAPTAIN + NEVER
    requires_captain: bool      # True for ASK_CAPTAIN
    reason: str
    audit_id: Optional[uuid.UUID] = None


class PolicyEngine:
    """Enforce the Authority Matrix before every autonomous action.

    Inject a DB session per-request (same pattern as the rest of the codebase).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audit = AuditLogger(session)

    async def check(
        self,
        operation: str,
        actor: str,
        resource_id: uuid.UUID | None = None,
        details: dict | None = None,
    ) -> PolicyDecision:
        """Evaluate whether `actor` may perform `operation`.

        Raises:
            PolicyViolationError: if tier is NEVER.
        Returns:
            PolicyDecision with permitted=True for AUTO.
            PolicyDecision with permitted=False for ASK_CAPTAIN — caller must
            surface to Captain and await explicit approval before proceeding.
        """
        tier = lookup_tier(operation)
        rule = lookup(operation)
        reason = rule.reason if rule else "Unknown operation — defaulting to ASK_CAPTAIN"

        details_payload = {
            **(details or {}),
            "operation": operation,
            "tier": tier.value,
            "reason": reason,
        }

        if tier == AuthorityTier.NEVER:
            audit_id = await self._audit.write(
                action_type="policy.blocked",
                actor=actor,
                resource_id=resource_id,
                details=details_payload,
                outcome="BLOCKED",
            )
            log.critical(
                "PolicyEngine: BLOCKED (NEVER) — %s by %s | %s",
                operation,
                actor,
                reason,
            )
            raise PolicyViolationError(
                f"Operation '{operation}' is unconditionally blocked. "
                f"Reason: {reason}. Explicit written order from Captain required."
            )

        if tier == AuthorityTier.ASK_CAPTAIN:
            audit_id = await self._audit.write(
                action_type="policy.captain_required",
                actor=actor,
                resource_id=resource_id,
                details=details_payload,
                outcome="PENDING_CAPTAIN_APPROVAL",
            )
            log.warning(
                "PolicyEngine: HALTED (ASK_CAPTAIN) — %s by %s | %s",
                operation,
                actor,
                reason,
            )
            # Surface to Captain via Telegram (fire-and-forget — import lazily
            # to avoid circular deps; failure here must not block the decision).
            try:
                await self._notify_captain(operation, actor, reason, details)
            except Exception as exc:
                log.error("PolicyEngine: Captain notification failed: %s", exc)

            return PolicyDecision(
                operation=operation,
                tier=tier,
                permitted=False,
                requires_captain=True,
                reason=reason,
                audit_id=audit_id,
            )

        # AUTO
        audit_id = await self._audit.write(
            action_type="policy.approved",
            actor=actor,
            resource_id=resource_id,
            details=details_payload,
            outcome="APPROVED",
        )
        log.debug("PolicyEngine: APPROVED (AUTO) — %s by %s", operation, actor)

        return PolicyDecision(
            operation=operation,
            tier=tier,
            permitted=True,
            requires_captain=False,
            reason=reason,
            audit_id=audit_id,
        )

    async def assert_auto(
        self,
        operation: str,
        actor: str,
        resource_id: uuid.UUID | None = None,
        details: dict | None = None,
    ) -> None:
        """Like check() but raises PolicyViolationError for non-AUTO outcomes.

        Use when the caller has no mechanism to wait for Captain approval.
        """
        decision = await self.check(operation, actor, resource_id, details)
        if not decision.permitted:
            raise PolicyViolationError(
                f"Operation '{operation}' requires Captain approval "
                f"but caller used assert_auto. Halting."
            )

    async def _notify_captain(
        self,
        operation: str,
        actor: str,
        reason: str,
        details: dict | None,
    ) -> None:
        """Fire-and-forget Captain notification via Telegram bridge."""
        try:
            from app.services.captain import telegram_bridge
            msg = (
                f"⚠️ *Captain Approval Required*\n\n"
                f"*Operation:* `{operation}`\n"
                f"*Requested by:* `{actor}`\n"
                f"*Reason for hold:* {reason}\n"
                f"*Details:* {details or {}}\n\n"
                f"Reply with /approve or /reject followed by the operation name."
            )
            await telegram_bridge.send_captain_alert(msg)
        except Exception:
            pass  # Notification failure must never block policy enforcement
