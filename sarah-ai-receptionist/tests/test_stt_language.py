"""
The Deepgram request must always name its transcription language explicitly.

Deepgram treats an absent `language` parameter as English rather than as
auto-detect, so omitting it is an invisible commitment to one language. That
matters more here than it would in most systems: Sarah's system prompt tells
her she is fully bilingual in Modern Standard Arabic and English, and her
ElevenLabs voice model renders Arabic speech, so transcription is the only
link in the chain that would refuse -- and it refuses silently. An Arabic
caller hears no error and no failure; they hear Sarah answer fluently about
something they never said.

These tests pin the parameter's presence, not a particular language: which
language a deployment serves is a config decision, and Deepgram's supported
model/language pairings have to be confirmed against the live API.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.speech_to_text import deepgram_url


def test_language_is_always_stated_explicitly():
    assert "&language=en" in deepgram_url("en")


def test_serving_a_new_language_market_is_configuration_not_code():
    url = deepgram_url("ar")

    assert "&language=ar" in url
    assert "&language=en" not in url


def test_language_does_not_disturb_the_telephony_audio_contract():
    """Twilio's media stream is mulaw/8kHz and Deepgram must be told so.
    A language change that also perturbed encoding or sample rate would
    produce silence on every call rather than a wrong-language transcript."""
    url = deepgram_url("ar")

    assert "&encoding=mulaw" in url
    assert "&sample_rate=8000" in url
