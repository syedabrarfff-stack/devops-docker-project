"""
Tests for STT reconnect and TTS retry behavior.

Voice-pipeline failures used to end the call silently -- these guard the
behavior that keeps a call alive through a transient Deepgram or ElevenLabs
blip. The behavioral tests below exercise the real reconnect/retry code
paths rather than trusting that comments describe them accurately.
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.speech_to_text import (  # noqa: E402
    ConnectionClosed,
    SpeechToText,
    _MAX_RECONNECT_ATTEMPTS,
)
from app.services.text_to_speech import SynthesisFailed, TextToSpeech  # noqa: E402


# ---- STT ---------------------------------------------------------------------

def _result_message(text: str) -> str:
    return json.dumps({
        "type": "Results",
        "is_final": True,
        "speech_final": True,
        "channel": {"alternatives": [{"transcript": text}]},
    })


class _FakeDeepgramSocket:
    """A single 'connection' that yields the messages it was seeded with,
    then either raises to simulate a drop or hangs to simulate a live idle
    socket."""

    def __init__(self, messages, then="drop"):
        self._messages = list(messages)
        self._then = then
        self._i = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._i < len(self._messages):
            m = self._messages[self._i]
            self._i += 1
            return m
        if self._then == "drop":
            raise ConnectionClosed(None, None)
        if self._then == "clean_close":
            raise StopAsyncIteration
        if self._then == "hang":
            await asyncio.Future()  # simulate a live idle socket
        raise StopAsyncIteration

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_transient_disconnect_triggers_reconnect_and_call_survives():
    stt = SpeechToText()

    calls = []

    async def open_socket():
        calls.append(1)
        if len(calls) == 1:
            return _FakeDeepgramSocket([_result_message("first")], then="drop")
        return _FakeDeepgramSocket([_result_message("after-reconnect")], then="hang")

    stt._open_socket = open_socket
    stt._ws = await stt._open_socket()
    stt._listen_task = asyncio.create_task(stt._listen_loop())
    try:
        ev1 = await asyncio.wait_for(stt.next_event(), timeout=2)
        ev2 = await asyncio.wait_for(stt.next_event(), timeout=5)
        assert ev1.text == "first"
        # This is the whole point: without reconnect, ev2 would be None and
        # the call would end.
        assert ev2 is not None and ev2.text == "after-reconnect"
    finally:
        await stt.close()


@pytest.mark.asyncio
async def test_reconnect_budget_is_bounded_not_forever():
    """Ends the STT stream (returns None on next_event) after the retry budget
    is spent, so call_manager sees a clean end rather than a hang."""
    stt = SpeechToText()
    stt._ws = _FakeDeepgramSocket([], then="drop")
    attempts = []

    async def always_fails():
        attempts.append(1)
        raise ConnectionRefusedError("simulated deepgram outage")

    stt._open_socket = always_fails
    stt._listen_task = asyncio.create_task(stt._listen_loop())
    try:
        # Bumping the deadline high to prove it terminates on its own,
        # not that the test timeout truncated it.
        ev = await asyncio.wait_for(stt.next_event(), timeout=20)
        assert ev is None, "should signal end of stream after exhausted retries"
        assert len(attempts) == _MAX_RECONNECT_ATTEMPTS
    finally:
        await stt.close()


# ---- TTS ---------------------------------------------------------------------

class _FailingHTTPXStream:
    """Drop-in for httpx.AsyncClient.stream() that fails a configurable
    number of times before succeeding (or forever)."""

    def __init__(self, fail_count: int):
        self._fail_count = fail_count
        self.calls = 0

    def stream(self, method, url, **kwargs):
        self.calls += 1
        if self.calls <= self._fail_count:
            raise httpx.ConnectError("simulated network failure")
        return _OKResponseStream()


class _OKResponseStream:
    async def __aenter__(self):
        class _R:
            def raise_for_status(self_): pass

            async def aiter_bytes(self_, chunk_size):
                yield b"\x00" * chunk_size

        return _R()

    async def __aexit__(self, *args):
        return False


@pytest.mark.asyncio
async def test_transient_tts_failure_retries_and_succeeds():
    tts = TextToSpeech()
    tts._client = _FailingHTTPXStream(fail_count=1)
    chunks = [c async for c in tts.stream_synthesize("hello")]
    assert len(chunks) == 1
    assert tts._client.calls == 2  # one failure + one success


@pytest.mark.asyncio
async def test_persistent_tts_failure_raises_instead_of_silence():
    """Silence is worse than an exception: silence looks like a dropped call,
    an exception lets call_manager play the fallback message."""
    tts = TextToSpeech()
    tts._client = _FailingHTTPXStream(fail_count=99)
    with pytest.raises(SynthesisFailed):
        async for _ in tts.stream_synthesize("hello"):
            pass


@pytest.mark.asyncio
async def test_empty_input_produces_no_audio_and_no_error():
    tts = TextToSpeech()
    tts._client = _FailingHTTPXStream(fail_count=0)  # would succeed if called
    chunks = [c async for c in tts.stream_synthesize("   ")]
    assert chunks == []
    assert tts._client.calls == 0  # never even hit the network
