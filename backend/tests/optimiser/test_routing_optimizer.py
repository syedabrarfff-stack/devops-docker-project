"""O5-1: Tests for RoutingOptimizer."""
from __future__ import annotations

import pytest

from app.services.fabric.routing_optimizer import (
    _LATENCY_BASELINE_MS,
    _MIN_CALLS_THRESHOLD,
    _W_COST_EFF,
    _W_QUALITY,
    _W_RELIABILITY,
    _W_SPEED,
    _compute_score,
)


# ── Weight constants ──────────────────────────────────────────────────────────

def test_weights_sum_to_one():
    total = _W_RELIABILITY + _W_SPEED + _W_COST_EFF + _W_QUALITY
    assert abs(total - 1.0) < 1e-9


def test_min_calls_threshold():
    assert _MIN_CALLS_THRESHOLD == 10


# ── Score computation ─────────────────────────────────────────────────────────

def test_perfect_model_scores_one_hundred():
    score = _compute_score(
        total_calls=1000,
        successful_calls=1000,
        avg_latency_ms=_LATENCY_BASELINE_MS,   # exactly at baseline → speed = 1.0
        avg_cost_per_call=0.001,
        avg_quality=1.0,
        min_cost_per_call_across_models=0.001,  # same as this model → cost_eff = 1.0
    )
    assert score == pytest.approx(100.0, abs=0.01)


def test_zero_success_scores_low():
    score = _compute_score(
        total_calls=100,
        successful_calls=0,
        avg_latency_ms=200.0,
        avg_cost_per_call=0.01,
        avg_quality=0.0,
        min_cost_per_call_across_models=0.001,
    )
    # reliability=0, speed=min(1,500/200)=1.0, cost_eff=min(1,0.001/0.01)=0.1, quality=0
    expected = _W_RELIABILITY * 0 + _W_SPEED * 1.0 + _W_COST_EFF * 0.1 + _W_QUALITY * 0.0
    assert score == pytest.approx(expected * 100, abs=0.1)


def test_high_latency_penalises_speed():
    score_fast = _compute_score(
        total_calls=100,
        successful_calls=100,
        avg_latency_ms=100.0,    # fast
        avg_cost_per_call=0.01,
        avg_quality=0.8,
        min_cost_per_call_across_models=0.01,
    )
    score_slow = _compute_score(
        total_calls=100,
        successful_calls=100,
        avg_latency_ms=5000.0,   # slow
        avg_cost_per_call=0.01,
        avg_quality=0.8,
        min_cost_per_call_across_models=0.01,
    )
    assert score_fast > score_slow


def test_expensive_model_penalised():
    score_cheap = _compute_score(
        total_calls=100,
        successful_calls=100,
        avg_latency_ms=200.0,
        avg_cost_per_call=0.001,
        avg_quality=0.8,
        min_cost_per_call_across_models=0.001,   # this IS the cheapest
    )
    score_expensive = _compute_score(
        total_calls=100,
        successful_calls=100,
        avg_latency_ms=200.0,
        avg_cost_per_call=0.05,
        avg_quality=0.8,
        min_cost_per_call_across_models=0.001,   # some other model is cheaper
    )
    assert score_cheap > score_expensive


def test_score_capped_at_100():
    # Even with artificially high quality, score can't exceed 100.
    score = _compute_score(
        total_calls=1000,
        successful_calls=1000,
        avg_latency_ms=10.0,      # very fast → speed capped at 1.0
        avg_cost_per_call=0.0001,
        avg_quality=1.0,
        min_cost_per_call_across_models=0.0001,
    )
    assert score <= 100.0


def test_score_non_negative():
    score = _compute_score(
        total_calls=0,
        successful_calls=0,
        avg_latency_ms=0.0,
        avg_cost_per_call=0.0,
        avg_quality=0.0,
        min_cost_per_call_across_models=0.0,
    )
    assert score >= 0.0


def test_zero_latency_gives_full_speed_score():
    score = _compute_score(
        total_calls=100,
        successful_calls=100,
        avg_latency_ms=0.0,   # zero latency → speed = 1.0
        avg_cost_per_call=0.01,
        avg_quality=1.0,
        min_cost_per_call_across_models=0.01,
    )
    # reliability=1.0, speed=1.0, cost_eff=1.0, quality=1.0
    assert score == pytest.approx(100.0, abs=0.01)


def test_partial_success_rate():
    score = _compute_score(
        total_calls=100,
        successful_calls=70,    # 70% success
        avg_latency_ms=300.0,
        avg_cost_per_call=0.005,
        avg_quality=0.7,
        min_cost_per_call_across_models=0.005,
    )
    reliability = 0.70
    speed       = min(1.0, 500.0 / 300.0)
    cost_eff    = 1.0
    quality     = 0.7
    expected = (
        _W_RELIABILITY * reliability
        + _W_SPEED     * speed
        + _W_COST_EFF  * cost_eff
        + _W_QUALITY   * quality
    ) * 100
    assert score == pytest.approx(expected, abs=0.1)


# ── Async run function with mocked DB ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_optimizer_no_data_returns_zero_updates():
    from unittest.mock import AsyncMock, MagicMock
    from app.services.fabric.routing_optimizer import run_routing_optimizer

    mock_session = AsyncMock()
    empty_result = MagicMock()
    empty_result.all.return_value = []
    mock_session.execute = AsyncMock(return_value=empty_result)

    result = await run_routing_optimizer(mock_session)

    assert result["models_updated"] == 0
    assert result["models_skipped"] == 0
    assert "run_at" in result


@pytest.mark.asyncio
async def test_run_optimizer_skips_thin_data():
    """Models with < MIN_CALLS_THRESHOLD calls should be skipped."""
    import uuid
    from unittest.mock import AsyncMock, MagicMock
    from app.services.fabric.routing_optimizer import run_routing_optimizer

    model_id = uuid.uuid4()

    mock_row = MagicMock()
    mock_row.model_id = model_id
    mock_row.total_calls = 5                 # below threshold of 10
    mock_row.successful_calls = 4
    mock_row.avg_latency_ms = 200.0
    mock_row.total_cost_usd = 0.005
    mock_row.avg_quality = 0.8

    agg_result = MagicMock()
    agg_result.all.return_value = [mock_row]

    commit_result = MagicMock()

    call_count = 0
    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        return agg_result if call_count == 1 else commit_result

    mock_session = AsyncMock()
    mock_session.execute = mock_execute
    mock_session.commit = AsyncMock()

    result = await run_routing_optimizer(mock_session)

    assert result["models_skipped"] == 1
    assert result["models_updated"] == 0
