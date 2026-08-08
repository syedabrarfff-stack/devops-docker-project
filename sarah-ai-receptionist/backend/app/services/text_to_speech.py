"""
Text-to-Speech — ElevenLabs Turbo streaming, output as 8kHz mulaw
(Twilio's native format, so no resampling is needed on our side).
"""

import asyncio
import base64
import logging

import httpx

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

# A transient ElevenLabs blip (a 5xx, a dropped connection) used to fail
# silently -- the caller heard nothing for that sentence with no sign the
# call was even still connected. One retry after a short pause absorbs most
# blips without noticeably lengthening the pause before Sarah speaks.
_MAX_TTS_ATTEMPTS = 2
_TTS_RETRY_DELAY_SECONDS = 0.4


class SynthesisFailed(Exception):
    """Raised when TTS could not produce audio after retrying. call_manager
    catches this to speak a fallback phrase instead of leaving the caller in
    silence that looks like a dropped call."""


def audio_to_twilio_payload(audio_bytes: bytes) -> str:
    return base64.b64encode(audio_bytes).decode("ascii")


class TextToSpeech:
    def __init__(self):
        self.settings = get_settings()
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0))

    async def close(self):
        await self._client.aclose()

    async def stream_synthesize(self, text: str, output_format: str = "ulaw_8000"):
        """
        Streams audio chunks from ElevenLabs as they arrive, in the requested
        output_format (default: raw mulaw/8000, Twilio's native format --
        the real call path never overrides this). Caller should forward each
        chunk to its destination immediately (do not buffer the whole thing).

        Retries once on a failure that happens before any audio has been
        yielded (a connection error, a 5xx before the stream opens) -- that's
        a clean retry, nothing was sent yet. A failure *mid-stream*, after
        real audio already reached the caller, does not retry: replaying the
        request from scratch would duplicate the part already spoken, which
        is worse than a sentence cut short. Only raises SynthesisFailed when
        zero audio was produced across every attempt.
        """
        if not text.strip():
            return

        url = (
            f"https://api.elevenlabs.io/v1/text-to-speech/"
            f"{self.settings.elevenlabs_voice_id}/stream"
            f"?output_format={output_format}"
        )
        payload = {
            "text": text,
            "model_id": self.settings.elevenlabs_model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.3,
                "use_speaker_boost": True,
            },
            "optimize_streaming_latency": 4,
        }
        headers = {
            "xi-api-key": self.settings.elevenlabs_api_key,
            "Content-Type": "application/json",
            "Accept": "audio/basic",
        }

        last_error: Exception | None = None
        for attempt in range(1, _MAX_TTS_ATTEMPTS + 1):
            produced_any = False
            try:
                async with self._client.stream("POST", url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes(chunk_size=640):  # 20ms of mulaw @ 8kHz
                        if chunk:
                            produced_any = True
                            yield chunk
                return  # Completed (possibly zero-length text -> zero chunks); done either way.
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.error(f"ElevenLabs API error (attempt {attempt}): {e.response.status_code}")
            except Exception as e:
                last_error = e
                logger.error(f"TTS streaming error (attempt {attempt}): {e}")

            if produced_any:
                # Real audio already reached the caller for this sentence.
                # Stopping here (not raising) is deliberate: call_manager
                # would otherwise treat this as total failure and speak a
                # fallback on top of audio that partially played.
                return
            if attempt < _MAX_TTS_ATTEMPTS:
                await asyncio.sleep(_TTS_RETRY_DELAY_SECONDS)

        raise SynthesisFailed(f"TTS produced no audio after {_MAX_TTS_ATTEMPTS} attempts: {last_error}")

    async def synthesize(self, text: str) -> bytes:
        """Non-streaming convenience wrapper — collects full audio (used for pre-caching greetings)."""
        chunks = []
        async for chunk in self.stream_synthesize(text):
            chunks.append(chunk)
        return b"".join(chunks)
