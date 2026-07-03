"""Tests for K1-3: Authority Matrix — lookup, tier correctness."""
from __future__ import annotations

import pytest

from app.services.kernel.authority_matrix import (
    AuthorityTier,
    AuthorityRule,
    AUTHORITY_MATRIX,
    lookup,
    lookup_tier,
)


class TestAuthorityMatrixData:
    def test_all_rules_have_non_empty_reason(self):
        for rule in AUTHORITY_MATRIX:
            assert rule.reason, f"Rule '{rule.operation}' has empty reason"

    def test_no_duplicate_operations(self):
        ops = [r.operation for r in AUTHORITY_MATRIX]
        assert len(ops) == len(set(ops)), "Duplicate operation keys in AUTHORITY_MATRIX"

    def test_never_tier_operations_are_not_reversible(self):
        for rule in AUTHORITY_MATRIX:
            if rule.tier == AuthorityTier.NEVER:
                assert not rule.reversible, (
                    f"NEVER operation '{rule.operation}' incorrectly marked reversible"
                )


class TestLookup:
    def test_exact_match_auto(self):
        rule = lookup("bug.fix")
        assert rule is not None
        assert rule.tier == AuthorityTier.AUTO

    def test_exact_match_never(self):
        rule = lookup("db.drop_table")
        assert rule is not None
        assert rule.tier == AuthorityTier.NEVER

    def test_exact_match_ask(self):
        rule = lookup("db.drop_column")
        assert rule is not None
        assert rule.tier == AuthorityTier.ASK_CAPTAIN

    def test_unknown_operation_returns_none(self):
        assert lookup("something.completely.unknown") is None

    def test_lookup_tier_defaults_to_ask(self):
        tier = lookup_tier("totally.unknown.operation")
        assert tier == AuthorityTier.ASK_CAPTAIN

    def test_lookup_tier_known_auto(self):
        assert lookup_tier("audit.log.write") == AuthorityTier.AUTO

    def test_lookup_tier_known_never(self):
        assert lookup_tier("git.force_push_main") == AuthorityTier.NEVER

    def test_lookup_tier_custom_default(self):
        tier = lookup_tier("unknown.op", default=AuthorityTier.AUTO)
        assert tier == AuthorityTier.AUTO


class TestCoverage:
    """Spot-check that key operations from §2.1 of JARVIS_V4_ARCHITECTURE.md are present."""

    def test_db_operations_covered(self):
        assert lookup("db.drop_table") is not None
        assert lookup("db.add_column") is not None
        assert lookup("db.delete_production_data") is not None

    def test_git_operations_covered(self):
        assert lookup("git.force_push_main") is not None

    def test_aws_operations_covered(self):
        assert lookup("aws.iam.modify_roles") is not None

    def test_kernel_operations_auto(self):
        assert lookup_tier("kernel.state.read") == AuthorityTier.AUTO
        assert lookup_tier("audit.log.write") == AuthorityTier.AUTO
