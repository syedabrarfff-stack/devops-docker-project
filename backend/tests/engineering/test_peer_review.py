"""E7-10: Tests for the Peer Review Gate (E7-7)."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.engineering import EngineeringWorkPackage, WorkPackageStatus
from app.services.engineering.peer_review import review_work_package


def _wp(draft_output=None):
    return EngineeringWorkPackage(
        id=uuid.uuid4(),
        task_graph_id=uuid.uuid4(),
        department="backend",
        title="test package",
        acceptance_criteria=["works"],
        draft_output=draft_output or {"summary": "s", "approach": "a"},
        status=WorkPackageStatus.IN_REVIEW,
    )


def _mock_outcome(decision, confidence=0.9):
    outcome = MagicMock()
    outcome.recommendation.to_dict.return_value = {
        "decision": decision,
        "aggregate_confidence": confidence,
        "unified_reasoning": "test reasoning",
    }
    return outcome


class TestReviewWorkPackage:
    @pytest.mark.asyncio
    async def test_raises_without_a_draft(self):
        wp = _wp(draft_output=None)
        wp.draft_output = None
        with pytest.raises(ValueError, match="no draft_output"):
            await review_work_package(MagicMock(), wp)

    @pytest.mark.asyncio
    async def test_approve_decision_sets_approved_status(self):
        wp = _wp()
        db = MagicMock()
        db.flush = AsyncMock()
        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=_mock_outcome("APPROVE"))

        with patch("app.services.engineering.peer_review.get_council_session", return_value=mock_session):
            result = await review_work_package(db, wp)

        assert wp.status == WorkPackageStatus.APPROVED
        assert result["decision"] == "APPROVE"

    @pytest.mark.asyncio
    async def test_captain_review_decision_sets_blocked_status(self):
        wp = _wp()
        db = MagicMock()
        db.flush = AsyncMock()
        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=_mock_outcome("CAPTAIN_REVIEW"))

        with patch("app.services.engineering.peer_review.get_council_session", return_value=mock_session):
            await review_work_package(db, wp)

        assert wp.status == WorkPackageStatus.BLOCKED

    @pytest.mark.asyncio
    async def test_reject_decision_sets_rejected_status(self):
        wp = _wp()
        db = MagicMock()
        db.flush = AsyncMock()
        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=_mock_outcome("REJECT"))

        with patch("app.services.engineering.peer_review.get_council_session", return_value=mock_session):
            await review_work_package(db, wp)

        assert wp.status == WorkPackageStatus.REJECTED

    @pytest.mark.asyncio
    async def test_calls_council_with_engineering_review_category(self):
        wp = _wp()
        db = MagicMock()
        db.flush = AsyncMock()
        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=_mock_outcome("APPROVE"))

        with patch("app.services.engineering.peer_review.get_council_session", return_value=mock_session):
            await review_work_package(db, wp)

        _, kwargs = mock_session.run.call_args
        assert kwargs["task_category"] == "engineering_review"
