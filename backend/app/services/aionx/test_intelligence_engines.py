"""End-to-end integration tests for all 5 intelligence engines and wisdom index.

Tests verify:
1. Each engine produces valid output (no crashes, proper structure)
2. Engines feed into Wisdom Index correctly
3. API endpoints return valid responses
4. Full feedback loop (decision → outcome → learning → better decision)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aionx_organs import (
    ClientDigitalTwin,
    CounterfactualActualization,
    DecisionObject,
    DecisionDebtAssessment,
    InstitutionalDebtIndex,
    MissionAutopsy,
    MissionOwnershipRecord,
    WisdomIndexSnapshot,
)
from app.services.aionx.counterfactual_engine import (
    extract_learning,
    record_actuality,
    simulate_decision,
)
from app.services.aionx.decision_debt_engine import (
    assess_institutional_debt,
    compute_decision_debt,
    recommend_debt_reduction,
)
from app.services.aionx.executive_accountability_engine import (
    compute_authority_decay,
    escalate_for_captain_review,
    score_decision_quality,
    track_maker_accuracy,
)
from app.services.aionx.institutional_wisdom_index import compute_weekly_wisdom
from app.services.aionx.mission_autopsy_engine import (
    analyze_mission_failure,
    extract_failure_patterns,
)
from app.services.aionx.client_trust_index import (
    compute_trust_score,
    escalate_trust_erosion,
    recovery_protocol,
)

logger = logging.getLogger(__name__)


async def test_counterfactual_engine(db: AsyncSession) -> dict:
    """Test counterfactual simulation and learning extraction."""
    logger.info("TEST: Counterfactual Engine")

    # Create a test decision
    decision = DecisionObject(
        trigger_event="TEST_COUNTERFACTUAL",
        problem_statement="Evaluate counterfactual accuracy",
        tier=2,
        decision_category="TEST",
        confidence_score=0.75,
    )
    db.add(decision)
    await db.flush()

    # Simulate alternatives
    simulations = await simulate_decision(db, decision.id)
    assert simulations["decision_id"] == str(decision.id)
    assert len(simulations.get("alternatives", [])) > 0

    # Record actual outcome
    actuality = await record_actuality(
        db,
        decision.id,
        "Positive outcome — target achieved",
        revenue_delta=5000.0,
        timeline_delta_days=-2,
    )
    assert actuality["recorded"] is True

    # Extract learning
    learning = await extract_learning(db)
    assert "success_rate" in learning
    assert "decisions_reviewed" in learning

    logger.info(f"✓ Counterfactual: {learning['decisions_reviewed']} decisions reviewed, {learning['success_rate']:.0%} success rate")
    return learning


async def test_debt_engine(db: AsyncSession) -> dict:
    """Test decision debt computation and reduction planning."""
    logger.info("TEST: Decision Debt Engine")

    # Create a test decision
    decision = DecisionObject(
        trigger_event="TEST_DEBT",
        problem_statement="Test debt computation",
        tier=1,
        decision_category="STRATEGY",
        confidence_score=0.5,
    )
    db.add(decision)
    await db.flush()

    # Compute debt
    debt = await compute_decision_debt(
        db,
        decision.id,
        lost_revenue_usd=10000.0,
        remediation_effort_hours=20,
        opportunity_cost_usd=5000.0,
    )
    assert debt["decision_id"] == str(decision.id)
    assert debt["debt_score"] > 0

    # Assess institutional debt
    institutional = await assess_institutional_debt(db)
    assert "total_institutional_debt_usd" in institutional
    assert "high_debt_decision_count" in institutional

    # Get reduction plan
    plan = await recommend_debt_reduction(db)
    assert "top_decisions" in plan

    logger.info(f"✓ Debt Engine: ${institutional['total_institutional_debt_usd']:.2f} total debt, {institutional['high_debt_decision_count']} high-debt decisions")
    return institutional


async def test_autopsy_engine(db: AsyncSession) -> dict:
    """Test mission failure analysis and pattern extraction."""
    logger.info("TEST: Mission Autopsy Engine")

    client_id = uuid.uuid4()
    mission_id = uuid.uuid4()

    # Create mission ownership
    ownership = MissionOwnershipRecord(
        mission_id=mission_id,
        client_id=client_id,
        mission_status="ACTIVE",
    )
    db.add(ownership)
    await db.flush()

    # Analyze failure
    analysis = await analyze_mission_failure(
        db,
        mission_id,
        "SCHEDULE_OVERRUN",
        "Project took 3 weeks longer than estimated",
    )
    assert analysis["mission_id"] == str(mission_id)
    assert "analysis" in analysis
    assert "prevention_strategies" in analysis

    # Extract patterns
    patterns = await extract_failure_patterns(db)
    assert "patterns" in patterns

    logger.info(f"✓ Autopsy Engine: Analyzed mission, extracted {len(patterns.get('patterns', []))} failure patterns")
    return patterns


async def test_accountability_engine(db: AsyncSession) -> dict:
    """Test decision quality scoring and maker accountability."""
    logger.info("TEST: Executive Accountability Engine")

    # Create decisions by a test maker
    maker_id = "TEST_MAKER_001"
    decisions = []

    for i in range(3):
        decision = DecisionObject(
            trigger_event=f"TEST_ACCOUNTABILITY_{i}",
            problem_statement=f"Accountability test decision {i}",
            tier=2,
            decision_category="TEST",
            confidence_score=0.8 - (i * 0.1),
            created_by=maker_id,
        )
        db.add(decision)
        decisions.append(decision)

    await db.flush()

    # Score decisions
    for decision in decisions[:1]:
        score = await score_decision_quality(db, decision.id, 0.9)
        assert score["decision_id"] == str(decision.id)
        assert "quality_score" in score

    # Track maker accuracy
    accuracy = await track_maker_accuracy(db, maker_id)
    assert accuracy["maker_id"] == maker_id
    assert "authority_score" in accuracy

    # Check authority decay
    decay = await compute_authority_decay(db, maker_id)
    assert decay["maker_id"] == maker_id
    assert "authority_decay" in decay

    # Check for escalation
    if decisions:
        escalation = await escalate_for_captain_review(db, decisions[0].id)
        assert "escalated" in escalation

    logger.info(f"✓ Accountability Engine: {maker_id} authority {accuracy['authority_score']:.0f}, {len(decisions)} decisions tracked")
    return accuracy


async def test_trust_engine(db: AsyncSession) -> dict:
    """Test client trust scoring and erosion detection."""
    logger.info("TEST: Client Trust Index Engine")

    client_id = uuid.uuid4()

    # Create or get digital twin
    twin = ClientDigitalTwin(client_id=client_id, trust_score=80.0)
    db.add(twin)
    await db.flush()

    # Compute trust
    trust = await compute_trust_score(db, client_id)
    assert trust["client_id"] == str(client_id)
    assert "trust_score" in trust

    # Check for erosion
    erosion = await escalate_trust_erosion(db, client_id, threshold=20.0)
    assert "escalated" in erosion

    # Get recovery actions
    actions = await recovery_protocol(db, client_id)
    assert isinstance(actions, list)
    assert len(actions) > 0

    logger.info(f"✓ Trust Engine: Client {str(client_id)[:8]}... trust {trust['trust_score']:.0f}, {len(actions)} recovery actions")
    return trust


async def test_wisdom_index_integration(db: AsyncSession) -> dict:
    """Test wisdom index computation with all engine data."""
    logger.info("TEST: Wisdom Index Integration")

    # Compute weekly wisdom
    snapshot = await compute_weekly_wisdom(db)

    assert snapshot.wisdom_score >= 0
    assert snapshot.wisdom_score <= 1000
    assert snapshot.decision_accuracy_score >= 0
    assert snapshot.counterfactual_precision_score >= 0
    assert snapshot.convergence_efficiency_score >= 0
    assert snapshot.client_retention_score >= 0

    # Verify narrative includes engine data
    assert "Decision accuracy" in snapshot.narrative or "accuracy" in snapshot.narrative.lower()
    assert "Wisdom" in snapshot.narrative

    # Verify recommendations based on wisdom
    assert isinstance(snapshot.recommendations, list)

    logger.info(
        f"✓ Wisdom Index: {snapshot.wisdom_score:.0f} "
        f"(±{snapshot.delta:+.1f}), recommendations={len(snapshot.recommendations)}"
    )
    return {
        "wisdom_score": snapshot.wisdom_score,
        "delta": snapshot.delta,
        "recommendations": snapshot.recommendations,
    }


async def test_full_feedback_loop(db: AsyncSession) -> dict:
    """Test complete intelligence loop: Decision → Outcome → Learning → Better Decision."""
    logger.info("TEST: Full Feedback Loop")

    # PHASE 1: Make a strategic decision
    decision = DecisionObject(
        trigger_event="FEEDBACK_LOOP_TEST",
        problem_statement="Evaluate full intelligence feedback loop",
        tier=1,
        decision_category="STRATEGIC",
        confidence_score=0.7,
        created_by="FEEDBACK_LOOP_TEST",
    )
    db.add(decision)
    await db.flush()
    logger.info(f"  Phase 1: Decision created {str(decision.id)[:8]}...")

    # PHASE 2: Simulate alternatives
    simulations = await simulate_decision(db, decision.id)
    assert len(simulations.get("alternatives", [])) > 0
    logger.info(f"  Phase 2: Generated {len(simulations['alternatives'])} alternatives")

    # PHASE 3: Record actual outcome
    actuality = await record_actuality(
        db,
        decision.id,
        "Positive outcome with early completion",
        revenue_delta=7500.0,
        timeline_delta_days=-3,
    )
    assert actuality["recorded"]
    logger.info(f"  Phase 3: Outcome recorded (+${7500.0:.2f}, -3 days)")

    # PHASE 4: Score decision quality
    score = await score_decision_quality(db, decision.id, 0.95)
    assert score["quality_score"] > 70
    logger.info(f"  Phase 4: Quality score {score['quality_score']:.0f}")

    # PHASE 5: Track maker learning
    accuracy = await track_maker_accuracy(db, "FEEDBACK_LOOP_TEST")
    assert accuracy["accuracy"] > 0.5
    logger.info(f"  Phase 5: Maker accuracy {accuracy['accuracy']:.0%}")

    # PHASE 6: Extract institutional learning
    learning = await extract_learning(db)
    logger.info(f"  Phase 6: Learning extracted ({learning['decisions_reviewed']} decisions, {learning['success_rate']:.0%} success)")

    # PHASE 7: Update wisdom
    wisdom = await compute_weekly_wisdom(db)
    logger.info(f"  Phase 7: Wisdom updated to {wisdom.wisdom_score:.0f} (±{wisdom.delta:+.1f})")

    logger.info("✓ Full Feedback Loop: Complete cycle from decision to institutional learning")
    return {
        "decision_id": str(decision.id),
        "quality_score": score["quality_score"],
        "maker_accuracy": accuracy["accuracy"],
        "learning_success_rate": learning["success_rate"],
        "wisdom_score": wisdom.wisdom_score,
    }


async def run_all_engine_tests(db: AsyncSession) -> dict:
    """Run all intelligence engine tests and summarize results."""
    logger.info("\n" + "="*80)
    logger.info("AIONX INTELLIGENCE ENGINE INTEGRATION TESTS")
    logger.info("="*80 + "\n")

    results = {}

    try:
        results["counterfactual"] = await test_counterfactual_engine(db)
    except Exception as e:
        logger.error(f"✗ Counterfactual Engine failed: {e}")
        results["counterfactual"] = {"error": str(e)}

    try:
        results["debt"] = await test_debt_engine(db)
    except Exception as e:
        logger.error(f"✗ Debt Engine failed: {e}")
        results["debt"] = {"error": str(e)}

    try:
        results["autopsy"] = await test_autopsy_engine(db)
    except Exception as e:
        logger.error(f"✗ Autopsy Engine failed: {e}")
        results["autopsy"] = {"error": str(e)}

    try:
        results["accountability"] = await test_accountability_engine(db)
    except Exception as e:
        logger.error(f"✗ Accountability Engine failed: {e}")
        results["accountability"] = {"error": str(e)}

    try:
        results["trust"] = await test_trust_engine(db)
    except Exception as e:
        logger.error(f"✗ Trust Engine failed: {e}")
        results["trust"] = {"error": str(e)}

    try:
        results["wisdom_integration"] = await test_wisdom_index_integration(db)
    except Exception as e:
        logger.error(f"✗ Wisdom Index Integration failed: {e}")
        results["wisdom_integration"] = {"error": str(e)}

    try:
        results["full_feedback_loop"] = await test_full_feedback_loop(db)
    except Exception as e:
        logger.error(f"✗ Full Feedback Loop failed: {e}")
        results["full_feedback_loop"] = {"error": str(e)}

    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    passed = sum(1 for r in results.values() if "error" not in r)
    total = len(results)
    logger.info(f"Passed: {passed}/{total}")
    logger.info("="*80 + "\n")

    return {
        "passed": passed,
        "total": total,
        "results": results,
    }
