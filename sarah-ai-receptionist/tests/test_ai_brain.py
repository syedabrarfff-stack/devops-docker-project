import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.ai_brain import parse_action_params, _extract_action, _strip_action_tags  # noqa: E402


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
