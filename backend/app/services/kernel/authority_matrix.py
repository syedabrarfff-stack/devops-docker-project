"""K1-3 (part 1): JARVIS Authority Matrix — the data layer.

This module defines every operation's authority tier as a data structure,
loaded at startup. The Policy Engine (policy_engine.py) enforces these rules
at runtime by intercepting every autonomous action before execution.

Tiers:
  AUTO        — execute without Captain approval
  ASK_CAPTAIN — halt, surface to Captain, wait for explicit approval
  NEVER       — block unconditionally; requires explicit written order from Captain

Adding a new operation: append one entry to AUTHORITY_MATRIX below.
No code logic changes required — the Policy Engine reads this table.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AuthorityTier(str, Enum):
    AUTO = "AUTO"
    ASK_CAPTAIN = "ASK_CAPTAIN"
    NEVER = "NEVER"


@dataclass(frozen=True)
class AuthorityRule:
    operation: str          # Pattern — exact match or prefix glob
    tier: AuthorityTier
    reason: str             # Why this tier — must be non-empty
    reversible: bool        # Quick-check hint for the Policy Engine


# The canonical Authority Matrix (from §2.1 of JARVIS_V4_ARCHITECTURE.md).
# Order: most specific rules first; the Policy Engine stops at first match.
AUTHORITY_MATRIX: list[AuthorityRule] = [
    # ── NEVER — absolute blocks ───────────────────────────────────────────────
    AuthorityRule(
        operation="db.drop_table",
        tier=AuthorityTier.NEVER,
        reason="Irreversible — explicit written order from Captain required",
        reversible=False,
    ),
    AuthorityRule(
        operation="db.delete_production_data",
        tier=AuthorityTier.NEVER,
        reason="Irreversible data loss — explicit written order required",
        reversible=False,
    ),
    AuthorityRule(
        operation="git.force_push_main",
        tier=AuthorityTier.NEVER,
        reason="Destroys shared history — forbidden without written order",
        reversible=False,
    ),
    AuthorityRule(
        operation="aws.iam.modify_roles",
        tier=AuthorityTier.NEVER,
        reason="Can lock out Captain — requires explicit written order",
        reversible=False,
    ),
    AuthorityRule(
        operation="aws.iam.modify_security_groups",
        tier=AuthorityTier.NEVER,
        reason="Can expose or lock down infrastructure — requires explicit order",
        reversible=False,
    ),

    # ── ASK_CAPTAIN — destructive or commercial ───────────────────────────────
    AuthorityRule(
        operation="db.drop_column",
        tier=AuthorityTier.ASK_CAPTAIN,
        reason="Destructive to existing data",
        reversible=False,
    ),
    AuthorityRule(
        operation="db.alter_column_type",
        tier=AuthorityTier.ASK_CAPTAIN,
        reason="May corrupt existing data",
        reversible=False,
    ),
    AuthorityRule(
        operation="integration.add_external_credentials",
        tier=AuthorityTier.ASK_CAPTAIN,
        reason="Financial and access implications",
        reversible=True,
    ),
    AuthorityRule(
        operation="client.pricing",
        tier=AuthorityTier.ASK_CAPTAIN,
        reason="Brand and commercial authority",
        reversible=True,
    ),
    AuthorityRule(
        operation="client.contract",
        tier=AuthorityTier.ASK_CAPTAIN,
        reason="Legal and commercial authority",
        reversible=True,
    ),
    AuthorityRule(
        operation="client.communication",
        tier=AuthorityTier.ASK_CAPTAIN,
        reason="Brand authority — external communication",
        reversible=True,
    ),

    # ── AUTO — safe, additive, or well-tested ────────────────────────────────
    AuthorityRule(
        operation="bug.fix",
        tier=AuthorityTier.AUTO,
        reason="Reversible, low blast radius",
        reversible=True,
    ),
    AuthorityRule(
        operation="security.patch",
        tier=AuthorityTier.AUTO,
        reason="Reverting a patch is safe and fast",
        reversible=True,
    ),
    AuthorityRule(
        operation="performance.improvement",
        tier=AuthorityTier.AUTO,
        reason="Reversible, observable",
        reversible=True,
    ),
    AuthorityRule(
        operation="endpoint.add",
        tier=AuthorityTier.AUTO,
        reason="Additive — nothing removed",
        reversible=True,
    ),
    AuthorityRule(
        operation="model.add",
        tier=AuthorityTier.AUTO,
        reason="Additive — nothing removed",
        reversible=True,
    ),
    AuthorityRule(
        operation="scheduler.job.add",
        tier=AuthorityTier.AUTO,
        reason="Additive — can be paused or removed",
        reversible=True,
    ),
    AuthorityRule(
        operation="ci.fix_and_redeploy",
        tier=AuthorityTier.AUTO,
        reason="Verified before push; CI failure diagnosed",
        reversible=True,
    ),
    AuthorityRule(
        operation="db.add_column",
        tier=AuthorityTier.AUTO,
        reason="Additive, no data loss",
        reversible=True,
    ),
    AuthorityRule(
        operation="db.create_index",
        tier=AuthorityTier.AUTO,
        reason="Additive, no data loss",
        reversible=True,
    ),
    AuthorityRule(
        operation="monitoring.configure",
        tier=AuthorityTier.AUTO,
        reason="Observability is always safe",
        reversible=True,
    ),
    AuthorityRule(
        operation="kernel.state.read",
        tier=AuthorityTier.AUTO,
        reason="Read-only",
        reversible=True,
    ),
    AuthorityRule(
        operation="kernel.event.publish",
        tier=AuthorityTier.AUTO,
        reason="Events are observable and logged",
        reversible=True,
    ),
    AuthorityRule(
        operation="audit.log.write",
        tier=AuthorityTier.AUTO,
        reason="Append-only write is always safe",
        reversible=True,
    ),
]

# Fast lookup map built at import time: operation → AuthorityRule
_MATRIX_MAP: dict[str, AuthorityRule] = {r.operation: r for r in AUTHORITY_MATRIX}


def lookup(operation: str) -> AuthorityRule | None:
    """Exact-match lookup. Returns None if no rule found (caller should default to ASK)."""
    return _MATRIX_MAP.get(operation)


def lookup_tier(operation: str, default: AuthorityTier = AuthorityTier.ASK_CAPTAIN) -> AuthorityTier:
    """Return the tier for an operation; defaults to ASK_CAPTAIN if unknown."""
    rule = lookup(operation)
    return rule.tier if rule is not None else default
