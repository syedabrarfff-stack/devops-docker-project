"""
Behavioural coverage for the Twilio call path's turn-taking.

test_turn_taking_parity.py pins that the phone path is *wired* to the semantic
turn detector. This file drives CallManager's real listen loop to prove what
the caller actually experiences: a sentence delivered in two pieces around a
pause gets ONE reply, to the whole sentence -- not a reply to the first
fragment with the rest talked over.

The three external services are faked at their public interface (their
transports have dedicated coverage in test_voice_resilience.py). The loop
under test is the genuine article.
"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.call_manager import CallManager
from app.services.speech_to_text import TranscriptEvent


def _final(text: str, speech_final: bool = True) -> TranscriptEvent:
    return TranscriptEvent(text=text, is_final=True, speech_final=speech_final)


class _ScriptedSTT:
    """Replays scripted transcript events, optionally pausing before one to
    simulate the caller thinking mid-sentence. Blocks forever once exhausted,
    the way a live stream with a silent caller does."""

    def __init__(self, script: list[tuple[float, TranscriptEvent | None]]):
        self._script = list(script)

    async def next_event(self):
        if not self._script:
            await asyncio.sleep(3600)  # silent line; the test ends the loop
        delay, event = self._script.pop(0)
        if delay:
            await asyncio.sleep(delay)
        return event


class _RecordingBrain:
    """Records exactly what text each turn was asked to answer."""

    def __init__(self):
        self.turns: list[str] = []

    async def stream_response(self, caller_text=None):
        self.turns.append(caller_text)
        yield ("sentence", "Sure, I can help with that.")
        yield ("action", None)


def _make_manager(script) -> tuple[CallManager, _RecordingBrain]:
    manager = CallManager.__new__(CallManager)  # bypass __init__'s real clients
    manager.call_sid = "CAtest"
    manager.is_active = True
    manager.stt = _ScriptedSTT(script)
    brain = _RecordingBrain()
    manager.ai_brain = brain
    manager._utterance_buffer = ""
    manager._stt_closed = False
    manager._speak_task = None
    manager.pending_action = None
    manager.call_log = []
    manager.fulfillment_actions = []
    manager._latencies_ms = []
    manager.clinic_config = {}
    manager._clinic_id = None
    manager.caller_phone = None

    async def _speak_sentence(text):
        return None

    async def _is_speaking():
        return False

    manager._speak_sentence = _speak_sentence
    manager._is_speaking = lambda: False
    return manager, brain


@pytest.mark.asyncio
async def test_a_caller_who_pauses_mid_sentence_gets_one_reply_to_the_whole_thing():
    """The regression this exists for: "I'd like to book a cleaning for"
    <pause> "next Tuesday afternoon" must produce a single turn answering the
    complete sentence. Answering the fragment is what made Sarah reply about
    the wrong thing and then speak over the caller finishing."""
    manager, brain = _make_manager(
        [
            (0.0, _final("I'd like to book a cleaning for")),
            (0.15, _final("next Tuesday afternoon.")),
            (0.0, None),  # stream ends -> loop exits
        ]
    )

    await asyncio.wait_for(manager._listen_loop(), timeout=5)

    assert brain.turns == ["I'd like to book a cleaning for next Tuesday afternoon."]


@pytest.mark.asyncio
async def test_a_complete_sentence_is_answered_without_waiting():
    """The grace period must cost nothing on the common case. A finished
    sentence is answered immediately -- if this regresses, every single turn
    of every call gets slower, which is the failure mode that made Sarah feel
    sluggish in the first place."""
    manager, brain = _make_manager(
        [
            (0.0, _final("My tooth really hurts.")),
            (0.0, None),
        ]
    )

    loop = asyncio.get_running_loop()
    started = loop.time()
    await asyncio.wait_for(manager._listen_loop(), timeout=5)
    elapsed = loop.time() - started

    assert brain.turns == ["My tooth really hurts."]
    assert elapsed < 0.3, f"complete sentence waited {elapsed:.2f}s; should be immediate"


@pytest.mark.asyncio
async def test_a_caller_who_trails_off_and_stops_is_still_answered():
    """Holding the turn must be bounded. A caller who genuinely stops on a
    dangling word ("I wanted to ask about...") and never resumes still gets a
    reply after the grace period -- silence must never strand them."""
    manager, brain = _make_manager(
        [
            (0.0, _final("I wanted to ask about")),
            # nothing follows; the grace period must expire and release the turn
        ]
    )

    task = asyncio.create_task(manager._listen_loop())
    await asyncio.sleep(1.5)
    manager.is_active = False
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert brain.turns == ["I wanted to ask about"]


@pytest.mark.asyncio
async def test_the_stream_ending_during_the_grace_period_ends_the_call_cleanly():
    """next_event() yields None exactly once when Deepgram is gone. If that
    None is swallowed by the grace-period wait without latching, the loop
    awaits a queue nothing will refill and the caller sits in dead air until
    the call times out."""
    manager, brain = _make_manager(
        [
            (0.0, _final("I need an appointment for")),
            (0.05, None),  # stream dies while we are holding the turn
        ]
    )

    await asyncio.wait_for(manager._listen_loop(), timeout=5)

    assert manager._stt_closed is True
    assert brain.turns == ["I need an appointment for"]
