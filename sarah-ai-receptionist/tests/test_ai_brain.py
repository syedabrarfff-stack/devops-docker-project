import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.ai_brain import (  # noqa: E402
    _SENTENCE_BOUNDARY,
    _extract_action,
    _strip_action_tags,
    parse_action_params,
)


def _split_sentences(text: str) -> list[str]:
    """Mirrors the streaming flush loop in AIBrain.stream_response."""
    out, buf = [], text
    while True:
        match = _SENTENCE_BOUNDARY.search(buf)
        if not match:
            break
        out.append(buf[: match.end()].strip())
        buf = buf[match.end() :]
    if buf.strip():
        out.append(buf.strip())
    return out


def test_parse_action_params_basic():
    params = parse_action_params("service=cleaning, name=John Doe, phone=555-1234")
    assert params == {"service": "cleaning", "name": "John Doe", "phone": "555-1234"}


def test_parse_action_params_empty():
    assert parse_action_params(None) == {}
    assert parse_action_params("") == {}


def test_extract_action_book():
    text = "Great, I've got you down. [BOOK: service=cleaning, name=Jane, phone=555-0001]"
    action = _extract_action(text)
    assert action is not None
    assert action.action == "BOOK"
    assert action.params["service"] == "cleaning"


def test_extract_action_none():
    assert _extract_action("Just a normal sentence with no tags.") is None


def test_extract_action_transfer():
    action = _extract_action("Let me get someone for you. [TRANSFER]")
    assert action.action == "TRANSFER"
    assert action.params == {}


def test_strip_action_tags():
    text = "Sounds good! [BOOK: service=cleaning] See you then."
    cleaned = _strip_action_tags(text)
    assert "[BOOK" not in cleaned
    assert "Sounds good!" in cleaned
    assert "See you then." in cleaned


def test_titles_do_not_split_sentences():
    """Splitting after "Dr." flushes it to TTS alone, stuttering mid-name on a
    dental clinic's most-spoken word."""
    assert _split_sentences("Dr. Chen has an opening at 3pm.") == ["Dr. Chen has an opening at 3pm."]
    assert _split_sentences("Mr. Patel is booked with Dr. Ramos.") == [
        "Mr. Patel is booked with Dr. Ramos."
    ]


def test_initials_and_decimals_do_not_split():
    assert _split_sentences("J. Smith is our hygienist.") == ["J. Smith is our hygienist."]
    assert _split_sentences("That costs $3.50 total.") == ["That costs $3.50 total."]


def test_real_sentence_boundaries_still_split():
    """The whole point of the splitter is early TTS flushing — it must still cut."""
    assert _split_sentences("Your appointment is confirmed. See you then!") == [
        "Your appointment is confirmed.",
        "See you then!",
    ]
    assert _split_sentences("Is 3pm okay? I can do 4pm.") == ["Is 3pm okay?", "I can do 4pm."]
