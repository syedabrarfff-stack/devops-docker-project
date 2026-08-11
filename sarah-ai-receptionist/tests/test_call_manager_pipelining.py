"""
Generating sentence N+1 must overlap with speaking sentence N, not follow it.

_stream_ai_response used to await _speak_sentence directly inside the loop
reading the AI's token stream, which paused that read for as long as TTS took
to synthesize and send the previous sentence. For any multi-sentence reply --
the common case, since Sarah's style guide asks for 1-3 sentences -- the two
costs stacked per sentence instead of overlapping, and calls got progressively
slower the more Sarah had to say.

The fix decouples the two onto separate tasks joined by a one-slot queue, so
the AI keeps generating while TTS is still working on the previous sentence.
These tests assert the overlap actually happens by timing it, not just that
the final transcript still comes out right (that part was never broken -- the
full pytest suite already covers it and passed unmodified).
"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.call_manager import CallManager

_GEN_DELAY = 0.15
_SPEAK_DELAY = 0.15
_N_SENTENCES = 3


class _SlowBrain:
    """Emits N sentences, each after a fixed generation delay -- standing in
    for OpenRouter token-stream latency."""

    def __init__(self, n: int = _N_SENTENCES, gen_delay: float = _GEN_DELAY):
        self.n = n
        self.gen_delay = gen_delay

    async def stream_response(self, caller_text=None):
        for i in range(self.n):
            await asyncio.sleep(self.gen_delay)
            yield ("sentence", f"sentence {i}")
        yield ("action", None)


def _make_manager(brain) -> CallManager:
    manager = CallManager.__new__(CallManager)
    manager.call_sid = "CAtest"
    manager.is_active = True
    manager.ai_brain = brain
    manager.pending_action = None
    manager.call_log = []
    manager.fulfillment_actions = []
    manager._latencies_ms = []

    async def _speak_sentence(text):
        await asyncio.sleep(_SPEAK_DELAY)

    manager._speak_sentence = _speak_sentence
    manager._log = lambda role, text: None
    manager._handle_transfer = None
    return manager


@pytest.mark.asyncio
async def test_generation_and_speaking_overlap_instead_of_stacking():
    """N sentences, each costing gen_delay to generate and speak_delay to
    speak. Stacked (the bug), total time is N * (gen_delay + speak_delay).
    Pipelined (the fix), total time is close to gen_delay + N * speak_delay --
    only the very first sentence's generation is on the critical path, because
    the queue lets generation of sentence i+1 run while sentence i is being
    spoken."""
    manager = _make_manager(_SlowBrain())

    loop = asyncio.get_running_loop()
    started = loop.time()
    await manager._stream_ai_response("hello")
    elapsed = loop.time() - started

    stacked = _N_SENTENCES * (_GEN_DELAY + _SPEAK_DELAY)
    pipelined = _GEN_DELAY + _N_SENTENCES * _SPEAK_DELAY

    assert elapsed < (stacked + pipelined) / 2, (
        f"elapsed={elapsed:.2f}s is closer to the stacked cost ({stacked:.2f}s) "
        f"than the pipelined one ({pipelined:.2f}s) -- generation and speaking "
        f"are not actually overlapping"
    )


@pytest.mark.asyncio
async def test_all_sentences_are_still_spoken_in_order():
    """Pipelining must not drop or reorder anything -- only change when the
    work happens, not what happens."""
    spoken: list[str] = []
    manager = _make_manager(_SlowBrain(n=4, gen_delay=0.02))

    async def _speak_sentence(text):
        spoken.append(text)

    manager._speak_sentence = _speak_sentence

    await manager._stream_ai_response("hello")

    assert spoken == ["sentence 0", "sentence 1", "sentence 2", "sentence 3"]


@pytest.mark.asyncio
async def test_barge_in_cancellation_stops_the_ai_stream_too():
    """Cancelling the outer task (a real barge-in) must cancel the producer
    reading OpenRouter as well. Without that, a caller interrupting Sarah
    would leave her still generating -- and paying for -- a reply nobody is
    ever going to hear."""
    producer_cancelled = asyncio.Event()

    class _NeverEndingBrain:
        async def stream_response(self, caller_text=None):
            try:
                yield ("sentence", "first")
                await asyncio.sleep(3600)
                yield ("sentence", "unreachable")
            except asyncio.CancelledError:
                producer_cancelled.set()
                raise

    manager = _make_manager(_NeverEndingBrain())

    task = asyncio.create_task(manager._stream_ai_response("hello"))
    await asyncio.sleep(0.05)  # let it consume "first" and start waiting
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert producer_cancelled.is_set()
