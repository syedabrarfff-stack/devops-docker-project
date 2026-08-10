"""
onboard_clinic() defaults country="SA" and auto_buy_twilio_number=True --
without a guard, onboarding a real Saudi clinic with no explicit
existing_twilio_number would silently attempt to auto-buy a Saudi-local
Twilio number, which requires a pre-approved Regulatory Bundle Twilio
onboarding cannot obtain on its own. _sa_autobuy_skip_reason is the pure
decision extracted from that branch so it's testable without a live
Twilio account or a database.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.routes.admin import _sa_autobuy_skip_reason


def test_saudi_autobuy_is_skipped_with_a_warning():
    reason = _sa_autobuy_skip_reason(auto_buy_twilio_number=True, country="SA")
    assert reason is not None
    assert "Regulatory Bundle" in reason
    assert "existing_twilio_number" in reason


def test_saudi_country_code_is_case_insensitive():
    assert _sa_autobuy_skip_reason(auto_buy_twilio_number=True, country="sa") is not None


def test_non_saudi_country_proceeds_normally():
    assert _sa_autobuy_skip_reason(auto_buy_twilio_number=True, country="US") is None
    assert _sa_autobuy_skip_reason(auto_buy_twilio_number=True, country="GB") is None


def test_saudi_country_with_autobuy_disabled_has_nothing_to_skip():
    """auto_buy_twilio_number=False already means 'don't buy anything' --
    the SA guard only matters when a purchase would otherwise be attempted."""
    assert _sa_autobuy_skip_reason(auto_buy_twilio_number=False, country="SA") is None
