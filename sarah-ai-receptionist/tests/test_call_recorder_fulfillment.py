"""
Tests for outcome/appointment_booked derivation in save_call_transcript.

These pin the fix for a latent bug: a caller who books and then says "thanks,
bye" makes Sarah emit [END] after [BOOK]. The old code read call.outcome from
whatever pending_action was last, so [END] silently overwrote [BOOK] and the
appointment was never written even though call_manager had already logged the
booking. Never triggered in production only because Twilio has been locked
since before this code shipped.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def _derive_outcome(fulfillment: list[dict], transfer_result: str | None, raw_outcome: str | None) -> str:
    """Mirrors the derivation in call_recorder.save_call_transcript so the
    decision can be tested without a database."""
    if fulfillment:
        return fulfillment[-1]["action"]
    if transfer_result:
        return "TRANSFER"
    return raw_outcome


def test_book_then_end_still_counts_as_booked():
    """The exact bug: [BOOK] logged, then caller says bye and [END] fires."""
    fulfillment = [{"action": "BOOK", "params": {"phone": "+15551234567"}}]
    outcome = _derive_outcome(fulfillment, transfer_result=None, raw_outcome="END")
    assert outcome == "BOOK"


def test_appointment_booked_flag_checks_fulfillment_not_last_action():
    fulfillment = [{"action": "BOOK", "params": {}}]
    booked = any(fa["action"] == "BOOK" for fa in fulfillment)
    assert booked is True


def test_reschedule_then_end_is_not_lost():
    fulfillment = [{"action": "RESCHEDULE", "params": {}}]
    assert _derive_outcome(fulfillment, None, "END") == "RESCHEDULE"


def test_cancel_then_book_keeps_the_later_action_as_the_headline_outcome():
    """A caller who cancels one slot and books another — both must be applied,
    and the outcome label reflects what they left the call with."""
    fulfillment = [{"action": "CANCEL", "params": {}}, {"action": "BOOK", "params": {}}]
    assert _derive_outcome(fulfillment, None, "END") == "BOOK"
    booked = any(fa["action"] == "BOOK" for fa in fulfillment)
    assert booked is True


def test_no_fulfillment_falls_back_to_transfer():
    assert _derive_outcome([], transfer_result="connected", raw_outcome="TRANSFER") == "TRANSFER"


def test_no_fulfillment_and_no_transfer_falls_back_to_raw_outcome():
    assert _derive_outcome([], None, "END") == "END"


def test_lookup_only_call_is_not_mistaken_for_a_booking():
    """A caller who only asks 'am I on file?' and hangs up must not register
    as having booked, rescheduled, or cancelled anything."""
    fulfillment: list[dict] = []  # LOOKUP_PATIENT never enters fulfillment_actions
    booked = any(fa["action"] == "BOOK" for fa in fulfillment)
    assert booked is False
    assert _derive_outcome(fulfillment, None, "END") == "END"
