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
from app.config.settings import get_settings

logger = logging.getLogger(__name__)

DEEPGRAM_URL = (
    "wss://api.deepgram.com/v1/listen"
    "?model=nova-3"
    "&encoding=mulaw"
    "&sample_rate=8000"
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
    def __init__(self):
        self.settings = get_settings()
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._events: asyncio.Queue[TranscriptEvent | None] = asyncio.Queue()
        self._listen_task: asyncio.Task | None = None
        self._closed = False

    async def connect(self):
        self._ws = await websockets.connect(
            DEEPGRAM_URL,
            additional_headers={"Authorization": f"Token {self.settings.deepgram_api_key}"},
            ping_interval=5,
            ping_timeout=20,
        )
        self._listen_task = asyncio.create_task(self._listen_loop())
        logger.info("Deepgram STT connected")

    async def _listen_loop(self):
        assert self._ws is not None
        try:
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
        except websockets.exceptions.ConnectionClosed:
            logger.info("Deepgram connection closed")
        except Exception as e:
            logger.error(f"Deepgram listen loop error: {e}")
        finally:
            if not self._closed:
                await self._events.put(None)

    async def send_audio(self, audio_bytes: bytes):
        if self._ws is not None and not self._closed:
            try:
                await self._ws.send(audio_bytes)
            except websockets.exceptions.ConnectionClosed:
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
