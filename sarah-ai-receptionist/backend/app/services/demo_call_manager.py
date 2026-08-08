"""
Browser-native demo call manager — the public "Call Sarah" widget's AI loop.

Runs the exact same Deepgram -> Claude(OpenRouter) -> ElevenLabs pipeline as
a real phone call, reusing speech_to_text.py / ai_brain.py / text_to_speech.py
unmodified, but:
  - talks raw PCM16 over a plain WebSocket instead of Twilio's mulaw/base64
    Media Streams framing -- no Twilio Voice SDK, no TwiML App, no trial-
    account restriction, because Twilio is not in this call path at all
  - uses the seeded is_demo clinic's config directly (passed in, not looked
    up per-turn) instead of a real clinic
  - never touches Postgres or S3 -- no call_log row, no recording persisted,
    no appointment actually created even if the AI emits a [BOOK:...] tag

Barge-in mirrors call_manager.py's proven approach exactly: Deepgram's
interim (non-final) transcripts drive interruption detection, the in-flight
AI/TTS task is cancelled, and the frontend is told to flush its queued audio
instantly via a control message (the browser-audio equivalent of Twilio's
"clear" event, since there's no Twilio Media Stream here to clear).
"""

import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect

from app.services.ai_brain import ActionCommand, AIBrain
from app.services.barge_in import is_real_interruption
from app.services.speech_to_text import SpeechToText
from app.services.text_to_speech import SynthesisFailed, TextToSpeech
from app.services.turn_detection import looks_incomplete

logger = logging.getLogger(__name__)

# Deepgram's own guidance for real-time linear16 streaming -- matches what
# the browser-side AudioWorklet resamples the mic to before sending.
_DEMO_STT_SAMPLE_RATE = 16000
# Raw PCM playback needs no client-side MP3/Opus decoder -- the browser just
# feeds the bytes straight into an AudioBuffer.
_DEMO_TTS_OUTPUT_FORMAT = "pcm_16000"

# Extra wait when the caller's words look mid-thought (see turn_detection.py).
# Long enough to cover drawing a breath while assembling the rest of a
# sentence, short enough that being wrong is barely perceptible.
_INCOMPLETE_UTTERANCE_GRACE_SECONDS = 0.7

# Hardcoded, not read from Postgres -- this call path is deliberately
# infra-independent (no RDS, no Redis, nothing but the running container and
# the three third-party API keys) so the demo widget can go live without
# waiting on Sarah's full production stack. Kept in sync by hand with the
# is_demo clinic seeded in migration 0005, which the real Twilio-based
# /browser-call path (voice_widget.py) still reads from the DB.
DEMO_CLINIC_CONFIG = {
    "name": "Sarah's Demo Practice — Riyadh",
    "sarah_name": "Sarah",
    "hours": "Open every day, 24 hours -- this is a live demo",
    "address": "King Fahd Road, Riyadh, Saudi Arabia",
    "services": ["cleanings", "fillings", "root canals", "crowns", "whitening", "emergency care"],
    "providers": [
        {"name": "Dr. Aslam", "specialty": "root canals and endodontics"},
        {"name": "Dr. Al-Rashid", "specialty": "general and cosmetic dentistry"},
        {"name": "Dr. Chen", "specialty": "orthodontics and pediatric dentistry"},
    ],
    "insurance_accepted": ["Bupa Arabia", "Tawuniya", "MedGulf", "AXA Gulf"],
    "emergency_instructions": "For a real dental emergency, please call your own dentist or 911.",
}


class DemoCallManager:
    def __init__(self, clinic_config: dict, session_id: str):
        self.clinic_config = clinic_config
        self.session_id = session_id
        self.stt = SpeechToText(encoding="linear16", sample_rate=_DEMO_STT_SAMPLE_RATE)
        self.ai_brain = AIBrain(clinic_config=clinic_config)
        self.tts = TextToSpeech()
        self.is_active = True
        self._speak_task: asyncio.Task | None = None
        # A turn waiting out the grace period, plus the text it will answer.
        self._turn_task: asyncio.Task | None = None
        self._pending_utterance: str = ""

    async def run(self, websocket: WebSocket) -> None:
        await self.stt.connect()
        transcript_task = asyncio.create_task(self._handle_transcripts(websocket))

        try:
            greeting = (
                f"Hi! I'm {self.clinic_config.get('sarah_name', 'Sarah')}, "
                f"{self.clinic_config.get('name', 'the practice')}'s AI receptionist. "
                "How can I help you today?"
            )
            self._speak_task = asyncio.create_task(self._speak(websocket, greeting))
            await self._safe_await(self._speak_task)

            while self.is_active:
                message = await websocket.receive()
                if message.get("type") == "websocket.disconnect":
                    break
                audio = message.get("bytes")
                if audio:
                    await self.stt.send_audio(audio)
                # Any text frame from the client is treated as "caller is done
                # talking for now" is unnecessary -- Deepgram's own endpointing
                # (speech_final) already drives turn-taking. Text frames are
                # reserved for future control messages and currently ignored.
        except WebSocketDisconnect:
            logger.info(f"Demo call {self.session_id} disconnected")
        finally:
            self.is_active = False
            transcript_task.cancel()
            try:
                await transcript_task
            except (asyncio.CancelledError, Exception):
                pass
            for task in (self._turn_task, self._speak_task):
                if task and not task.done():
                    task.cancel()
                    await self._safe_await(task)
            await self._cleanup()

    async def _handle_transcripts(self, websocket: WebSocket) -> None:
        while self.is_active:
            event = await self.stt.next_event()
            if event is None:
                break

            # Barge-in: caller started talking while Sarah is still speaking.
            if self._is_speaking() and is_real_interruption(event.text):
                await self._interrupt_speech(websocket)

            if event.speech_final and event.text.strip():
                await self._schedule_turn(websocket, event.text)

    async def _schedule_turn(self, websocket: WebSocket, text: str) -> None:
        """Decide whether to answer now or wait -- the caller may still be
        mid-thought even though they've gone quiet.

        Each new final transcript cancels any turn already waiting and
        reschedules with the combined text, so a caller who pauses partway
        ("I'd like to book something for..." <pause> "...next Tuesday") gets
        one coherent reply to the whole sentence instead of Sarah answering
        the fragment and then being interrupted by the rest of it.
        """
        self._pending_utterance = f"{self._pending_utterance} {text}".strip()
        if self._turn_task and not self._turn_task.done():
            self._turn_task.cancel()
            await self._safe_await(self._turn_task)
        delay = _INCOMPLETE_UTTERANCE_GRACE_SECONDS if looks_incomplete(self._pending_utterance) else 0.0
        self._turn_task = asyncio.create_task(self._respond_after(websocket, delay))

    async def _respond_after(self, websocket: WebSocket, delay: float) -> None:
        if delay:
            # Cancelled by _schedule_turn if the caller resumes talking, which
            # is exactly the point -- the wait only ever costs anything when
            # they had in fact finished.
            await asyncio.sleep(delay)
        utterance, self._pending_utterance = self._pending_utterance, ""
        if utterance:
            await self._respond(websocket, utterance)

    async def _respond(self, websocket: WebSocket, caller_text: str) -> None:
        await _send_json(websocket, {"type": "transcript", "role": "caller", "text": caller_text})
        self._speak_task = asyncio.create_task(self._stream_ai_response(websocket, caller_text))
        await self._safe_await(self._speak_task)

    async def _stream_ai_response(self, websocket: WebSocket, caller_text: str) -> None:
        async for kind, value in self.ai_brain.stream_response(caller_text):
            if not self.is_active:
                return
            if kind == "sentence":
                await _send_json(websocket, {"type": "transcript", "role": "sarah", "text": value})
                await self._speak(websocket, value)
            elif kind == "action" and value is not None:
                await self._handle_action(websocket, value)

    async def _speak(self, websocket: WebSocket, text: str) -> None:
        try:
            async for chunk in self.tts.stream_synthesize(text, output_format=_DEMO_TTS_OUTPUT_FORMAT):
                if not self.is_active:
                    return
                await websocket.send_bytes(chunk)
        except asyncio.CancelledError:
            raise
        except SynthesisFailed:
            await _send_json(
                websocket,
                {"type": "error", "message": "Sarah had trouble speaking that — continuing."},
            )

    def _is_speaking(self) -> bool:
        return self._speak_task is not None and not self._speak_task.done()

    async def _interrupt_speech(self, websocket: WebSocket) -> None:
        """Cancel whatever Sarah is mid-saying and tell the browser to flush
        its queued/playing audio instantly -- the browser-audio equivalent of
        call_manager.py's send_clear_event() for a real Twilio call."""
        if self._speak_task and not self._speak_task.done():
            self._speak_task.cancel()
            await self._safe_await(self._speak_task)
        await _send_json(websocket, {"type": "interrupt"})

    async def _safe_await(self, task: asyncio.Task) -> None:
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Demo call {self.session_id} task error: {e}")

    async def _handle_action(self, websocket: WebSocket, action: ActionCommand) -> None:
        """Demo mode never actually books/transfers/ends for real -- we just
        surface what the action *would have been*, which is the proof point
        (the AI genuinely decided to book, with real extracted details) that
        matters for a sales demo, without writing to any real clinic's data."""
        await _send_json(
            websocket, {"type": "action", "action": action.action, "params": action.params}
        )
        if action.action == "END":
            self.is_active = False

    async def _cleanup(self) -> None:
        await self.stt.close()
        await self.ai_brain.close()
        await self.tts.close()


async def _send_json(websocket: WebSocket, payload: dict) -> None:
    try:
        await websocket.send_json(payload)
    except Exception:
        # Socket already closing -- nothing useful to do with the failure.
        pass
