"""
Text-to-Speech — ElevenLabs Turbo streaming, output as 8kHz mulaw
(Twilio's native format, so no resampling is needed on our side).
"""

import base64
import logging
import httpx
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


def audio_to_twilio_payload(audio_bytes: bytes) -> str:
    return base64.b64encode(audio_bytes).decode("ascii")


class TextToSpeech:
    def __init__(self):
        self.settings = get_settings()
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0))

    async def close(self):
        await self._client.aclose()

    async def stream_synthesize(self, text: str):
        """
        Streams raw mulaw/8000 audio chunks from ElevenLabs as they arrive.
        Caller should forward each chunk to Twilio immediately (do not buffer the whole thing).
        """
        if not text.strip():
            return

        url = (
            f"https://api.elevenlabs.io/v1/text-to-speech/"
            f"{self.settings.elevenlabs_voice_id}/stream"
            f"?output_format=ulaw_8000"
        )

        try:
            async with self._client.stream(
                "POST",
                url,
                headers={
                    "xi-api-key": self.settings.elevenlabs_api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/basic",
                },
                json={
                    "text": text,
                    "model_id": self.settings.elevenlabs_model,
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                        "style": 0.3,
                        "use_speaker_boost": True,
                    },
                    "optimize_streaming_latency": 4,
                },
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=640):  # 20ms of mulaw @ 8kHz
                    if chunk:
                        yield chunk

        except httpx.HTTPStatusError as e:
            logger.error(f"ElevenLabs API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"TTS streaming error: {e}")

    async def synthesize(self, text: str) -> bytes:
        """Non-streaming convenience wrapper — collects full audio (used for pre-caching greetings)."""
        chunks = []
        async for chunk in self.stream_synthesize(text):
            chunks.append(chunk)
        return b"".join(chunks)
