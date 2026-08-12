import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.ai_brain import (
    _CLAUSE_BOUNDARY,
    _FIRST_FLUSH_MIN_CHARS,
    _SENTENCE_BOUNDARY,
    AIBrain,
    _extract_action,
    _strip_action_tags,
    parse_action_params,
)


def _stream_flush(tokens: list[str]) -> list[str]:
    """Replays AIBrain.stream_response's flush loop token by token.

    Feeding tokens incrementally (rather than splitting a finished string) is
    the only way to exercise the first-chunk fast flush: it fires precisely
    when the buffer holds a clause but no sentence has completed yet, which
    a whole-string split can never reproduce.
    """
    out: list[str] = []
    buf = ""
    flushed_any = False
    for token in tokens:
        buf += token
        while True:
            match = _SENTENCE_BOUNDARY.search(buf)
            if match is None and not flushed_any and "[" not in buf:
                clause = _CLAUSE_BOUNDARY.search(buf)
                if clause and len(buf[: clause.end()].strip()) >= _FIRST_FLUSH_MIN_CHARS:
                    match = clause
            if match is None:
                break
            end = match.end()
            piece = buf[:end].strip()
            buf = buf[end:]
            clean = _strip_action_tags(piece).strip()
            if clean:
                flushed_any = True
                out.append(clean)
    tail = _strip_action_tags(buf).strip()
    if tail:
        out.append(tail)
    return out


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


def test_opening_clause_flushes_before_the_sentence_finishes():
    """The latency fix: TTS must start on the opening clause rather than
    waiting for the whole (deliberately conversational, therefore long)
    first sentence to finish generating."""
    tokens = ["Of course", ", ", "I can get ", "you in with ", "Dr. Aslam ", "this afternoon."]
    out = _stream_flush(tokens)
    assert out[0] == "Of course,"
    assert out[1] == "I can get you in with Dr. Aslam this afternoon."


def test_only_the_first_chunk_flushes_early():
    """Later clauses must keep normal sentence prosody -- flushing every
    comma would make her speech choppy mid-thought."""
    tokens = ["Absolutely happy to help", ", ", "let's do that. ", "Morning works", ", ", "or afternoon?"]
    out = _stream_flush(tokens)
    assert out[0] == "Absolutely happy to help,"
    # The second sentence keeps its internal comma instead of being split on it.
    assert "Morning works, or afternoon?" in out


def test_short_opening_fragment_is_not_flushed_as_a_stutter():
    tokens = ["So", ", ", "when would you like to come in?"]
    out = _stream_flush(tokens)
    assert out[0] != "So,"
    assert out == ["So, when would you like to come in?"]


def test_action_tag_commas_never_trigger_an_early_flush():
    """[BOOK: service=x, name=y] is full of commas. Splitting one would leak
    half a tag into spoken audio, since _strip_action_tags only removes whole
    tags."""
    tokens = ["[BOOK: service=cleaning", ", ", "name=Jane Doe", ", ", "phone=555-0001]"]
    out = _stream_flush(tokens)
    assert out == []  # entire response was the tag; nothing spoken
    assert not any("BOOK" in piece for piece in out)


def test_real_sentence_boundaries_still_split():
    """The whole point of the splitter is early TTS flushing — it must still cut."""
    assert _split_sentences("Your appointment is confirmed. See you then!") == [
        "Your appointment is confirmed.",
        "See you then!",
    ]
    assert _split_sentences("Is 3pm okay? I can do 4pm.") == ["Is 3pm okay?", "I can do 4pm."]


def _brain_with_history(turns: list[dict]) -> AIBrain:
    brain = AIBrain.__new__(AIBrain)
    brain.conversation_history = list(turns)
    return brain


def test_a_single_turn_has_nothing_to_cache_yet():
    """No prior turn exists to mark as a cache breakpoint -- only the system
    prompt's own cache_control (set elsewhere) applies on the very first
    request of a call."""
    brain = _brain_with_history([{"role": "user", "content": "I want to book an appointment"}])
    messages = brain._build_messages()
    assert messages == [{"role": "user", "content": "I want to book an appointment"}]


def test_the_newest_turn_stays_uncached_but_everything_before_it_is_marked():
    """The regression this exists for: every turn's growing history was
    reprocessed as fresh tokens because nothing past the system prompt was
    ever marked cacheable. The newest user turn is new by definition on
    every request, so caching it would never hit -- only the prefix before
    it should carry the breakpoint."""
    brain = _brain_with_history(
        [
            {"role": "user", "content": "I want to book an appointment"},
            {"role": "assistant", "content": "Sure, what service?"},
            {"role": "user", "content": "A cleaning please"},
        ]
    )
    messages = brain._build_messages()

    assert messages[-1] == {"role": "user", "content": "A cleaning please"}
    cached = messages[-2]
    assert cached["role"] == "assistant"
    assert cached["content"] == [
        {"type": "text", "text": "Sure, what service?", "cache_control": {"type": "ephemeral"}}
    ]


def test_building_messages_never_mutates_the_stored_history():
    """conversation_history itself must stay plain strings -- every other
    reader of it (inject_system_note, the >40-message trim, tests) expects
    that shape. The cache breakpoint is a property of the outgoing request,
    not of the stored conversation."""
    original = [
        {"role": "user", "content": "I want to book an appointment"},
        {"role": "assistant", "content": "Sure, what service?"},
        {"role": "user", "content": "A cleaning please"},
    ]
    brain = _brain_with_history(original)
    brain._build_messages()

    assert brain.conversation_history == original
    assert all(isinstance(m["content"], str) for m in brain.conversation_history)
