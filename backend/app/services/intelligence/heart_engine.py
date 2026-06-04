"""
JARVIS Heart Engine — Prospect Emotional Intelligence.

Deals are not won by features or price alone.
They are won when a prospect feels understood — when the person reading
our proposal feels like it was written specifically for them,
by someone who actually gets what they're dealing with.

The Heart Engine profiles prospect psychology, decodes their emotional
drivers, and calibrates every communication to land with precision.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


# The 8 core emotional buying drivers (every decision has at least 2)
EMOTIONAL_DRIVERS = {
    "FEAR_OF_FALLING_BEHIND": {
        "description": "Competitor is moving faster. Client fears irrelevance.",
        "trigger_signals": [
            "mentions competition",
            "asks about 'latest' or 'cutting edge'",
            "references what their industry is doing",
        ],
        "message_frame": "urgency + positioning as the fast-track solution",
        "sample_hook": "While others are still figuring out AI automation, {company}'s competitors are already deploying it. The window to move first is still open — barely.",
        "close_frame": "Don't let another quarter pass watching this advantage build for someone else.",
    },
    "DESIRE_FOR_STATUS": {
        "description": "Wants to be seen as innovative, smart, ahead of the curve.",
        "trigger_signals": [
            "uses words like 'cutting edge', 'modern', 'leading'",
            "mentions awards, press, or industry recognition",
            "talks about being 'first' or 'best in class'",
        ],
        "message_frame": "exclusivity + prestige + being ahead of peers",
        "sample_hook": "The companies that will define their industry over the next five years are making operational AI decisions right now.",
        "close_frame": "This positions {company} among the operators who move early.",
    },
    "NEED_TO_REDUCE_STRESS": {
        "description": "Overwhelmed, over-stretched, burning out. Wants relief.",
        "trigger_signals": [
            "mentions being 'swamped', 'stretched thin', 'can't keep up'",
            "asks about automation frequently",
            "quick responses late at night or on weekends",
        ],
        "message_frame": "relief + simplicity + we handle it",
        "sample_hook": "What if you woke up Monday and the operational work was already done?",
        "close_frame": "We take this entirely off your plate. You focus on the decisions only you can make.",
    },
    "FINANCIAL_AMBITION": {
        "description": "Motivated by ROI, growth, and revenue numbers.",
        "trigger_signals": [
            "asks about ROI upfront",
            "talks about revenue targets",
            "asks for case studies with numbers",
        ],
        "message_frame": "specific financial return, clear metrics, growth framing",
        "sample_hook": "Our clients typically see a 3-5x return on operational investment within 90 days.",
        "close_frame": "The question isn't whether this pays for itself — it's how quickly.",
    },
    "NEED_FOR_CERTAINTY": {
        "description": "Risk-averse. Needs proof before moving. Hates surprises.",
        "trigger_signals": [
            "asks many 'what if' questions",
            "requests references or testimonials",
            "takes long to respond; asks very detailed questions",
        ],
        "message_frame": "proof, guarantees, step-by-step process, risk reversal",
        "sample_hook": "We break every engagement into clear phases with defined deliverables. Nothing moves to the next phase until you've confirmed the previous one.",
        "close_frame": "You never commit to the full engagement upfront. You approve each stage.",
    },
    "DESIRE_FOR_CONTROL": {
        "description": "Wants to be in charge. Needs to feel like they're directing it.",
        "trigger_signals": [
            "asks detailed questions about process",
            "wants to understand 'how it works'",
            "prefers meetings and updates",
        ],
        "message_frame": "transparency, regular reporting, collaborative framing",
        "sample_hook": "We send weekly updates, and you have full visibility into every action we take.",
        "close_frame": "You set the direction. We execute it. You always have final say.",
    },
    "TRUST_DEFICIT": {
        "description": "Been burned before. Skeptical of vendors. Slow to trust.",
        "trigger_signals": [
            "mentions bad past experience",
            "asks about guarantees or contracts",
            "slower email responses, shorter replies",
        ],
        "message_frame": "proof over promises, small first step, honest about limitations",
        "sample_hook": "We understand you've been through this before. We don't ask for trust upfront — we earn it.",
        "close_frame": "Start with a pilot. No long-term commitment. See the results first.",
    },
    "IDENTITY_ALIGNMENT": {
        "description": "Wants the partner to reflect their own values and identity.",
        "trigger_signals": [
            "asks about company culture or values",
            "references their own company mission",
            "asks 'what kind of company are you'",
        ],
        "message_frame": "shared values, mission alignment, long-term partnership framing",
        "sample_hook": "We built Aliyar Solutions on the same principle your company operates on: results without waste.",
        "close_frame": "This isn't a vendor relationship. This is a long-term operational partnership.",
    },
}


# Relationship momentum states — where is this prospect in their journey with us?
RELATIONSHIP_MOMENTUM = {
    "COLD": {
        "description": "First contact. No prior interaction. Unknown trust level.",
        "approach": "value-first, no ask, demonstrate intelligence",
        "goal": "earn a response",
        "tone": "respectful, specific, brief",
    },
    "WARM": {
        "description": "Has responded or engaged. Knows us. Some curiosity established.",
        "approach": "deepen insight, reference their specific situation",
        "goal": "earn a meeting",
        "tone": "engaged, specific, slightly bolder",
    },
    "HOT": {
        "description": "Actively engaged. Has asked questions or requested more info.",
        "approach": "move toward commitment, surface objections proactively",
        "goal": "earn a decision",
        "tone": "confident, direct, closing-oriented",
    },
    "STALLED": {
        "description": "Was engaged, went quiet. Interested but something stopped them.",
        "approach": "pattern interrupt, new angle, no pressure",
        "goal": "re-engage with a reason",
        "tone": "low-pressure, fresh perspective, honest",
    },
    "CLOSING": {
        "description": "In proposal stage or negotiation. Decision is imminent.",
        "approach": "remove every obstacle, make yes easy, handle final objections",
        "goal": "get the signature",
        "tone": "assumptive, supportive, obstacle-removing",
    },
}


class ProspectEmotionalProfile:
    """Full emotional and psychological profile of a prospect."""

    def __init__(self, lead_id: str, company_name: str):
        self.lead_id = lead_id
        self.company_name = company_name
        self.profiled_at = datetime.now(UTC).isoformat()

        self.primary_driver: str = ""
        self.secondary_driver: str = ""
        self.relationship_momentum: str = "COLD"
        self.communication_style: str = ""
        self.decision_style: str = ""
        self.objection_profile: list[str] = []
        self.recommended_message_frame: str = ""
        self.recommended_close_frame: str = ""
        self.personalization_hooks: list[str] = []

    def to_dict(self) -> dict:
        return {
            "lead_id": self.lead_id,
            "company_name": self.company_name,
            "profiled_at": self.profiled_at,
            "primary_driver": self.primary_driver,
            "secondary_driver": self.secondary_driver,
            "relationship_momentum": self.relationship_momentum,
            "communication_style": self.communication_style,
            "decision_style": self.decision_style,
            "objection_profile": self.objection_profile,
            "recommended_message_frame": self.recommended_message_frame,
            "recommended_close_frame": self.recommended_close_frame,
            "personalization_hooks": self.personalization_hooks,
        }


class HeartEngine:
    """
    JARVIS reads prospects at a deeper level than demographics.
    It reads what drives them, what frightens them, and what will make
    them say yes — then crafts every communication accordingly.
    """

    def profile_prospect(
        self,
        lead_data: dict,
        interaction_history: list[dict] | None = None,
    ) -> ProspectEmotionalProfile:
        """
        Build a full emotional profile of a prospect from lead data
        and any interaction history.
        """
        interaction_history = interaction_history or []
        company_name = lead_data.get("company_name", "Unknown")
        lead_id = str(lead_data.get("id", "unknown"))

        profile = ProspectEmotionalProfile(lead_id, company_name)

        # Determine relationship momentum
        profile.relationship_momentum = self._assess_momentum(
            lead_data, interaction_history
        )

        # Decode primary emotional driver from all signals
        all_signals = self._gather_signals(lead_data, interaction_history)
        primary, secondary = self._decode_drivers(all_signals)
        profile.primary_driver = primary
        profile.secondary_driver = secondary

        # Set communication and decision style
        profile.communication_style = self._decode_comm_style(lead_data)
        profile.decision_style = self._decode_decision_style(lead_data, all_signals)

        # Build objection profile
        profile.objection_profile = self._predict_objections(profile)

        # Set recommended message and close frames
        driver_data = EMOTIONAL_DRIVERS.get(primary, {})
        profile.recommended_message_frame = driver_data.get("message_frame", "value-first")
        profile.recommended_close_frame = driver_data.get(
            "close_frame", "Clear next step with no risk."
        ).replace("{company}", company_name)

        # Personalization hooks
        profile.personalization_hooks = self._build_personalization_hooks(
            lead_data, profile.primary_driver
        )

        logger.info(
            "Prospect profiled: %s — driver: %s, momentum: %s",
            company_name, primary, profile.relationship_momentum
        )

        return profile

    def generate_personalized_hook(
        self, profile: ProspectEmotionalProfile, lead_data: dict
    ) -> str:
        """Generate a single opening hook calibrated to this prospect's psychology."""
        driver_data = EMOTIONAL_DRIVERS.get(profile.primary_driver, {})
        template = driver_data.get("sample_hook", "Aliyar Solutions helps companies like {company} improve operational efficiency.")
        company = lead_data.get("company_name", "your company")
        return template.replace("{company}", company)

    def assess_relationship_health(
        self, interaction_history: list[dict]
    ) -> dict:
        """
        Evaluate the health of a relationship based on interaction patterns.
        Is engagement increasing or decreasing?
        """
        if not interaction_history:
            return {
                "health": "UNKNOWN",
                "recommendation": "Initiate first contact with a high-value insight.",
            }

        response_count = sum(1 for i in interaction_history if i.get("type") == "reply")
        total_touches = len(interaction_history)
        recency_days = interaction_history[-1].get("days_ago", 999) if interaction_history else 999

        if recency_days > 30:
            health = "COOLING"
            rec = "Re-engage with a completely different angle. Do not repeat past messaging."
        elif response_count == 0:
            health = "UNRESPONSIVE"
            rec = "Try a different channel or a dramatically different value proposition."
        elif response_count / max(total_touches, 1) > 0.5:
            health = "STRONG"
            rec = "Momentum is positive. Push toward next commitment stage."
        else:
            health = "MODERATE"
            rec = "Deepening is needed. Add more specific value before the next ask."

        return {
            "health": health,
            "touches": total_touches,
            "responses": response_count,
            "days_since_last_interaction": recency_days,
            "recommendation": rec,
        }

    # ── private helpers ──────────────────────────────────────────────────────

    def _assess_momentum(
        self, lead_data: dict, history: list[dict]
    ) -> str:
        if any(i.get("type") == "reply" for i in history):
            if lead_data.get("stage") in ("proposal", "negotiation", "closing"):
                return "CLOSING"
            return "HOT"
        if history and len(history) > 3:
            days_since = history[-1].get("days_ago", 999) if history else 999
            if days_since > 14:
                return "STALLED"
            return "WARM"
        return "COLD"

    def _gather_signals(self, lead_data: dict, history: list[dict]) -> list[str]:
        signals = []
        signals.append(lead_data.get("notes", "").lower())
        signals.append(lead_data.get("company_description", "").lower())
        for interaction in history:
            signals.append(interaction.get("content", "").lower())
        return signals

    def _decode_drivers(self, signals: list[str]) -> tuple[str, str]:
        signal_text = " ".join(signals)
        scores: dict[str, int] = {}

        for driver_key, driver_data in EMOTIONAL_DRIVERS.items():
            score = 0
            for trigger in driver_data.get("trigger_signals", []):
                if trigger.lower() in signal_text:
                    score += 1
            scores[driver_key] = score

        sorted_drivers = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        primary = sorted_drivers[0][0] if sorted_drivers else "FINANCIAL_AMBITION"
        secondary = sorted_drivers[1][0] if len(sorted_drivers) > 1 else "NEED_FOR_CERTAINTY"

        return primary, secondary

    def _decode_comm_style(self, lead_data: dict) -> str:
        title = lead_data.get("contact_title", "").lower()
        if any(t in title for t in ["cto", "engineer", "technical", "developer", "architect"]):
            return "technical — detail-oriented, expects specifics, low tolerance for vague claims"
        if any(t in title for t in ["ceo", "founder", "owner", "director", "president"]):
            return "executive — ROI and outcomes, not features; time-scarce; decisive"
        if any(t in title for t in ["cmo", "marketing", "brand", "content"]):
            return "creative/strategic — story-driven, brand-aware, audience-focused"
        if any(t in title for t in ["cfo", "finance", "accounting", "controller"]):
            return "financial — cost-focused, risk-averse, wants clear ROI model"
        if any(t in title for t in ["ops", "operations", "process", "manager"]):
            return "operational — process-oriented, concerned with implementation reality"
        return "general professional — balance between outcome, evidence, and ease of decision"

    def _decode_decision_style(self, lead_data: dict, signals: list[str]) -> str:
        signal_text = " ".join(signals)
        if "committee" in signal_text or "team decision" in signal_text or "stakeholder" in signal_text:
            return "committee — multiple approvers; need to arm the champion"
        if any(t in lead_data.get("contact_title", "").lower() for t in ["ceo", "founder", "owner"]):
            return "unilateral — single decision-maker; can move fast once convinced"
        return "consultative — involves 2-3 people; champion sells internally"

    def _predict_objections(self, profile: ProspectEmotionalProfile) -> list[str]:
        objections = []
        if profile.primary_driver == "NEED_FOR_CERTAINTY":
            objections.append("'How do I know this will actually work?'")
            objections.append("'Can you guarantee results?'")
        if profile.primary_driver == "TRUST_DEFICIT":
            objections.append("'We've tried this before and it didn't work.'")
            objections.append("'I need to see proof before I commit.'")
        if profile.primary_driver == "FINANCIAL_AMBITION":
            objections.append("'What's the ROI and how quickly?'")
            objections.append("'This seems expensive relative to the risk.'")
        if profile.relationship_momentum == "COLD":
            objections.append("'I don't know your company well enough.'")
        if profile.decision_style == "committee":
            objections.append("'I need to bring this to my team.'")
        if not objections:
            objections.append("'What makes you different from others?'")
            objections.append("'Is now the right time to invest in this?'")
        return objections[:4]

    def _build_personalization_hooks(
        self, lead_data: dict, primary_driver: str
    ) -> list[str]:
        hooks = []
        company = lead_data.get("company_name", "your company")
        industry = lead_data.get("industry", "")
        size = lead_data.get("employee_count", 0)
        tags = lead_data.get("tags", [])

        if industry:
            hooks.append(f"Reference {industry} industry dynamics specifically")
        if size and int(size) > 200:
            hooks.append("Emphasize enterprise-grade reliability and scale")
        elif size and int(size) < 50:
            hooks.append("Emphasize speed, flexibility, and lean-team advantage")
        if "growth" in str(tags).lower() or "scaling" in str(tags).lower():
            hooks.append(f"Frame around {company}'s growth trajectory")

        driver_data = EMOTIONAL_DRIVERS.get(primary_driver, {})
        for signal in driver_data.get("trigger_signals", [])[:2]:
            hooks.append(f"Address their signal: '{signal}'")

        return hooks[:5]


heart_engine = HeartEngine()
