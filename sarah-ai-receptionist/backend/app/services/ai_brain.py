"""
AI Brain — streams Claude's response via OpenRouter, sentence by sentence,
so TTS can start speaking before the full response is generated.
"""

import re
import json
import logging
import httpx
from dataclasses import dataclass, field
from app.config.settings import get_settings
from app.prompts.dental_receptionist import build_system_prompt, get_default_clinic_config

logger = logging.getLogger(__name__)

# Titles and abbreviations whose trailing period is not a sentence ending.
# Without these, "Dr. Chen has an opening" is flushed to TTS as "Dr." followed
# by "Chen has an opening" — an audible stutter mid-name, on a dental clinic's
# most-spoken word. Each needs its own lookbehind: Python requires fixed-width
# lookbehinds, so they cannot be collapsed into one alternation.
_ABBREVIATIONS = ("Dr", "Mr", "Mrs", "Ms", "Prof", "St", "Ave", "Rd", "Blvd", "Jr", "Sr", "vs", "approx", "Inc", "Ltd")

# Matches sentence boundaries: . ! ? followed by space/end, but not after a
# known abbreviation or a single initial ("J. Smith").
_SENTENCE_BOUNDARY = re.compile(
    "".join(rf"(?<!\b{abbr})" for abbr in _ABBREVIATIONS) + r"(?<!\b[A-Z])" + r"([.!?])(\s+|$)"
)
_ACTION_TAG = re.compile(r"\[(\w+)(?::\s*(.+?))?\]")


@dataclass
class ActionCommand:
    action: str
    params: dict[str, str] = field(default_factory=dict)


def parse_action_params(raw: str | None) -> dict[str, str]:
    """Parse 'service=cleaning, name=John Doe, phone=555-1234' into a dict."""
    if not raw:
        return {}
    params = {}
    for part in raw.split(","):
        if "=" in part:
            key, _, value = part.partition("=")
            params[key.strip()] = value.strip()
    return params


class AIBrain:
    def __init__(self, clinic_config: dict | None = None, model: str | None = None):
        self.settings = get_settings()
        self.clinic_config = clinic_config or get_default_clinic_config()
        self.system_prompt = build_system_prompt(self.clinic_config)
        self.conversation_history: list[dict] = []
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = model or self.settings.ai_model
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0))

    async def close(self):
        await self._client.aclose()

    def inject_system_note(self, note: str) -> None:
        """Feed the model data it asked for mid-call (e.g. a patient-record lookup).

        Framed explicitly as system data on a user-role turn — the only role
        every OpenRouter-fronted model handles consistently mid-conversation —
        and marked 'do not read aloud' so Sarah paraphrases it instead of
        reciting the raw record. This is never added to the spoken transcript;
        it is context, not something the caller said.
        """
        self.conversation_history.append(
            {
                "role": "user",
                "content": (
                    "[SYSTEM DATA — not spoken by the caller. Use it to answer naturally; "
                    f"do not read it aloud verbatim.]\n{note}"
                ),
            }
        )

    async def stream_response(self, caller_text: str | None = None):
        """
        Streams Sarah's spoken response as sentence-sized chunks (for TTS),
        then yields a final ActionCommand (or None) once the stream ends.

        caller_text=None continues from the current history without adding a new
        caller turn — used after inject_system_note, so Sarah answers using the
        looked-up data rather than waiting for the caller to speak again.

        Yields: ("sentence", str) for each spoken chunk
                ("action", ActionCommand | None) exactly once at the end
        """
        if caller_text is not None:
            self.conversation_history.append({"role": "user", "content": caller_text})
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]

        buffer = ""
        full_response = ""
        action: ActionCommand | None = None

        try:
            async with self._client.stream(
                "POST",
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://aliyarsolutions.com",
                    "X-Title": "Sarah AI Receptionist",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "system", "content": self.system_prompt}, *self.conversation_history],
                    "max_tokens": 200,
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue

                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if not content:
                        continue

                    full_response += content
                    buffer += content

                    # Flush complete sentences to the caller for immediate TTS
                    while True:
                        match = _SENTENCE_BOUNDARY.search(buffer)
                        if not match:
                            break
                        end = match.end()
                        sentence = buffer[:end].strip()
                        buffer = buffer[end:]
                        clean = _strip_action_tags(sentence).strip()
                        if clean:
                            yield ("sentence", clean)

            # Flush whatever remains after stream ends
            tail = _strip_action_tags(buffer).strip()
            if tail:
                yield ("sentence", tail)

            action = _extract_action(full_response)
            self.conversation_history.append({"role": "assistant", "content": full_response})

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error: {e.response.status_code} — {e.response.text}")
            yield ("sentence", "I'm sorry, I'm having a little trouble right now. Could you hold on one moment?")
        except Exception as e:
            logger.error(f"AI Brain streaming error: {e}")
            yield ("sentence", "I apologize for the inconvenience. Let me transfer you to our office manager.")
            action = ActionCommand(action="TRANSFER")

        yield ("action", action)

    def reset_conversation(self):
        self.conversation_history = []


def _extract_action(text: str) -> ActionCommand | None:
    match = _ACTION_TAG.search(text)
    if not match:
        return None
    return ActionCommand(action=match.group(1), params=parse_action_params(match.group(2)))


def _strip_action_tags(text: str) -> str:
    return _ACTION_TAG.sub("", text)
