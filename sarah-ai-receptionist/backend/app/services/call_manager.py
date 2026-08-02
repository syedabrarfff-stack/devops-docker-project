"""
Call Manager — orchestrates the complete call flow with streaming + barge-in.

Flow: Twilio audio -> Deepgram STT (event-driven) -> Claude (sentence-streamed)
      -> ElevenLabs (streamed) -> Twilio audio, with instant interruption support.

Each active phone call gets its own CallManager instance, torn down at call end.
"""

import asyncio
import base64
import json
import logging
import time
from datetime import datetime, timezone

from app.services.ai_brain import ActionCommand, AIBrain
from app.services.barge_in import is_real_interruption, send_clear_event
from app.services.call_recorder import upload_recording_to_s3
from app.services.speech_to_text import SpeechToText, TranscriptEvent
from app.services.text_to_speech import TextToSpeech, audio_to_twilio_payload
from app.services.transfer_service import (
    UNAVAILABLE_MESSAGE,
    TransferPlan,
    plan_transfer,
    redirect_call_to_human,
)

logger = logging.getLogger(__name__)

SILENCE_PROMPT_SECONDS = 30.0

# Upper bound on waiting for Twilio to confirm the handoff line finished
# playing. Exceeding it means a mark was lost, not that audio is still going —
# transferring late is better than stranding the caller with Sarah.
PLAYBACK_CONFIRM_TIMEOUT = 10.0


class CallManager:
    def __init__(self, call_sid: str, stream_sid: str, clinic_config: dict | None = None):
        self.call_sid = call_sid
        self.stream_sid = stream_sid
        # Kept separate from ai_brain.clinic_config, which substitutes defaults
        # for an unrecognised number — routing must never fall back to a
        # sample clinic's numbers.
        self.clinic_config = clinic_config or {}
        self.ai_brain = AIBrain(clinic_config)
        self.stt = SpeechToText()
        self.tts = TextToSpeech()
        self.twilio_ws = None
        self.is_active = False
        self.call_start = datetime.now(timezone.utc)
        self.call_log: list[dict] = []
        self.pending_action: ActionCommand | None = None
        self._clinic_id = (clinic_config or {}).get("_clinic_id")

        self._speak_task: asyncio.Task | None = None
        self._utterance_buffer: str = ""
        # Twilio echoes a mark back once the audio before it has actually been
        # played to the caller. Handing the call to a human discards whatever is
        # still buffered, so the transfer path waits on these.
        self._pending_marks: dict[str, asyncio.Event] = {}
        self._mark_counter = 0
        self.transfer_plan: TransferPlan | None = None
        self._latencies_ms: list[float] = []
        # Raw mulaw/8kHz bytes, both directions, appended in real-time arrival
        # order — a simple but faithful single-track recording. (Proper
        # duplex would multiplex two timestamped tracks; this captures full
        # audio content, which is what compliance/QA review actually needs.)
        self._recorded_audio: list[bytes] = []

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
                await self._handle_transfer()

    async def _handle_transfer(self):
        """Hand the caller to a person, or tell them the truth about why we can't.

        This used to announce a transfer and then hang up — on the emergency
        path, which is the one call a dental practice cannot afford to drop.
        """
        plan = plan_transfer(self.clinic_config)
        self.transfer_plan = plan
        self._log("assistant", plan.spoken_message)
        logger.info(f"[{self.call_sid}] Transfer plan: {plan.result}")

        # Must finish playing before the redirect discards Twilio's buffer.
        await self._speak_sentence(plan.spoken_message, await_playback=plan.should_dial)

        if plan.should_dial:
            connected = await redirect_call_to_human(
                self.call_sid, plan.dial_number, self.clinic_config.get("_twilio_phone_number")
            )
            if not connected:
                # Twilio refused the redirect; the caller is still with Sarah,
                # so recover rather than leaving them on a dead promise.
                plan.result = "unavailable"
                plan.dial_number = None
                plan.escalate_sms_to = self.clinic_config.get("_after_hours_escalation_number")
                self._log("assistant", UNAVAILABLE_MESSAGE)
                await self._speak_sentence(UNAVAILABLE_MESSAGE)

    async def _speak_text(self, text: str):
        """Speak a single fixed string (used for greeting / silence prompts). Caller logs it."""
        await self._speak_sentence(text)

    async def _speak_sentence(self, text: str, await_playback: bool = False):
        """Stream one sentence to the caller.

        With await_playback, waits until Twilio confirms the audio actually
        reached the caller. Only the transfer path needs that: redirecting the
        call discards Twilio's buffer, so returning early would cut Sarah off
        mid-sentence and the caller would hear a click instead of a handoff.
        """
        if not text.strip() or not self.twilio_ws:
            return
        try:
            async for audio_chunk in self.tts.stream_synthesize(text):
                self._recorded_audio.append(audio_chunk)
                payload = audio_to_twilio_payload(audio_chunk)
                media_message = json.dumps({
                    "event": "media",
                    "streamSid": self.stream_sid,
                    "media": {"payload": payload},
                })
                await self.twilio_ws.send_text(media_message)

            self._mark_counter += 1
            mark_name = f"speech_{self._mark_counter}"
            # Registered before the mark is sent — Twilio can echo it back
            # faster than this coroutine resumes.
            played = asyncio.Event() if await_playback else None
            if played is not None:
                self._pending_marks[mark_name] = played

            mark_message = json.dumps({
                "event": "mark",
                "streamSid": self.stream_sid,
                "mark": {"name": mark_name},
            })
            await self.twilio_ws.send_text(mark_message)

            if played is not None:
                try:
                    await asyncio.wait_for(played.wait(), timeout=PLAYBACK_CONFIRM_TIMEOUT)
                except asyncio.TimeoutError:
                    logger.warning(f"[{self.call_sid}] No playback confirmation for {mark_name}")
                finally:
                    self._pending_marks.pop(mark_name, None)
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
                self._recorded_audio.append(audio_bytes)
                await self.stt.send_audio(audio_bytes)
            elif event == "start":
                logger.info(f"Call stream started: {data.get('start', {}).get('callSid')}")
            elif event == "stop":
                logger.info("Call stream stopped")
                self.is_active = False
            elif event == "mark":
                mark_name = data.get("mark", {}).get("name")
                logger.debug(f"Mark event: {mark_name}")
                # Twilio only echoes a mark once the audio queued before it has
                # played, so this is the signal the transfer path waits on.
                waiter = self._pending_marks.pop(mark_name, None)
                if waiter is not None:
                    waiter.set()
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

        recording_s3_key = None
        if self._recorded_audio and self._clinic_id:
            try:
                recording_s3_key = await upload_recording_to_s3(
                    self.call_sid, b"".join(self._recorded_audio), self._clinic_id
                )
            except Exception as e:
                logger.error(f"Failed to upload call recording for {self.call_sid}: {e}")

        logger.info(
            f"Call {self.call_sid} ended. Duration: {duration:.0f}s, "
            f"Exchanges: {len(self.call_log)}, Avg latency: {avg_latency}"
        )

        return {
            "call_sid": self.call_sid,
            "started_at": self.call_start,
            "duration_seconds": duration,
            "transcript": self.call_log,
            "outcome": self.pending_action.action if self.pending_action else "completed",
            "avg_response_ms": avg_latency,
            "action_params": self.pending_action.params if self.pending_action else {},
            "recording_s3_key": recording_s3_key,
            # The escalation SMS is sent after teardown rather than mid-call:
            # this dict is handed to save_call_transcript from call_handler's
            # finally block, which runs even if the caller hangs up abruptly.
            "transfer_result": self.transfer_plan.result if self.transfer_plan else None,
            "escalate_sms_to": self.transfer_plan.escalate_sms_to if self.transfer_plan else None,
        }
