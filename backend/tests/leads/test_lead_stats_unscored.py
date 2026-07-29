"""lead_stats() previously had no way to tell "every lead already scored" apart
from "the scoring engine is broken" — the frontend's "Score All (50)" button
showed the total lead count regardless of how many actually needed scoring,
so clicking it against an already-fully-scored pipeline did nothing (scored: 0)
with no explanation, and repeated confused clicks tripped the endpoint's rate
limit. This test locks in the new `unscored` field lead_stats() now returns.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.leads.engine import lead_stats


@pytest.mark.asyncio
async def test_lead_stats_includes_unscored_count():
    db = MagicMock()
    # Call order in lead_stats(): total, qualified, high_score, outreach_eligible,
    # contacted, unscored, avg_score, then one count per status in the fixed list.
    scalar_values = [
        50,   # total
        0,    # qualified
        0,    # high_score
        0,    # outreach_eligible
        0,    # contacted
        3,    # unscored
        25.9, # avg_score
        50, 0, 0, 0, 0, 0, 0,  # by_status: NEW, CONTACTED, REPLIED, DEMO, PROPOSAL, WON, LOST
    ]
    db.scalar = AsyncMock(side_effect=scalar_values)

    stats = await lead_stats(db)

    assert stats["total"] == 50
    assert stats["unscored"] == 3
    assert stats["avg_score"] == 25.9


@pytest.mark.asyncio
async def test_lead_stats_unscored_zero_when_everything_already_scored():
    db = MagicMock()
    scalar_values = [50, 0, 0, 0, 0, 0, 25.9, 50, 0, 0, 0, 0, 0, 0]
    db.scalar = AsyncMock(side_effect=scalar_values)

    stats = await lead_stats(db)

    assert stats["unscored"] == 0
