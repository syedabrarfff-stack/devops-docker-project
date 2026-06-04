"""
JARVIS Offer Engine — Grand Slam Offer Framework.

A mediocre offer at any price is a bad deal.
A Grand Slam Offer makes the prospect feel like they are getting
10x more value than they are paying for.

This is not about manipulation. It is about framing real value
in a way that makes the decision obvious.

Framework adapted from Alex Hormozi's Grand Slam Offer system —
applied to Aliyar Solutions' service model.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


# The 5 value drivers that make an offer irresistible (Hormozi framework)
VALUE_DRIVERS = {
    "DREAM_OUTCOME": {
        "definition": "The specific, vivid result the client wants to achieve",
        "amplifier": "Make the outcome as specific and visual as possible",
        "example": "Not 'improve operations' — but 'cut your reporting time from 8 hours/week to 20 minutes'",
        "weight": 0.35,
    },
    "PERCEIVED_LIKELIHOOD": {
        "definition": "How confident the prospect is that they will actually get the result",
        "amplifier": "Proof: case studies, guarantees, references, pilot offers",
        "example": "Not 'we'll try our best' — but 'here are 3 companies who got exactly this result'",
        "weight": 0.25,
    },
    "TIME_TO_VALUE": {
        "definition": "How quickly they start seeing results",
        "amplifier": "Quick wins in week 1. Show progress before the invoice is due.",
        "example": "Not 'results in 3–6 months' — but 'you'll see the first deliverable within 48 hours of signing'",
        "weight": 0.20,
    },
    "EFFORT_AND_SACRIFICE": {
        "definition": "How much effort the client has to put in themselves",
        "amplifier": "Remove every requirement on the client. We do the work. They approve.",
        "example": "Not 'you'll need to attend weekly workshops' — but 'we handle everything, you just review and approve'",
        "weight": 0.15,
    },
    "RISK_REVERSAL": {
        "definition": "Who bears the risk if it doesn't work",
        "amplifier": "Pilot offers, milestone payments, satisfaction guarantees",
        "example": "Not 'pay 100% upfront' — but '50% now, 50% when you see the deliverables'",
        "weight": 0.05,
    },
}


# The 4 pricing tiers for Aliyar Solutions
PRICING_TIERS = {
    "STARTER": {
        "name": "Starter",
        "price_range": "$2,500–$3,500/month",
        "anchor_price": 2500,
        "target_client": "Growing startups, small businesses scaling operations",
        "included": [
            "AI-powered lead generation (20–30 qualified leads/month)",
            "Automated outreach sequences (3-touch email + LinkedIn)",
            "Monthly performance reporting",
            "Dedicated account coordinator",
        ],
        "dream_outcome": "Consistent pipeline of qualified prospects without hiring a sales team",
        "time_to_value": "First leads within 5 business days of onboarding",
        "risk_reversal": "30-day pilot with milestone review before full commitment",
    },
    "GROWTH": {
        "name": "Growth",
        "price_range": "$5,000–$7,500/month",
        "anchor_price": 5500,
        "target_client": "Established businesses ready to systematize and scale",
        "included": [
            "Everything in Starter",
            "Full CRM automation (HubSpot/Apollo integration)",
            "AI proposal generation and follow-up",
            "Weekly strategic intelligence briefing",
            "Multi-channel outreach (email + LinkedIn + WhatsApp)",
        ],
        "dream_outcome": "Revenue operation that runs without the founder's daily involvement",
        "time_to_value": "Fully configured system live within 7 business days",
        "risk_reversal": "50/50 payment split — 50% upfront, 50% at 30-day review",
    },
    "ENTERPRISE": {
        "name": "Enterprise Operations",
        "price_range": "$10,000–$15,000/month",
        "anchor_price": 12000,
        "target_client": "Scaling companies needing full operational AI infrastructure",
        "included": [
            "Everything in Growth",
            "Full AI infrastructure deployment (JARVIS operational layer)",
            "Custom AI agents for client-specific workflows",
            "Cloud architecture + DevOps management",
            "Weekly executive briefing for leadership team",
            "Priority support — 4-hour response SLA",
        ],
        "dream_outcome": "A company that operates like it has a 20-person operations team at a fraction of the cost",
        "time_to_value": "Phase 1 delivery within 10 business days; full operation within 30",
        "risk_reversal": "Phased payment: 33% at each delivery milestone",
    },
    "PROJECT": {
        "name": "Fixed-Scope Project",
        "price_range": "$5,000–$25,000 one-time",
        "anchor_price": 8000,
        "target_client": "Companies needing a specific system built, then managed internally",
        "included": [
            "Scoped discovery and solution design",
            "Full build and deployment",
            "Documentation and handover",
            "30-day post-launch support",
        ],
        "dream_outcome": "A specific operational problem solved permanently, with documentation to run it yourself",
        "time_to_value": "Discovery completed within 48 hours; build timeline agreed upfront",
        "risk_reversal": "50% upfront, 50% on delivery and client sign-off",
    },
}


# Objection-to-response map for closing conversations
OBJECTION_RESPONSES: dict[str, dict] = {
    "too_expensive": {
        "objection": "This is too expensive / out of our budget",
        "reframe": "Cost vs. value comparison",
        "response": (
            "I understand the number feels significant. Let me put it in context: "
            "a mid-level marketing hire costs $50,000–$80,000 per year in salary alone, "
            "before benefits, management time, and ramp-up. "
            "At $X/month, that is $Xy/year — for a system that works 24/7, "
            "never leaves, and improves over time. "
            "The question is not whether this is expensive. "
            "It is whether the return justifies the investment. Let me show you the math."
        ),
        "fallback": "Offer a scoped pilot at 50% of standard price to demonstrate results first.",
    },
    "not_sure_it_works": {
        "objection": "I'm not sure this will work for our specific situation",
        "reframe": "Risk reversal + specificity",
        "response": (
            "That is exactly why we offer a pilot structure. "
            "We do not ask you to commit to a 12-month retainer before you have seen the results. "
            "We agree on specific deliverables for the first 30 days. "
            "You review. If it is not what we described, you do not continue. "
            "The risk sits with us, not with you."
        ),
        "fallback": "Offer a single-deliverable starter: one campaign, one audit, one build — scoped tight.",
    },
    "need_to_think": {
        "objection": "I need to think about it / I'll get back to you",
        "reframe": "Uncover the real objection",
        "response": (
            "Of course — and I want to make sure you have everything you need to think clearly. "
            "Usually when someone wants to think it over, there is one specific thing that is not yet resolved. "
            "Is it the price? The scope? Whether this is the right time? "
            "Tell me what the real sticking point is and we can address it directly."
        ),
        "fallback": "Set a specific follow-up time. Do not leave it open-ended.",
    },
    "already_have_someone": {
        "objection": "We already have a solution / agency for this",
        "reframe": "Stack vs. replace positioning",
        "response": (
            "That makes sense — and I am not here to replace what is working. "
            "The question worth asking is: what is it not doing? "
            "Most of our clients came to us with existing solutions. "
            "What we add is the intelligence layer — the part that learns, adapts, and compounds. "
            "What specifically is your current setup not delivering that you wish it would?"
        ),
        "fallback": "Ask for a comparison: 'What would it take for you to consider switching?'",
    },
    "no_time_to_implement": {
        "objection": "We don't have time to implement this right now",
        "reframe": "We handle implementation entirely",
        "response": (
            "That is exactly why this is designed to require almost none of your time. "
            "We handle the setup, the configuration, the onboarding. "
            "Your involvement is approximately 2 hours total in the first week — "
            "a kickoff call and a review call. After that, we operate and report. "
            "Your time investment is intentionally minimal by design."
        ),
        "fallback": "Offer a delayed start date: 'We can begin setup on [date X] when timing is better.'",
    },
}


class OfferEngine:
    """
    Constructs Grand Slam Offers for Aliyar Solutions service proposals.
    Every output maximizes perceived value relative to price, includes
    risk reversal, and drives toward a specific next action.
    """

    def build_proposal_offer(
        self,
        lead_data: dict,
        emotional_profile: dict | None = None,
        recommended_tier: str = "GROWTH",
    ) -> dict:
        """
        Build a complete proposal offer structure for a specific lead.
        Returns all elements needed to construct the proposal document.
        """
        company = lead_data.get("company_name", "your company")
        industry = lead_data.get("industry", "")
        pain_points = lead_data.get("pain_points", [])
        tier = PRICING_TIERS.get(recommended_tier, PRICING_TIERS["GROWTH"])

        # Build the dream outcome statement
        dream_outcome = self._craft_dream_outcome(company, industry, pain_points, tier)

        # Build the value stack
        value_stack = self._build_value_stack(tier, emotional_profile)

        # Select risk reversal approach
        risk_reversal = self._select_risk_reversal(lead_data, emotional_profile)

        # Build urgency frame
        urgency = self._build_urgency_frame(lead_data)

        # Build the opening statement
        opening = self._craft_opening(company, industry, dream_outcome)

        logger.info("Offer built for %s — tier: %s", company, recommended_tier)

        return {
            "company": company,
            "tier": recommended_tier,
            "tier_details": tier,
            "dream_outcome": dream_outcome,
            "value_stack": value_stack,
            "risk_reversal": risk_reversal,
            "urgency_frame": urgency,
            "opening_statement": opening,
            "price_anchor": tier["anchor_price"],
            "call_to_action": f"Let's schedule a 20-minute call this week to confirm this is the right fit for {company}.",
            "built_at": datetime.now(UTC).isoformat(),
        }

    def select_tier(self, lead_data: dict) -> str:
        """Recommend the right pricing tier based on lead profile."""
        size = int(lead_data.get("employee_count", 0))
        revenue = lead_data.get("annual_revenue", "")
        stage = lead_data.get("company_stage", "").lower()
        score = lead_data.get("lead_score", 0)

        if size > 200 or "enterprise" in stage or score > 85:
            return "ENTERPRISE"
        if size > 20 or "growth" in stage or score > 70:
            return "GROWTH"
        if "project" in str(lead_data.get("pain_points", [])).lower():
            return "PROJECT"
        return "STARTER"

    def handle_objection(self, objection_type: str) -> dict:
        """Return the response framework for a specific objection."""
        obj = OBJECTION_RESPONSES.get(objection_type)
        if not obj:
            # Find closest match
            for key, val in OBJECTION_RESPONSES.items():
                if objection_type.lower() in key.lower():
                    return val
            return {
                "response": (
                    "Tell me more about that concern. "
                    "I want to make sure I'm addressing exactly what is holding you back."
                ),
                "fallback": "Ask an open question to surface the real objection.",
            }
        return obj

    def get_all_tiers(self) -> dict:
        return PRICING_TIERS

    # ── private helpers ──────────────────────────────────────────────────────

    def _craft_dream_outcome(
        self,
        company: str,
        industry: str,
        pain_points: list,
        tier: dict,
    ) -> str:
        base = tier.get("dream_outcome", "")
        if pain_points:
            top_pain = pain_points[0] if isinstance(pain_points[0], str) else str(pain_points[0])
            return (
                f"For {company}: {base}. "
                f"Specifically addressing {top_pain} — "
                f"resolved in the first 30 days."
            )
        return f"For {company}: {base}"

    def _build_value_stack(self, tier: dict, emotional_profile: dict | None) -> list[dict]:
        stack = []
        for item in tier.get("included", []):
            stack.append({
                "deliverable": item,
                "value_driver": "DREAM_OUTCOME",
                "standalone_value": "Included",
            })

        # Add time-to-value element
        stack.append({
            "deliverable": f"Onboarding & setup: {tier.get('time_to_value', 'Within 7 days')}",
            "value_driver": "TIME_TO_VALUE",
            "standalone_value": "Included",
        })

        # Add risk reversal element
        stack.append({
            "deliverable": f"Payment structure: {tier.get('risk_reversal', '50/50 split')}",
            "value_driver": "RISK_REVERSAL",
            "standalone_value": "Included",
        })

        return stack

    def _select_risk_reversal(
        self, lead_data: dict, emotional_profile: dict | None
    ) -> str:
        primary_driver = (emotional_profile or {}).get("primary_driver", "")

        if primary_driver in ("NEED_FOR_CERTAINTY", "TRUST_DEFICIT"):
            return (
                "Pilot offer: 30-day structured pilot with defined deliverables. "
                "Review at day 30. No commitment to continue unless results are satisfactory."
            )
        if primary_driver == "FINANCIAL_AMBITION":
            return (
                "Milestone-based payment: 50% at engagement start, 50% tied to "
                "specific agreed deliverables. You approve before the second payment."
            )
        return (
            "Standard split: 50% upfront to begin, 50% at 30-day review. "
            "You own all deliverables from day one."
        )

    def _build_urgency_frame(self, lead_data: dict) -> str:
        industry = lead_data.get("industry", "your industry")
        return (
            f"AI-native operational advantages are being built right now across {industry}. "
            "The companies establishing these systems today will have a 12–18 month operational lead "
            "that their competitors cannot close quickly. "
            "This advantage is time-sensitive — not because of artificial scarcity, "
            "but because early implementation means earlier compounding."
        )

    def _craft_opening(self, company: str, industry: str, dream_outcome: str) -> str:
        return (
            f"Aliyar Solutions is pleased to present this proposal for {company}. "
            f"Our team has reviewed your operational profile and designed a solution "
            f"specifically for a {industry} company at your stage. "
            f"The objective is direct: {dream_outcome}."
        )


offer_engine = OfferEngine()
