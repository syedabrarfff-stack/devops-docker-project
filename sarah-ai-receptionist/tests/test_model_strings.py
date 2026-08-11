"""
Every model string in Settings must be one OpenRouter's catalog actually has.

This class of bug has hit this codebase twice: "anthropic/claude-sonnet-4-6"
(hyphenated) and "google/gemini-flash-1.5" were both requested on every
relevant call for a stretch of time despite neither existing in OpenRouter's
current catalog. Neither failure was loud -- ai_model degraded every live
conversation's quality/speed silently, and ai_model_summary silently failed
every background call-summary job. A wrong string is not a crash; it is a
quietly worse (or entirely broken) product.

These tests can't call OpenRouter's live API from CI (no network, and no key
guaranteed present), so they pin syntax invariants that would have caught
both real incidents:
  - "claude-sonnet-4-6" used a hyphen where OpenRouter's naming uses a dot
    for the minor version (compare the correct "claude-sonnet-4.6"). A
    version-looking suffix with hyphens instead of dots is the exact shape
    of the bug that shipped.
  - Neither broken string carried a date suffix, but that is another
    concrete way this recurs (a snapshot-dated model ID that was valid the
    day it was hardcoded and later retired) -- worth pinning the same
    invariant now that the second incident makes the pattern obvious: no
    "-YYYYMMDD" suffix on any configured model, since dated snapshots are
    exactly the ones that get quietly deprecated out from under a hardcoded
    default.

Actual existence still has to be verified against the live API when a model
string changes -- see settings.py's comments for the specific measurements
behind the current choice. These tests are the regression guard for the
narrower, mechanical failure mode: a typo'd or stale-format string slipping
back in.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.config.settings import Settings

_MODEL_FIELDS = ("ai_model", "ai_model_fast", "ai_model_summary")

# anthropic/claude-<name>-<major>-<minor> (hyphen where a dot belongs) is the
# exact shape of the string that shipped broken.
_HYPHENATED_VERSION = re.compile(r"anthropic/claude-[a-z]+-\d+-\d+(?!-\d)")
_DATE_SUFFIX = re.compile(r"-\d{8}$")


def _defaults() -> dict[str, str]:
    return {f: Settings.model_fields[f].default for f in _MODEL_FIELDS}


def test_no_model_default_is_missing():
    for field, value in _defaults().items():
        assert value, f"{field} has no default at all"


def test_no_anthropic_model_uses_a_hyphenated_version_suffix():
    """The exact bug that shipped: 'claude-sonnet-4-6' instead of the
    catalog's 'claude-sonnet-4.6'. A hyphen where OpenRouter's naming uses a
    dot is not a stylistic difference -- it is a different, nonexistent
    string, and the API accepts it as a request and then fails the call
    rather than rejecting it as malformed."""
    for field, value in _defaults().items():
        if value.startswith("anthropic/"):
            assert not _HYPHENATED_VERSION.match(value), (
                f"{field}={value!r} looks like a hyphenated version suffix "
                f"(x-y instead of x.y) -- exactly the shape of the bug that "
                f"shipped as claude-sonnet-4-6"
            )


def test_no_model_default_carries_a_dated_snapshot_suffix():
    """A '-YYYYMMDD' suffix pins a specific snapshot, which providers retire
    on their own schedule -- valid the day someone hardcodes it, silently
    gone later. Prefer the rolling alias (no date) so this can't recur the
    same way twice."""
    for field, value in _defaults().items():
        assert not _DATE_SUFFIX.search(value), (
            f"{field}={value!r} carries a dated snapshot suffix -- prefer "
            f"the undated rolling alias"
        )


def test_the_live_call_model_is_the_currently_verified_fastest_choice():
    """Pins the specific string chosen from the live A/B in settings.py's
    comment, not just 'a plausible-looking model' -- so a well-intentioned
    edit that types a different valid-looking model doesn't silently undo a
    measured decision. Update this alongside settings.py's measurement
    comment, together, when re-testing supersedes the current numbers."""
    assert Settings.model_fields["ai_model"].default == "anthropic/claude-sonnet-4.6"
