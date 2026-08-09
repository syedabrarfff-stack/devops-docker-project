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

from app.services.speech_to_text import _deepgram_url


def test_language_is_always_stated_explicitly():
    assert "&language=en" in _deepgram_url("mulaw", 8000, "en")


def test_serving_a_new_language_market_is_configuration_not_code():
    url = _deepgram_url("mulaw", 8000, "ar")

    assert "&language=ar" in url
    assert "&language=en" not in url


def test_the_demo_and_the_phone_agree_on_language():
    """Two call paths reach Deepgram: the browser demo (linear16/16kHz), which
    is what a prospect evaluates Sarah on, and Twilio telephony (mulaw/8kHz),
    which is what their patients actually get. A language that applied to only
    one of them would make the demo a lie -- Arabic working in the sales call
    and failing for every real patient.

    Each path must also keep its own audio contract: a language change that
    perturbed encoding or sample rate would produce silence rather than a
    wrong-language transcript."""
    phone = _deepgram_url("mulaw", 8000, "ar")
    browser = _deepgram_url("linear16", 16000, "ar")

    assert "&language=ar" in phone
    assert "&encoding=mulaw" in phone and "&sample_rate=8000" in phone

    assert "&language=ar" in browser
    assert "&encoding=linear16" in browser and "&sample_rate=16000" in browser
