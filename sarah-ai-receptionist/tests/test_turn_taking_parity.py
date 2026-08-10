"""
Both call paths must apply semantic turn-taking, not just the demo one.

Two code paths reach the same Deepgram/Claude/ElevenLabs pipeline:

  - demo_call_manager.py  -- the browser widget a prospect evaluates Sarah on
  - call_manager.py       -- the Twilio path every real patient actually gets

`turn_detection.looks_incomplete` holds Sarah's turn for a moment when the
caller has gone quiet but their words look mid-thought ("I'd like to book
something for..."). It shipped wired into the demo path only. The phone path
answered on Deepgram's raw acoustic `speech_final`, so the call path real
patients use was the one that would cut a thinking caller off mid-sentence --
the exact "she talks over me and answers half my sentence" complaint, and
invisible in the demo that gets used to sell the product.

That asymmetry got worse when endpointing was tightened to 100ms for
multilingual mode: `speech_final` now fires on less silence, so the phone path
had less margin, not more.

These tests pin the parity itself rather than any one implementation. The two
managers are legitimately different shapes (the demo schedules a cancellable
task; the phone loop waits inline), so this asserts the shared contract: both
import the detector, both use the one shared grace constant, and the phone
loop actually gates its response on it.
"""

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services import call_manager, demo_call_manager, turn_detection


def test_the_grace_period_has_exactly_one_definition():
    """A copy per call manager is how the two paths drifted apart before:
    turn_detection owns the policy, and both managers read it from there."""
    assert turn_detection.INCOMPLETE_UTTERANCE_GRACE_SECONDS > 0

    assert call_manager.INCOMPLETE_UTTERANCE_GRACE_SECONDS is (
        turn_detection.INCOMPLETE_UTTERANCE_GRACE_SECONDS
    )
    assert demo_call_manager.INCOMPLETE_UTTERANCE_GRACE_SECONDS is (
        turn_detection.INCOMPLETE_UTTERANCE_GRACE_SECONDS
    )


def test_the_grace_period_stays_within_human_pause_range():
    """Below ~0.4s it does not cover drawing a breath, so it buys nothing;
    above ~1.2s it is audible dead air on every mid-thought turn, which is the
    sluggishness this whole mechanism exists to avoid."""
    assert 0.4 <= turn_detection.INCOMPLETE_UTTERANCE_GRACE_SECONDS <= 1.2


def test_both_call_paths_consult_the_turn_detector():
    assert call_manager.looks_incomplete is turn_detection.looks_incomplete
    assert demo_call_manager.looks_incomplete is turn_detection.looks_incomplete


def test_the_phone_path_gates_its_reply_on_the_detector():
    """The import existing is not enough -- it has to actually be consulted on
    the path between `speech_final` and generating a response."""
    listen_loop = inspect.getsource(call_manager.CallManager._listen_loop)

    assert "looks_incomplete" in listen_loop
    # The detector must be consulted *before* the turn is handed to the AI,
    # otherwise it is decorative.
    assert listen_loop.index("looks_incomplete") < listen_loop.index("_respond_now")


def test_the_phone_path_can_fold_in_resumed_speech():
    """Holding the turn is only half of it: whatever the caller says during
    the grace period has to end up in the utterance Sarah answers, or she
    replies to the fragment anyway just a beat later."""
    source = inspect.getsource(call_manager.CallManager._await_continuation)

    assert "INCOMPLETE_UTTERANCE_GRACE_SECONDS" in source
    # Must return early once the resumed speech is itself final, rather than
    # always burning the whole window.
    assert "speech_final" in source


def test_a_stream_ending_mid_grace_period_does_not_hang_the_call():
    """`next_event()` returns None exactly once when Deepgram's stream is
    gone; awaiting it again blocks on a queue nothing will refill. Consuming
    that None inside the grace-period wait must therefore latch a flag the
    listen loop checks, or a caller whose STT drops mid-sentence sits in dead
    air until the call times out."""
    continuation = inspect.getsource(call_manager.CallManager._await_continuation)
    listen_loop = inspect.getsource(call_manager.CallManager._listen_loop)

    assert "_stt_closed" in continuation
    assert "_stt_closed" in listen_loop
