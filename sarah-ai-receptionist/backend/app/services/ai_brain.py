"""
AI Brain — streams Claude's response via OpenRouter, sentence by sentence,
so TTS can start speaking before the full response is generated.
"""

import json
import logging
import re
from dataclasses import dataclass, field

import httpx

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

# Clause boundaries (comma, semicolon, colon, dash) used ONLY for the first
# flush of a turn. Waiting for a full sentence before starting TTS means the
# caller hears nothing until the model has generated an entire sentence --
# and Sarah's sentences are deliberately conversational, so that dead air is
# the single largest contributor to "she takes a long time to respond".
# Flushing the opening clause ("Of course," / "I can definitely help with
# that,") gets her voice started while the rest of the sentence is still
# generating; every subsequent chunk uses normal sentence boundaries so
# prosody stays natural mid-thought.
_CLAUSE_BOUNDARY = re.compile(r"[,;:—–]\s+")
# Tuned against real openers: "So," (3) and "Sure," (5) are too short to send
# alone -- they'd land as a clipped stutter and cost a TTS round-trip for
# almost no audio. "Of course," (10) and "I understand," (13) are complete
# conversational units that sound natural standing on their own, which is
# exactly how a person actually talks. 10 is the boundary between the two.
_FIRST_FLUSH_MIN_CHARS = 10


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

    def _build_messages(self) -> list[dict]:
        """conversation_history plus a second cache breakpoint on everything
        in it except the newest turn.

        Only the system prompt was ever marked cacheable before this. That
        left every turn's growing conversation history -- the caller's and
        Sarah's own prior lines, all of it -- reprocessed as fresh,
        uncached tokens on every single request, including the parts that
        were identical to the previous turn's request. Confirmed live: a
        5-turn demo conversation with no history caching measured
        time-to-first-token growing from ~1.5s to ~2.0s turn over turn,
        purely from cold-processing the same prior messages again and
        again.

        The newest turn is deliberately left out of the cached prefix --
        it's new every request by definition, so marking it cacheable would
        never hit and just adds overhead for nothing.
        """
        messages = list(self.conversation_history)
        if len(messages) < 2:
            return messages
        idx = len(messages) - 2
        prior = messages[idx]
        content = prior["content"]
        if isinstance(content, str):
            messages[idx] = {
                **prior,
                "content": [{"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}],
            }
        return messages

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
        # Whether anything has been handed to TTS yet this turn -- gates the
        # early clause-level flush to the opening fragment only.
        flushed_any = False

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
                    # cache_control on the system block asks Claude to cache it
                    # server-side (Anthropic prompt caching, passed through by
                    # OpenRouter) so every turn after the first in a call reuses
                    # it instead of reprocessing the whole system prompt from
                    # scratch -- the system prompt has grown substantially and
                    # was becoming a real, measurable chunk of response latency
                    # on every single turn, not just the first.
                    "messages": [
                        {
                            "role": "system",
                            "content": [
                                {
                                    "type": "text",
                                    "text": self.system_prompt,
                                    "cache_control": {"type": "ephemeral"},
                                }
                            ],
                        },
                        *self._build_messages(),
                    ],
                    "max_tokens": 280,
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "stream": True,
                    # OpenRouter fronts several upstream providers for the same
                    # model, and picks one by its own default heuristics. On a
                    # live phone call time-to-first-token is what the caller
                    # actually feels, so ask for the lowest-latency provider
                    # rather than the cheapest.
                    "provider": {"sort": "latency"},
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
                        if match is None and not flushed_any and "[" not in buffer:
                            # Opening fragment only, and only while no action
                            # tag has started: splitting on a comma inside
                            # "[BOOK: service=x, name=y]" would cut the tag in
                            # half and leak its text into spoken audio, since
                            # _strip_action_tags can only remove a whole tag.
                            clause = _CLAUSE_BOUNDARY.search(buffer)
                            if clause and len(buffer[: clause.end()].strip()) >= _FIRST_FLUSH_MIN_CHARS:
                                match = clause
                        if match is None:
                            break
                        end = match.end()
                        sentence = buffer[:end].strip()
                        buffer = buffer[end:]
                        clean = _strip_action_tags(sentence).strip()
                        if clean:
                            flushed_any = True
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
