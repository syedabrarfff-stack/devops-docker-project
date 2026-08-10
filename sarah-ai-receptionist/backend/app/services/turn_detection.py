"""
Semantic turn detection — deciding whether the caller has actually finished
their thought, rather than just gone quiet for a moment.

Deepgram's endpointing is purely acoustic: N milliseconds of silence and it
declares the utterance final. That single threshold has to serve two opposite
situations, and does neither well:

  - "I'd like to book an appointment for..."   (thinking -- do NOT answer yet)
  - "...Tuesday afternoon."                    (finished -- answer immediately)

Tuned short, Sarah talks over people mid-sentence. Tuned long, she feels
sluggish even when the caller has clearly finished. The fix is to stop using
silence alone: keep the acoustic threshold short so complete thoughts get an
immediate reply, and add a brief grace period on top only when the words
themselves look unfinished.

This is deliberately lexical rather than a model call. A round-trip to an LLM
to classify turn completion would cost more latency than the grace period it
is trying to avoid, which defeats the purpose.
"""

import re

# Extra wait before answering when the caller's words look mid-thought. Long
# enough to cover drawing a breath while assembling the rest of a sentence,
# short enough that being wrong is barely perceptible.
#
# Owned here rather than in each call manager on purpose: this module is the
# single source of truth for turn-taking policy, and the phone path and the
# browser-demo path drifting apart on it is not hypothetical -- the grace
# period shipped on the demo path alone for some time, so the call path real
# patients use was the only one that would cut a thinking caller off.
INCOMPLETE_UTTERANCE_GRACE_SECONDS = 0.7

# Words that essentially cannot end a finished sentence -- if the caller
# stopped here, they are mid-thought and still assembling the rest.
_TRAILING_INCOMPLETE_WORDS = frozenset(
    {
        # coordinating / subordinating conjunctions
        "and", "but", "or", "so", "because", "since", "while", "although",
        "though", "unless", "until", "if", "whether", "that", "which",
        # prepositions
        "at", "on", "in", "for", "with", "to", "from", "by", "about", "of",
        "into", "onto", "than", "like", "around", "before", "after", "during",
        # articles / determiners
        "a", "an", "the", "my", "your", "his", "her", "their", "our", "its",
        "some", "any", "this", "these", "those",
        # auxiliaries and copulas left dangling
        "is", "are", "was", "were", "am", "be", "been", "being", "do", "does",
        "did", "have", "has", "had", "can", "could", "will", "would", "should",
        "may", "might", "must", "want", "need", "going", "get", "got",
        # hesitation sounds Deepgram transcribes literally
        "um", "uh", "er", "ah", "hmm", "well", "let's", "lets",
    }
)

# A caller who ends on a question mark or a clear terminal is done, full stop --
# never hold those back, even if the last word is in the set above
# ("...what should I do about the pain?" ends in "pain", but "is that okay?"
# would otherwise trip on nothing at all).
_TERMINAL_PUNCTUATION = ("?", "!", ".")

_WORD_RE = re.compile(r"[a-z']+")


def looks_incomplete(text: str) -> bool:
    """Whether the caller appears to be mid-thought rather than finished.

    Conservative by design: when in doubt this returns False (treat as
    finished). A false positive costs the caller a short, pointless wait on
    every single turn; a false negative just means Sarah answers as promptly
    as she did before. Erring toward "finished" keeps the common case fast.
    """
    stripped = text.strip()
    if not stripped:
        return False

    # An explicit terminal means the speaker landed the sentence.
    if stripped.endswith(_TERMINAL_PUNCTUATION):
        return False

    # Trailing comma/dash is an explicit "there's more coming".
    if stripped.endswith((",", ";", ":", "-", "—", "–")):
        return True

    words = _WORD_RE.findall(stripped.lower())
    if not words:
        return False

    # A single word with no punctuation is usually an answer ("Tuesday",
    # "Yes", "Aslam") -- answering promptly matters more here than the rare
    # case where they were about to continue.
    if len(words) == 1:
        return words[0] in _TRAILING_INCOMPLETE_WORDS

    return words[-1] in _TRAILING_INCOMPLETE_WORDS
