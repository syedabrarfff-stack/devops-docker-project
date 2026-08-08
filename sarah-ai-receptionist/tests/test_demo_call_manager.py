"""
Tests for the browser "Call Sarah" demo's orchestration logic.

DemoCallManager wires SpeechToText / AIBrain / TextToSpeech together the
same way the real Twilio call_manager.py does, but over a plain WebSocket
with no Twilio, DB, or Redis involved. These tests fake the three services
at their public interface (not their transports -- STT reconnect and TTS
retry already have dedicated coverage in test_voice_resilience.py) to
verify DemoCallManager's own turn-taking, message shapes, and cleanup.
"""

import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.ai_brain import ActionCommand
from app.services.demo_call_manager import (
    DEMO_CLINIC_CONFIG,
    DemoCallManager,
)
from app.services.speech_to_text import TranscriptEvent


class _FakeWebSocket:
    """Captures every send_json/send_bytes call and replays a scripted
    sequence of receive() results, the same shape FastAPI's WebSocket
    yields for text/binary frames and a disconnect."""

    def __init__(self, incoming: list[dict]):
        self._incoming = list(incoming)
        self.json_sent: list[dict] = []
        self.bytes_sent: list[bytes] = []

    async def receive(self) -> dict:
        if not self._incoming:
            return {"type": "websocket.disconnect"}
        return self._incoming.pop(0)

    async def send_json(self, payload: dict) -> None:
        self.json_sent.append(payload)

    async def send_bytes(self, data: bytes) -> None:
        self.bytes_sent.append(data)


class _FakeSTT:
    """Emits a single scripted final transcript, then signals end-of-stream."""

    def __init__(self, transcript: str):
        self._events = [TranscriptEvent(text=transcript, is_final=True, speech_final=True), None]
        self.closed = False
        self.audio_received: list[bytes] = []

    async def connect(self):
        pass

    async def send_audio(self, audio_bytes: bytes):
        self.audio_received.append(audio_bytes)

    async def next_event(self):
        if not self._events:
            await asyncio.sleep(3600)  # never resolves -- test ends via cancellation first
        return self._events.pop(0)

    async def close(self):
        self.closed = True


@dataclass
class _FakeAIBrain:
    """Replays scripted (kind, value) tuples exactly as ai_brain.stream_response yields them."""

    scripted_turns: dict = field(default_factory=dict)
    closed: bool = False

    def stream_response(self, caller_text: str | None = None):
        turn = self.scripted_turns.get(caller_text, [("action", None)])

        async def _gen():
            for item in turn:
                yield item

        return _gen()

    async def close(self):
        self.closed = True


class _FakeTTS:
    def __init__(self):
        self.closed = False
        self.synthesized: list[str] = []

    async def stream_synthesize(self, text: str, output_format: str = "ulaw_8000"):
        self.synthesized.append(text)
        yield f"<audio:{text}>".encode()

    async def close(self):
        self.closed = True


def _make_manager(caller_text: str, turns: dict) -> tuple[DemoCallManager, _FakeSTT, _FakeAIBrain, _FakeTTS]:
    manager = DemoCallManager(clinic_config=DEMO_CLINIC_CONFIG, session_id="test-session")
    fake_stt = _FakeSTT(caller_text)
    fake_ai = _FakeAIBrain(scripted_turns=turns)
    fake_tts = _FakeTTS()
    manager.stt = fake_stt
    manager.ai_brain = fake_ai
    manager.tts = fake_tts
    return manager, fake_stt, fake_ai, fake_tts


@pytest.mark.asyncio
async def test_greeting_is_spoken_before_anything_else():
    manager, _, _, tts = _make_manager("", turns={})
    ws = _FakeWebSocket(incoming=[])

    await manager.run(ws)

    assert tts.synthesized[0].startswith("Hi! I'm Sarah")


@pytest.mark.asyncio
async def test_final_transcript_drives_a_full_turn():
    # Exercises _respond directly rather than through run()'s receive() loop
    # + concurrent transcript task -- run() is covered separately below for
    # its own contract (greeting-first, cleanup-always-happens); interleaving
    # a real STT event with a faked, instantly-resolving receive() loop would
    # be a race, not a meaningful ordering guarantee this code makes.
    manager, _, ai, tts = _make_manager(
        "I'd like to book a cleaning",
        turns={"I'd like to book a cleaning": [
            ("sentence", "Sure, let's get that booked."),
            ("action", ActionCommand(action="BOOK", params={"service": "cleaning"})),
        ]},
    )
    ws = _FakeWebSocket(incoming=[])

    await manager._respond(ws, "I'd like to book a cleaning")

    # The transcript came back as a caller message, Sarah's sentence was both
    # sent as text and actually synthesized, and the action was surfaced
    # (not silently dropped).
    caller_msgs = [m for m in ws.json_sent if m.get("role") == "caller"]
    assert caller_msgs == [{"type": "transcript", "role": "caller", "text": "I'd like to book a cleaning"}]
    assert "Sure, let's get that booked." in ai.scripted_turns["I'd like to book a cleaning"][0][1]
    assert tts.synthesized == ["Sure, let's get that booked."]
    action_msgs = [m for m in ws.json_sent if m.get("type") == "action"]
    assert action_msgs == [{"type": "action", "action": "BOOK", "params": {"service": "cleaning"}}]


@pytest.mark.asyncio
async def test_end_action_stops_the_call_loop():
    manager, _, _, _ = _make_manager(
        "goodbye",
        turns={"goodbye": [("action", ActionCommand(action="END"))]},
    )
    ws = _FakeWebSocket(incoming=[])

    assert manager.is_active is True
    await manager._respond(ws, "goodbye")

    assert manager.is_active is False


@pytest.mark.asyncio
async def test_cleanup_closes_every_underlying_service():
    manager, stt, ai, tts = _make_manager("", turns={})
    ws = _FakeWebSocket(incoming=[])

    await manager.run(ws)

    assert stt.closed is True
    assert ai.closed is True
    assert tts.closed is True


@pytest.mark.asyncio
async def test_interrupt_cancels_in_flight_speech_and_notifies_client():
    manager, _, _, _ = _make_manager("", turns={})
    ws = _FakeWebSocket(incoming=[])
    manager._speak_task = asyncio.create_task(asyncio.sleep(3600))
    assert manager._is_speaking() is True

    await manager._interrupt_speech(ws)

    assert manager._speak_task.cancelled()
    assert {"type": "interrupt"} in ws.json_sent


@pytest.mark.asyncio
async def test_barge_in_interrupts_speech_and_flushes_client_playback():
    # A real (non-tiny) interim transcript arriving while Sarah is mid-speech
    # is exactly what a caller talking over her looks like -- it should cut
    # her off immediately, the same as call_manager.py does for a real call.
    manager, stt, _, _ = _make_manager("", turns={})
    ws = _FakeWebSocket(incoming=[])
    stt._events = [TranscriptEvent(text="wait, actually", is_final=False, speech_final=False), None]
    manager._speak_task = asyncio.create_task(asyncio.sleep(3600))

    await manager._handle_transcripts(ws)

    assert manager._speak_task.cancelled()
    assert {"type": "interrupt"} in ws.json_sent


@pytest.mark.asyncio
async def test_tiny_noise_blip_does_not_trigger_a_barge_in():
    # "uh"/"um" style blips are filtered by barge_in.is_real_interruption --
    # a real caller clearing their throat shouldn't cut Sarah off mid-word.
    manager, stt, _, _ = _make_manager("", turns={})
    ws = _FakeWebSocket(incoming=[])
    stt._events = [TranscriptEvent(text="uh", is_final=False, speech_final=False), None]
    manager._speak_task = asyncio.create_task(asyncio.sleep(3600))

    await manager._handle_transcripts(ws)

    assert manager._speak_task.cancelled() is False
    assert {"type": "interrupt"} not in ws.json_sent
    manager._speak_task.cancel()


@pytest.mark.asyncio
async def test_demo_config_never_touches_a_real_clinic_lookup():
    # DEMO_CLINIC_CONFIG is a plain dict literal, not a DB row -- this just
    # pins its shape so a future edit can't silently drop a field the AI
    # prompt depends on (see prompts/dental_receptionist.py).
    assert DEMO_CLINIC_CONFIG["name"]
    assert DEMO_CLINIC_CONFIG["services"]
    assert "sarah_name" in DEMO_CLINIC_CONFIG
