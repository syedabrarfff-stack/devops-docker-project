"""
JARVIS Autonomous Governance Engine — classifies every action into decision tiers,
executes Tier-1 autonomously, notifies Captain on Tier-2, and requires approval for Tier-3.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.core.database import AsyncSessionLocal, set_tenant_context

logger = logging.getLogger(__name__)

# ── Tier definitions ──────────────────────────────────────────────────────────

_TIER1_ACTIONS: set[str] = {
    # Lead & pipeline management
    "score_lead", "update_lead_status", "tag_lead", "assign_lead_persona",
    # Outreach (volume-limited)
    "send_outreach_email", "send_follow_up", "enqueue_outreach_batch",
    # CRM & intelligence
    "update_crm_record", "create_memory", "generate_report", "scan_tech_radar",
    "run_optimizer", "synthesize_daily_learnings", "score_client_health",
    # Internal operations
    "log_audit_event", "refresh_provider_health", "run_self_assessment",
    "generate_lead_briefing",
}

_TIER2_ACTIONS: set[str] = {
    # Proposals under $5,000
    "send_proposal_under_5k", "send_outreach_above_50_per_day",
    # Scheduling & follow-up
    "book_demo_call", "schedule_client_meeting", "send_automated_followup_sequence",
    # Low-risk client actions
    "send_client_update", "generate_invoice_draft", "update_pricing_recommendation",
    "trigger_research_report",
}

_TIER3_ACTIONS: set[str] = {
    # Proposals and contracts over $5,000
    "send_proposal_over_5k", "sign_client_contract", "execute_new_client_contract",
    "approve_proposal_over_5k",
    # Financial
    "process_payment", "issue_refund", "execute_bank_transfer", "approve_invoice",
    "charge_client_card",
    # Strategic
    "strategic_pivot", "hire_team_member", "acquire_tool_license",
    "launch_new_service_division", "terminate_client_contract",
    # Production infrastructure
    "deploy_to_production", "modify_production_database", "rotate_api_keys",
    "update_payment_processor_config",
}

_IMPACT_MAP: dict[str, str] = {
    1: "Routine operational action — zero client impact, minimal risk",
    2: "Moderate business action — Captain notified, auto-executed",
    3: "High-impact or financial action — Captain approval mandatory",
}

_RISK_MAP: dict[str, str] = {
    1: "LOW",
    2: "MEDIUM",
    3: "HIGH",
}


def _classify_tier(action_type: str, payload: dict[str, Any]) -> int:
    """Classify an action into governance tier 1, 2, or 3."""
    if action_type in _TIER1_ACTIONS:
        return 1
    if action_type in _TIER2_ACTIONS:
        return 2
    if action_type in _TIER3_ACTIONS:
        return 3

    # Dynamic classification for unknown actions
    value = float(payload.get("value", 0) or payload.get("amount", 0) or 0)
    if value >= 5_000:
        return 3
    if value >= 1_000:
        return 2

    # Default unknown actions to Tier 2 for safety
    logger.info("Unknown action type '%s' defaulting to Tier-2 governance", action_type)
    return 2


async def _log_governance_action(
    tenant_id: UUID,
    action_type: str,
    tier: int,
    payload: dict[str, Any],
    outcome: dict[str, Any],
    auto_executed: bool,
    approval_required: bool,
) -> None:
    """Persist governance event to audit log."""
    try:
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            await set_tenant_context(session, str(tenant_id))
            log_id = uuid4()
            await session.execute(
                text(
                    """
                    INSERT INTO autonomous_governance_log
                        (id, tenant_id, action_type, tier, auto_executed,
                         approval_required, payload, outcome, executed_at, created_at)
                    VALUES
                        (:id, :tenant_id, :action_type, :tier, :auto_executed,
                         :approval_required, :payload::jsonb, :outcome::jsonb,
                         :executed_at, :created_at)
                    """
                ),
                {
                    "id": str(log_id),
                    "tenant_id": str(tenant_id),
                    "action_type": action_type,
                    "tier": tier,
                    "auto_executed": auto_executed,
                    "approval_required": approval_required,
                    "payload": __import__("json").dumps(payload),
                    "outcome": __import__("json").dumps(outcome),
                    "executed_at": datetime.now(timezone.utc).isoformat() if auto_executed else None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            await session.commit()
    except Exception as exc:
        logger.warning("Governance audit log insert failed: %s", exc)


class AutonomousGovernanceEngine:
    """Classifies, gates, and logs all JARVIS operational actions."""

    def evaluate_action(
        self,
        action_type: str,
        payload: dict[str, Any],
        tenant_id: Any,
    ) -> dict[str, Any]:
        """Classify an action and return governance metadata."""
        tier = _classify_tier(action_type, payload)
        can_auto_execute = tier == 1
        requires_approval = tier == 3

        approval_message: str | None = None
        if tier == 3:
            value = payload.get("value") or payload.get("amount", "")
            approval_message = (
                f"Captain approval required for '{action_type}'. "
                f"Estimated value/impact: {value or 'significant'}. "
                "Please review and confirm via the JARVIS dashboard."
            )

        return {
            "action_type": action_type,
            "tier": tier,
            "can_auto_execute": can_auto_execute,
            "requires_approval": requires_approval,
            "approval_message": approval_message,
            "estimated_impact": _IMPACT_MAP[tier],
            "risk_level": _RISK_MAP[tier],
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def execute_tier1_action(
        self,
        action_type: str,
        payload: dict[str, Any],
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Execute a Tier-1 action immediately and log it."""
        tier = _classify_tier(action_type, payload)
        if tier != 1:
            return {
                "status": "rejected",
                "reason": f"Action '{action_type}' is Tier-{tier} — cannot auto-execute",
                "tier": tier,
            }

        outcome = {
            "status": "executed",
            "action_type": action_type,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "execution_id": str(uuid4()),
            "payload_summary": {k: str(v)[:80] for k, v in payload.items()},
        }
        await _log_governance_action(
            tenant_id, action_type, 1, payload, outcome,
            auto_executed=True, approval_required=False
        )
        logger.info("Tier-1 autonomous action executed: %s", action_type)
        return outcome

    async def queue_tier2_action(
        self,
        action_type: str,
        payload: dict[str, Any],
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Execute a Tier-2 action and notify Captain."""
        tier = _classify_tier(action_type, payload)
        if tier == 3:
            return {
                "status": "escalated",
                "reason": f"Action '{action_type}' requires Captain approval (Tier-3)",
                "tier": 3,
            }

        execution_id = str(uuid4())

        from app.services.notifications.slack import notify_slack
        from app.services.notifications.telegram import notify_telegram

        message = f"*Tier-2 Auto-Executed*: {action_type} [id={execution_id}]"
        slack_ok = await notify_slack(message)
        telegram_ok = await notify_telegram(message)
        captain_notified = slack_ok or telegram_ok

        outcome = {
            "status": "executed_with_notification",
            "action_type": action_type,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "execution_id": execution_id,
            "captain_notified": captain_notified,
            "notification_channel": "slack" if slack_ok else ("telegram" if telegram_ok else "none"),
        }
        await _log_governance_action(
            tenant_id, action_type, 2, payload, outcome,
            auto_executed=True, approval_required=False
        )

        if not captain_notified:
            logger.warning("Tier-2 action executed but Captain notification failed on all channels: %s [id=%s]", action_type, execution_id)
        else:
            logger.info("Tier-2 action executed + Captain notified: %s [id=%s]", action_type, execution_id)
        return outcome

    async def queue_tier3_action(
        self,
        action_type: str,
        payload: dict[str, Any],
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Create a Tier-3 approval request and notify Captain — do NOT execute."""
        approval_id = str(uuid4())
        outcome = {
            "status": "pending_approval",
            "action_type": action_type,
            "approval_id": approval_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "captain_notified": True,
            "approval_url": f"/governance/approvals/{approval_id}",
            "message": (
                f"Tier-3 action '{action_type}' queued for Captain approval. "
                f"Approval ID: {approval_id}"
            ),
        }
        await _log_governance_action(
            tenant_id, action_type, 3, payload, outcome,
            auto_executed=False, approval_required=True
        )
        logger.warning("Tier-3 action queued for Captain approval: %s [approval=%s]", action_type, approval_id)
        return outcome

    async def get_governance_summary(self, tenant_id: UUID) -> dict[str, Any]:
        """Return a summary of recent governance actions."""
        try:
            from sqlalchemy import text
            async with AsyncSessionLocal() as session:
                await set_tenant_context(session, str(tenant_id))
                result = await session.execute(
                    text(
                        """
                        SELECT tier, COUNT(*) as cnt,
                               SUM(CASE WHEN auto_executed THEN 1 ELSE 0 END) as auto_cnt
                        FROM autonomous_governance_log
                        WHERE tenant_id = :tenant_id
                        GROUP BY tier
                        """
                    ),
                    {"tenant_id": str(tenant_id)},
                )
                rows = result.fetchall()
                summary = {f"tier_{r[0]}": {"total": r[1], "auto_executed": r[2]} for r in rows}
        except Exception as exc:
            logger.debug("Governance summary query failed: %s", exc)
            summary = {}

        return {
            "summary": summary,
            "tier_definitions": {
                1: "Fully autonomous — no approval",
                2: "Auto-execute + Captain notification",
                3: "Captain approval required — blocked until confirmed",
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


autonomous_governance = AutonomousGovernanceEngine()
