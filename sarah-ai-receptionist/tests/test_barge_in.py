import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.barge_in import is_real_interruption  # noqa: E402


def test_ignores_short_noise():
    assert is_real_interruption("") is False
    assert is_real_interruption("uh") is False
    assert is_real_interruption("  ") is False


def test_detects_real_interruption():
    assert is_real_interruption("wait, actually") is True
    assert is_real_interruption("no I meant") is True
