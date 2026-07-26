"""
Barge-in — lets the caller interrupt Sarah mid-sentence.

Twilio's Media Streams protocol supports a "clear" event that instantly
flushes any audio queued for playback on the caller's line. Combined with
cancelling our in-flight TTS/AI tasks, this gives a natural interruption
experience like a real phone conversation.
"""

import json
import logging

logger = logging.getLogger(__name__)

MIN_INTERRUPT_CHARS = 3  # ignore tiny noise blips ("uh", "um") as interruptions


async def send_clear_event(twilio_ws, stream_sid: str):
    """Tell Twilio to immediately drop any buffered/playing audio on this call."""
    try:
        await twilio_ws.send_text(json.dumps({"event": "clear", "streamSid": stream_sid}))
    except Exception as e:
        logger.warning(f"Failed to send clear event: {e}")


def is_real_interruption(interim_text: str) -> bool:
    return len(interim_text.strip()) >= MIN_INTERRUPT_CHARS
