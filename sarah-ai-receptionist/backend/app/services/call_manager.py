"""
Call Manager — orchestrates the complete call flow with streaming + barge-in.

Flow: Twilio audio -> Deepgram STT (event-driven) -> Claude (sentence-streamed)
      -> ElevenLabs (streamed) -> Twilio audio, with instant interruption support.

Each active phone call gets its own CallManager instance, torn down at call end.
"""

import asyncio
import json
import base64
import logging
import time
from datetime import datetime, timezone

from app.services.ai_brain import AIBrain, ActionCommand
from app.services.speech_to_text import SpeechToText, TranscriptEvent
from app.services.text_to_speech import TextToSpeech, audio_to_twilio_payload
from app.services.barge_in import send_clear_event, is_real_interruption

logger = logging.getLogger(__name__)

SILENCE_PROMPT_SECONDS = 30.0


class CallManager:
    def __init__(self, call_sid: str, stream_sid: str, clinic_config: dict | None = None):
        self.call_sid = call_sid
        self.stream_sid = stream_sid
        self.ai_brain = AIBrain(clinic_config)
        self.stt = SpeechToText()
        self.tts = TextToSpeech()
        self.twilio_ws = None
        self.is_active = False
        self.call_start = datetime.now(timezone.utc)
        self.call_log: list[dict] = []
        self.pending_action: ActionCommand | None = None

        self._speak_task: asyncio.Task | None = None
        self._utterance_buffer: str = ""
        self._latencies_ms: list[float] = []

    async def start(self, twilio_ws):
        self.twilio_ws = twilio_ws
        self.is_active = True

        await self.stt.connect()

        greeting = (
            f"Hi, thank you for calling {self.ai_brain.clinic_config['name']}! "
            f"This is {self.ai_brain.clinic_config.get('sarah_name', 'Sarah')}, how can I help you today?"
        )
        self._speak_task = asyncio.create_task(self._speak_text(greeting))
        self._log("assistant", greeting)

        await self._listen_loop()

    async def _listen_loop(self):
        """Main event loop: consumes Deepgram transcript events, handles barge-in and turn-taking."""
        while self.is_active:
            try:
                event: TranscriptEvent | None = await asyncio.wait_for(
                    self.stt.next_event(), timeout=SILENCE_PROMPT_SECONDS
                )
            except asyncio.TimeoutError:
                if self.is_active and not self._is_speaking():
                    prompt = "Are you still there? I'm happy to help if you have any questions."
                    self._speak_task = asyncio.create_task(self._speak_text(prompt))
                    await self._safe_await(self._speak_task)
                    self._log("assistant", prompt)
                continue

            if event is None:
                break  # Deepgram connection closed

            # Barge-in: caller started talking while Sarah is speaking
            if self._is_speaking() and is_real_interruption(event.text):
                await self._interrupt_speech()

            if event.is_final:
                self._utterance_buffer = (self._utterance_buffer + " " + event.text).strip()

            if event.speech_final and self._utterance_buffer:
                transcript = self._utterance_buffer
                self._utterance_buffer = ""
                self._log("caller", transcript)
                logger.info(f"[{self.call_sid}] Caller: {transcript}")

                if self.pending_action and self.pending_action.action == "TRANSFER":
                    break
                if self.pending_action and self.pending_action.action == "END":
                    break

                await self._respond_now(transcript)

                if self.pending_action and self.pending_action.action == "TRANSFER":
                    break
                if self.pending_action and self.pending_action.action == "END":
                    break

    async def _respond_now(self, caller_text: str):
        """Wait for any in-flight speech to finish, then stream a fresh AI response."""
        if self._speak_task:
            await self._safe_await(self._speak_task)
        self._speak_task = asyncio.create_task(self._stream_ai_response(caller_text))
        await self._safe_await(self._speak_task)

    async def _stream_ai_response(self, caller_text: str):
        """Streams sentence chunks from the AI brain straight into TTS, tracking latency."""
        t0 = time.monotonic()
        first_token_ms = None
        spoken_parts: list[str] = []
        action: ActionCommand | None = None

        try:
            async for kind, payload in self.ai_brain.stream_response(caller_text):
                if kind == "sentence":
                    if first_token_ms is None:
                        first_token_ms = (time.monotonic() - t0) * 1000
                    spoken_parts.append(payload)
                    await self._speak_sentence(payload)
                elif kind == "action":
                    action = payload
        except asyncio.CancelledError:
            raise
        finally:
            elapsed_ms = (time.monotonic() - t0) * 1000
            self._latencies_ms.append(elapsed_ms)

        full_text = " ".join(spoken_parts).strip()
        if full_text:
            self._log("assistant", full_text)
            logger.info(f"[{self.call_sid}] Sarah: {full_text}")

        self.pending_action = action
        if action:
            logger.info(f"[{self.call_sid}] Action: {action.action} {action.params}")
            if action.action == "TRANSFER":
                await self._speak_sentence("Let me connect you with our office manager. One moment please.")

    async def _speak_text(self, text: str):
        """Speak a single fixed string (used for greeting / silence prompts). Caller logs it."""
        await self._speak_sentence(text)

    async def _speak_sentence(self, text: str):
        if not text.strip() or not self.twilio_ws:
            return
        try:
            async for audio_chunk in self.tts.stream_synthesize(text):
                payload = audio_to_twilio_payload(audio_chunk)
                media_message = json.dumps({
                    "event": "media",
                    "streamSid": self.stream_sid,
                    "media": {"payload": payload},
                })
                await self.twilio_ws.send_text(media_message)

            mark_message = json.dumps({
                "event": "mark",
                "streamSid": self.stream_sid,
                "mark": {"name": f"speech_{len(self.call_log)}"},
            })
            await self.twilio_ws.send_text(mark_message)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Speak error: {e}")

    def _is_speaking(self) -> bool:
        return self._speak_task is not None and not self._speak_task.done()

    async def _interrupt_speech(self):
        """Cancel in-flight speech and flush Twilio's playback buffer instantly."""
        if self._speak_task and not self._speak_task.done():
            self._speak_task.cancel()
            await self._safe_await(self._speak_task)
        if self.twilio_ws:
            await send_clear_event(self.twilio_ws, self.stream_sid)

    async def _safe_await(self, task: asyncio.Task):
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Task error: {e}")

    async def handle_twilio_message(self, message: str):
        try:
            data = json.loads(message)
            event = data.get("event")

            if event == "media":
                payload = data["media"]["payload"]
                audio_bytes = base64.b64decode(payload)
                await self.stt.send_audio(audio_bytes)
            elif event == "start":
                logger.info(f"Call stream started: {data.get('start', {}).get('callSid')}")
            elif event == "stop":
                logger.info("Call stream stopped")
                self.is_active = False
            elif event == "mark":
                logger.debug(f"Mark event: {data.get('mark', {}).get('name')}")
        except Exception as e:
            logger.error(f"Error handling Twilio message: {e}")

    def _log(self, role: str, content: str):
        self.call_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "content": content,
        })

    async def end_call(self) -> dict:
        self.is_active = False
        if self._speak_task and not self._speak_task.done():
            self._speak_task.cancel()
            await self._safe_await(self._speak_task)

        await self.stt.close()
        await self.tts.close()
        await self.ai_brain.close()

        duration = (datetime.now(timezone.utc) - self.call_start).total_seconds()
        avg_latency = sum(self._latencies_ms) / len(self._latencies_ms) if self._latencies_ms else None

        logger.info(
            f"Call {self.call_sid} ended. Duration: {duration:.0f}s, "
            f"Exchanges: {len(self.call_log)}, Avg latency: {avg_latency}"
        )

        return {
            "call_sid": self.call_sid,
            "duration_seconds": duration,
            "transcript": self.call_log,
            "outcome": self.pending_action.action if self.pending_action else "completed",
            "avg_response_ms": avg_latency,
            "action_params": self.pending_action.params if self.pending_action else {},
        }
