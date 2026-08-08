"""
Tests for semantic turn detection.

The rule that matters: a caller who trails off mid-sentence must NOT get
answered yet, and a caller who has clearly finished must NOT be made to wait.
Getting the second one wrong adds latency to every single turn of every call,
so these tests lean hard on "finished" staying fast.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.turn_detection import looks_incomplete


def test_trailing_preposition_is_mid_thought():
    assert looks_incomplete("I'd like to book an appointment for") is True


def test_trailing_conjunction_is_mid_thought():
    assert looks_incomplete("I need a cleaning and") is True
    assert looks_incomplete("I wanted to ask because") is True


def test_trailing_article_is_mid_thought():
    assert looks_incomplete("It's been hurting since I had the") is True


def test_hesitation_sound_is_mid_thought():
    assert looks_incomplete("I think it was, um") is True


def test_trailing_comma_is_mid_thought():
    assert looks_incomplete("Tuesday would work,") is True


def test_completed_sentence_is_answered_immediately():
    assert looks_incomplete("I'd like to book a cleaning next Tuesday") is False
    assert looks_incomplete("My tooth really hurts.") is False


def test_question_is_never_held_back():
    """A question is the clearest possible 'your turn' signal."""
    assert looks_incomplete("Do you take Bupa Arabia?") is False
    assert looks_incomplete("Is that okay?") is False


def test_terminal_punctuation_wins_over_a_trailing_stopword():
    """"...about the pain." ends on a noun, but "...what do I do about?" would
    end on a preposition while still being a complete question."""
    assert looks_incomplete("What should I do about?") is False


def test_short_answers_are_answered_immediately():
    """One-word replies are the most common thing a caller says. Making these
    wait would add a pause to nearly every turn."""
    assert looks_incomplete("Tuesday") is False
    assert looks_incomplete("Yes") is False
    assert looks_incomplete("Aslam") is False


def test_bare_hesitation_alone_still_waits():
    assert looks_incomplete("um") is True


def test_empty_input_does_not_wait():
    assert looks_incomplete("") is False
    assert looks_incomplete("   ") is False
