"""
Speech-to-Text — Deepgram Nova-3 real-time streaming.

Event-driven: Deepgram pushes transcripts to us over its own WebSocket.
We push them into an asyncio.Queue that the call loop awaits on — no polling.
Partial (interim) transcripts are surfaced immediately for barge-in detection.
"""

import asyncio
import json
import logging
from dataclasses import dataclass

import websockets

# Imported directly rather than referenced as websockets.exceptions.X: the
# websockets package (14.x) lazily populates its submodules, and
# `websockets.exceptions` is NOT set on the top-level module by a plain
# `import websockets` -- accessing it as a dotted attribute raises
# AttributeError at the exact moment Python tries to match an exception
# against it. That was the pre-existing pattern here; a real Deepgram
# disconnect would have hit that AttributeError instead of the intended
# graceful-close handling.
from websockets.exceptions import ConnectionClosed

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class _StreamEnded(Exception):
    """Internal signal: the read loop ended without an exception (a clean
    remote close). Treated the same as ConnectionClosed by the reconnect
    logic -- both mean 'this socket is gone, decide whether to retry.'"""

# A transient blip on Deepgram's side (or a brief network hiccup) used to end
# the call outright: the listen loop closed, next_event() returned None, and
# call_manager's loop broke immediately with no attempt to recover. A patient
# mid-conversation would just go silent and eventually hang up confused. This
# retries the connection a few times with backoff before actually giving up.
_MAX_RECONNECT_ATTEMPTS = 3
_RECONNECT_BACKOFF_SECONDS = (0.5, 1.5, 3.0)

def _deepgram_url(encoding: str, sample_rate: int) -> str:
    return (
        "wss://api.deepgram.com/v1/listen"
        "?model=nova-3"
        f"&encoding={encoding}"
        f"&sample_rate={sample_rate}"
        "&channels=1"
        "&interim_results=true"
        "&endpointing=300"
        "&smart_format=true"
        "&punctuate=true"
    )


@dataclass
class TranscriptEvent:
    text: str
    is_final: bool
    speech_final: bool  # Deepgram's endpointing signal: caller has stopped talking


class SpeechToText:
    def __init__(self, encoding: str = "mulaw", sample_rate: int = 8000):
        """encoding/sample_rate default to Twilio's telephony format (mulaw/
        8kHz) -- the real call path never overrides these. The browser demo
        path (no Twilio involved) passes linear16/16000, which Deepgram
        supports natively with no server-side transcoding needed."""
        self.settings = get_settings()
        self._url = _deepgram_url(encoding, sample_rate)
        self._ws: "websockets.asyncio.client.ClientConnection" | None = None
        self._events: asyncio.Queue[TranscriptEvent | None] = asyncio.Queue()
        self._listen_task: asyncio.Task | None = None
        self._closed = False

    async def connect(self):
        self._ws = await self._open_socket()
        self._listen_task = asyncio.create_task(self._listen_loop())
        logger.info("Deepgram STT connected")

    async def _open_socket(self) -> "websockets.asyncio.client.ClientConnection":
        return await websockets.connect(
            self._url,
            additional_headers={"Authorization": f"Token {self.settings.deepgram_api_key}"},
            ping_interval=5,
            ping_timeout=20,
        )

    async def _listen_loop(self):
        """Outer loop: reads events off the current socket, and on an
        unexpected drop reconnects with backoff instead of ending the call.
        Audio arriving from the caller during the reconnect gap is dropped
        (send_audio no-ops while self._ws is a stale/closed handle) -- a real
        but bounded quality hit, versus the call ending outright."""
        while not self._closed:
            try:
                await self._read_until_disconnected()
                return  # self._closed was set out from under us; a clean exit.
            except (ConnectionClosed, _StreamEnded, OSError) as e:
                if self._closed:
                    return
                logger.warning(f"Deepgram connection dropped ({e}); attempting to reconnect")
            except Exception as e:
                if self._closed:
                    return
                logger.error(f"Deepgram listen loop error: {e}; attempting to reconnect")

            if not await self._reconnect_with_backoff():
                logger.error("Deepgram reconnect attempts exhausted; ending call's STT stream")
                if not self._closed:
                    await self._events.put(None)
                return

    async def _read_until_disconnected(self):
        assert self._ws is not None
        async for raw_message in self._ws:
            data = json.loads(raw_message)
            if data.get("type") != "Results":
                continue

            alternatives = data.get("channel", {}).get("alternatives", [])
            if not alternatives:
                continue

            transcript = alternatives[0].get("transcript", "")
            if not transcript:
                continue

            is_final = data.get("is_final", False)
            speech_final = data.get("speech_final", False)

            await self._events.put(
                TranscriptEvent(text=transcript, is_final=is_final, speech_final=speech_final)
            )
        # The async-for loop ends when the socket closes -- including a clean
        # server-initiated close, which raises nothing. Treat that the same as
        # ConnectionClosed: worth a reconnect attempt, not a silent return.
        if not self._closed:
            raise _StreamEnded()

    async def _reconnect_with_backoff(self) -> bool:
        """Tries to re-establish the Deepgram socket. Returns False once the
        attempt budget is spent, so the caller can give up cleanly instead of
        retrying forever."""
        for attempt, delay in enumerate(_RECONNECT_BACKOFF_SECONDS[:_MAX_RECONNECT_ATTEMPTS], start=1):
            if self._closed:
                return False
            await asyncio.sleep(delay)
            try:
                self._ws = await self._open_socket()
                logger.info(f"Deepgram reconnected (attempt {attempt})")
                return True
            except Exception as e:
                logger.warning(f"Deepgram reconnect attempt {attempt} failed: {e}")
        return False

    async def send_audio(self, audio_bytes: bytes):
        if self._ws is not None and not self._closed:
            try:
                await self._ws.send(audio_bytes)
            except ConnectionClosed:
                pass

    async def next_event(self) -> TranscriptEvent | None:
        """Await the next transcript event (interim or final). Returns None on close."""
        return await self._events.get()

    async def close(self):
        self._closed = True
        if self._listen_task:
            self._listen_task.cancel()
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
