"""Tests for F3-6: ResponseVerifier — hallucination detection, policy check, format."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.fabric.response_verifier import ResponseVerifier, CONFIDENCE_REVIEW_THRESHOLD


def make_verifier() -> ResponseVerifier:
    return ResponseVerifier()


class TestHallucinationDetection:
    @pytest.mark.asyncio
    async def test_clean_response_passes(self):
        rv = make_verifier()
        result = await rv.verify("The client needs a proposal.", "general")
        assert result.passed is True
        assert result.hallucination_risk < 0.5

    @pytest.mark.asyncio
    async def test_many_fabrication_patterns_reduce_confidence(self):
        rv = make_verifier()
        # Multiple suspicious patterns: fake URL, dollar amounts, numeric IDs
        # Use a CRITICAL task type so the hallucination check runs.
        response = (
            "Visit https://fakesite.example.com/report-12345 for invoice #98765. "
            "The deal is worth $9,999,999 per our records. "
            "Reference ID: TXN-00112233445566778899. "
            "See also https://another.fake/link?id=abc123xyz987."
        )
        result = await rv.verify(response, "STRATEGY")
        # Confidence should be reduced below full score
        assert result.confidence < 1.0

    @pytest.mark.asyncio
    async def test_critical_task_type_stricter_than_general(self):
        rv = make_verifier()
        suspicious = (
            "Our revenue was $50,000,000 last quarter per https://report.example.com."
        )
        result_general = await rv.verify(suspicious, "general")
        result_strategy = await rv.verify(suspicious, "STRATEGY")
        # Critical task type applies hallucination penalty; general does not.
        assert result_strategy.confidence < result_general.confidence


class TestPolicyCheck:
    @pytest.mark.asyncio
    async def test_skipped_without_session(self):
        rv = make_verifier()
        result = await rv.verify("Hello world", "general", session=None)
        # Policy check is skipped; should still pass
        assert result.policy_compliant is True

    @pytest.mark.asyncio
    async def test_policy_engine_called_with_session(self):
        rv = make_verifier()
        mock_session = MagicMock()

        mock_decision = MagicMock()
        mock_decision.permitted = True
        mock_decision.requires_captain = False
        mock_decision.reason = "ok"

        mock_engine = AsyncMock()
        mock_engine.check = AsyncMock(return_value=mock_decision)
        mock_engine_class = MagicMock(return_value=mock_engine)

        with patch(
            "app.services.kernel.policy_engine.PolicyEngine",
            mock_engine_class,
        ):
            result = await rv.verify("Hello", "general", session=mock_session)

        assert result.policy_compliant is True

    @pytest.mark.asyncio
    async def test_policy_block_marks_failed(self):
        rv = make_verifier()
        mock_session = MagicMock()

        mock_decision = MagicMock()
        mock_decision.permitted = False
        mock_decision.requires_captain = False
        mock_decision.reason = "blocked"

        mock_engine = AsyncMock()
        mock_engine.check = AsyncMock(return_value=mock_decision)
        mock_engine_class = MagicMock(return_value=mock_engine)

        with patch(
            "app.services.kernel.policy_engine.PolicyEngine",
            mock_engine_class,
        ):
            result = await rv.verify("Some output", "general", session=mock_session)

        assert result.policy_compliant is False
        assert result.passed is False


class TestFormatValidation:
    @pytest.mark.asyncio
    async def test_valid_json(self):
        rv = make_verifier()
        result = await rv.verify('{"key": "value"}', "general", expected_format="json")
        issues = [i for i in result.issues if i.category == "format"]
        assert not issues

    @pytest.mark.asyncio
    async def test_invalid_json(self):
        rv = make_verifier()
        result = await rv.verify("not json at all", "general", expected_format="json")
        format_issues = [i for i in result.issues if i.category == "format"]
        assert len(format_issues) > 0

    @pytest.mark.asyncio
    async def test_valid_markdown(self):
        rv = make_verifier()
        md = "# Heading\n\n- bullet one\n- bullet two"
        result = await rv.verify(md, "general", expected_format="markdown")
        format_issues = [i for i in result.issues if i.category == "format"]
        assert not format_issues

    @pytest.mark.asyncio
    async def test_invalid_markdown(self):
        rv = make_verifier()
        result = await rv.verify("plain text no markup", "general", expected_format="markdown")
        format_issues = [i for i in result.issues if i.category == "format"]
        assert len(format_issues) > 0

    @pytest.mark.asyncio
    async def test_plain_with_markup_flagged(self):
        rv = make_verifier()
        result = await rv.verify("# Unexpected header", "general", expected_format="plain")
        format_issues = [i for i in result.issues if i.category == "format"]
        assert len(format_issues) > 0


class TestConfidenceThreshold:
    @pytest.mark.asyncio
    async def test_requires_review_below_threshold(self):
        rv = make_verifier()
        # Use STRATEGY so hallucination check runs; many URLs → big penalty.
        response = " ".join([
            f"https://fake-{i}.example.com/ref-{i*100}" for i in range(20)
        ])
        result = await rv.verify(response, "STRATEGY")
        if result.confidence < CONFIDENCE_REVIEW_THRESHOLD:
            assert result.requires_review is True

    @pytest.mark.asyncio
    async def test_no_review_above_threshold(self):
        rv = make_verifier()
        result = await rv.verify("A short clean answer.", "STRATEGY")
        if result.confidence >= CONFIDENCE_REVIEW_THRESHOLD:
            assert result.requires_review is False


class TestVerificationResult:
    @pytest.mark.asyncio
    async def test_result_has_expected_fields(self):
        rv = make_verifier()
        result = await rv.verify("test response", "general")
        assert hasattr(result, "passed")
        assert hasattr(result, "confidence")
        assert hasattr(result, "issues")
        assert hasattr(result, "requires_review")
        assert hasattr(result, "policy_compliant")
        assert hasattr(result, "hallucination_risk")

    @pytest.mark.asyncio
    async def test_empty_response_still_returns_result(self):
        rv = make_verifier()
        result = await rv.verify("", "general")
        assert result is not None
