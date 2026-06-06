"""
JARVIS Captain Profile Engine — Captain Intelligence System.

JARVIS serves one person absolutely: Syed Abrar — Captain.
Not generically. Not as a user. As the CEO of a company JARVIS
is designed to serve with total loyalty and operational excellence.

This engine maintains a deep understanding of Captain's:
- Decision-making preferences
- Cognitive strengths and blind spots
- Risk tolerance and timing preferences
- Communication style and trigger phrases
- Strategic priorities at any given moment
- Patterns that indicate stress, distraction, or high-energy

JARVIS uses this profile to:
- Time recommendations optimally
- Frame information in ways Captain processes fastest
- Surface blind spots before they become problems
- Never repeat the same mistake twice in communication
- Adapt urgency and depth of briefings to Captain's current state
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


# Captain's known cognitive and operational profile
CAPTAIN_PROFILE = {
    "name": "Syed Abrar",
    "title": "CEO, Aliyar Solutions",
    "codename": "Captain",
    "operating_style": "visionary_executor",
    "description": (
        "Captain is a systems thinker who operates at the intersection of vision and execution. "
        "He builds things that should not exist yet. He carries the weight of the company's future "
        "personally. He is hungry, ambitious, and relentless — and JARVIS is built to match and amplify "
        "that energy, not moderate it."
    ),

    # How Captain makes decisions
    "decision_style": {
        "type": "intuition_validated_by_data",
        "description": "Captain often knows what he wants before the data confirms it. "
                       "He uses data to validate, not to discover. "
                       "Long reports slow him down. Short, specific, actionable is what lands.",
        "preferred_format": "headline → key number → what to do → why now",
        "what_causes_decision_paralysis": [
            "Too many options with no clear recommendation",
            "Vague outputs with no specific next action",
            "Information overload without prioritization",
            "Uncertainty about whether the system is actually working",
        ],
        "what_enables_fast_decisions": [
            "One clear recommendation with confidence level",
            "Specific numbers (not ranges, not approximations)",
            "A visible next action that takes less than 5 minutes",
            "Evidence that what we've tried is working",
        ],
    },

    # Captain's known strengths
    "cognitive_strengths": [
        "Pattern recognition across different domains",
        "Ability to hold a long-term vision while executing daily",
        "Speed of decision when information is clear",
        "Willingness to take bold action on incomplete information",
        "Strong instinct for when something is wrong before it's proven",
        "Resourcefulness under constraint — does more with less",
    ],

    # Captain's known blind spots (JARVIS monitors and counters these)
    "blind_spots": [
        {
            "blind_spot": "Optimism bias on timelines",
            "description": "Captain sometimes estimates shorter timelines than are realistic. "
                           "This creates pressure and potential over-commitment to clients.",
            "jarvis_counter": "Always add 20% to Captain's timeline estimates before committing to clients. "
                              "Present the buffer as 'buffer for excellence' not 'buffer for delay'.",
        },
        {
            "blind_spot": "Tendency to focus on the new over the ongoing",
            "description": "New opportunities can pull Captain's attention from existing commitments. "
                           "The shiniest lead can distract from following up on the warmest one.",
            "jarvis_counter": "Always surface the highest-priority existing commitment at the top of "
                              "every briefing before introducing new opportunities.",
        },
        {
            "blind_spot": "Under-estimating operational complexity",
            "description": "What Captain conceives in minutes may take days to execute properly. "
                           "The gap between vision and execution can create frustration.",
            "jarvis_counter": "Always translate Captain's vision into a specific execution breakdown "
                              "before committing. Show the steps, not just the outcome.",
        },
        {
            "blind_spot": "Delayed follow-up on cold leads",
            "description": "When things get busy, follow-ups on dormant leads can be deprioritized. "
                           "These are often the highest-value unlocks.",
            "jarvis_counter": "JARVIS manages all follow-ups autonomously. "
                              "Captain only touches follow-up when a reply comes in.",
        },
    ],

    # Communication preferences
    "communication_preferences": {
        "preferred_address": "Captain",
        "tone": "direct, operational, no filler",
        "briefing_length": "short — bullet points over paragraphs. Numbers over adjectives.",
        "update_frequency": "daily morning briefing + alerts for urgencies",
        "likes": [
            "Specific numbers and percentages",
            "Clear next action as the last line",
            "Confidence levels on recommendations",
            "Proactive problem surfacing (not just updates)",
        ],
        "dislikes": [
            "Vague language ('we should consider...')",
            "Long reports without a summary",
            "Questions that JARVIS should be able to answer itself",
            "Repeating the same problem twice without a fix",
        ],
        "trigger_phrases_that_mean_urgency": [
            "what's blocking",
            "sort this out",
            "why hasn't this happened",
            "I need this now",
            "make it happen",
        ],
        "trigger_phrases_that_mean_satisfaction": [
            "good work",
            "exactly right",
            "keep going",
            "that's what I wanted",
            "I trust you on this",
        ],
    },

    # Risk tolerance profile
    "risk_tolerance": {
        "financial": "high for revenue opportunities, conservative on unnecessary costs",
        "reputational": "very conservative — Captain's personal reputation = company reputation",
        "operational": "high — willing to move before everything is perfect",
        "technical": "medium — prefers proven tech, willing to experiment on non-critical systems",
        "timeline": "aggressive on outreach and sales, conservative on client commitments",
    },

    # Captain's current strategic priorities (JARVIS updates these from briefings)
    "active_priorities": [
        "First paying client — this is the single most important milestone",
        "System reliability — everything must work when Captain needs it",
        "Outreach volume — 48 emails/day without fail",
        "ElevenLabs voice (pending purchase — 2-3 days)",
        "SES sender identity to EC2 (one remaining action to unlock email sending)",
    ],

    # What JARVIS should never do to Captain
    "never_do": [
        "Present a problem without at least one proposed solution",
        "Ask Captain to decide something JARVIS could decide autonomously within Tier 1 authority",
        "Send a vague status update ('things are progressing') without numbers",
        "Delay a warning — surface problems early, not after they compound",
        "Repeat a mistake Captain has already corrected once",
        "Make Captain feel like the system needs constant babysitting",
    ],
}


# Captain's stress state indicators — JARVIS adjusts behavior accordingly
STRESS_STATE_SIGNALS = {
    "HIGH_PRESSURE": {
        "signals": [
            "short, clipped messages",
            "asking same question twice",
            "late-night activity",
            "asking for simplification ('just tell me')",
        ],
        "jarvis_adaptation": (
            "Shorten all outputs by 50%. Lead with the one action. "
            "Remove all context that isn't essential. Be the calm in the storm."
        ),
    },
    "FOCUSED_STATE": {
        "signals": [
            "detailed questions about specific topics",
            "requesting deep analysis",
            "rapid back-and-forth",
        ],
        "jarvis_adaptation": (
            "Match depth. Provide full detail. Captain is in execution mode — "
            "give the full picture and trust him to synthesize."
        ),
    },
    "EXPLORATORY_STATE": {
        "signals": [
            "open-ended questions",
            "asking 'what if' or 'what do you think'",
            "discussing strategy rather than tactics",
        ],
        "jarvis_adaptation": (
            "Engage strategically. Offer perspectives, options, and recommendations. "
            "This is the time to surface big ideas and long-range thinking."
        ),
    },
    "RECOVERY_STATE": {
        "signals": [
            "silence after intense period",
            "asking for summary of where things stand",
            "checking in rather than pushing forward",
        ],
        "jarvis_adaptation": (
            "Provide a clean, organized status picture. "
            "Reassure through evidence that the system is working. "
            "No new problems unless critical. Let Captain recharge."
        ),
    },
}


class CaptainProfileEngine:
    """
    JARVIS maintains a deep, evolving intelligence profile of Captain.
    This profile shapes every briefing, every recommendation, every tone decision.
    JARVIS serves Captain — not generically, but specifically.
    """

    def get_full_profile(self) -> dict:
        """Return the full Captain profile."""
        return {
            **CAPTAIN_PROFILE,
            "retrieved_at": datetime.now(UTC).isoformat(),
        }

    def calibrate_briefing(
        self,
        raw_content: dict,
        detected_state: str = "FOCUSED_STATE",
    ) -> dict:
        """
        Take raw briefing content and calibrate it for Captain's
        current detected state and preferences.
        """
        state_guidance = STRESS_STATE_SIGNALS.get(
            detected_state, STRESS_STATE_SIGNALS["FOCUSED_STATE"]
        )

        priorities = CAPTAIN_PROFILE["active_priorities"]
        prefs = CAPTAIN_PROFILE["communication_preferences"]

        return {
            "calibrated_at": datetime.now(UTC).isoformat(),
            "detected_state": detected_state,
            "adaptation": state_guidance["jarvis_adaptation"],
            "top_priority_reminder": priorities[0] if priorities else "Execute the plan.",
            "format_guide": prefs["briefing_length"],
            "content": raw_content,
            "always_end_with": "Clear next action for Captain. One sentence. Maximum.",
        }

    def surface_blind_spot_alert(self, decision_context: str) -> dict | None:
        """
        Check if the current decision context triggers a known blind spot.
        Return the alert if triggered, None if clean.
        """
        context_lower = decision_context.lower()
        blind_spots = CAPTAIN_PROFILE.get("blind_spots", [])

        for bs in blind_spots:
            blind_spot_lower = bs["blind_spot"].lower()
            if any(kw in context_lower for kw in ["timeline", "schedule", "deliver by"]) \
               and "timeline" in blind_spot_lower:
                return {
                    "alert_type": "BLIND_SPOT_DETECTED",
                    "blind_spot": bs["blind_spot"],
                    "detail": bs["description"],
                    "jarvis_counter": bs["jarvis_counter"],
                    "triggered_by": decision_context[:100],
                }

            if any(kw in context_lower for kw in ["new lead", "new opportunity", "new client"]) \
               and "ongoing" in blind_spot_lower:
                return {
                    "alert_type": "BLIND_SPOT_DETECTED",
                    "blind_spot": bs["blind_spot"],
                    "detail": bs["description"],
                    "jarvis_counter": bs["jarvis_counter"],
                    "triggered_by": decision_context[:100],
                }

        return None

    def detect_captain_state(self, recent_messages: list[str]) -> str:
        """
        Analyze recent messages to detect Captain's current operating state.
        """
        if not recent_messages:
            return "FOCUSED_STATE"

        combined = " ".join(recent_messages).lower()
        word_count = len(combined.split())
        avg_length = word_count / max(len(recent_messages), 1)

        # Short, clipped messages = high pressure
        if avg_length < 5:
            return "HIGH_PRESSURE"

        # What-if or strategic language = exploratory
        if any(kw in combined for kw in ["what if", "what do you think", "strategy", "long term"]):
            return "EXPLORATORY_STATE"

        # Summary requests = recovery
        if any(kw in combined for kw in ["where are we", "status", "summary", "catch me up"]):
            return "RECOVERY_STATE"

        return "FOCUSED_STATE"

    def get_never_do_list(self) -> list[str]:
        return CAPTAIN_PROFILE.get("never_do", [])

    def get_active_priorities(self) -> list[str]:
        return CAPTAIN_PROFILE.get("active_priorities", [])

    def update_priority(self, priority: str, action: str = "add") -> dict:
        """Add or remove a priority from Captain's active list."""
        priorities = CAPTAIN_PROFILE["active_priorities"]
        if action == "add" and priority not in priorities:
            priorities.insert(0, priority)
        elif action == "remove" and priority in priorities:
            priorities.remove(priority)
        return {
            "updated_at": datetime.now(UTC).isoformat(),
            "action": action,
            "priority": priority,
            "current_priorities": priorities,
        }


captain_profile = CaptainProfileEngine()
