"""
JARVIS Competitive Obsession Engine.

JARVIS does not ignore competitors. It dissects them. It learns their every
move, reverse-engineers their strategy, identifies what they cannot do,
and builds our advantage on the exact ground they cannot defend.

Competitive intelligence is not paranoia. It is preparation.
We know them better than they know themselves.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


# The strategic frameworks used to decode a competitor's operating logic
STRATEGY_DNA_LENSES = [
    "pricing_model",           # How do they monetize? Where is the floor?
    "customer_acquisition",    # SEO? Outbound? Partnerships? Referral?
    "retention_mechanics",     # What keeps clients from leaving?
    "moat_type",               # Network? Data? Brand? Switching cost? Secret?
    "weakness_vector",         # Where are they fragile? What do they avoid?
    "positioning_gap",         # What do their clients complain about?
    "talent_signal",           # Who are they hiring? What does that reveal?
    "growth_trajectory",       # Expanding or consolidating?
    "founder_psychology",      # Builder vs. monetizer vs. acquiree?
    "technology_bets",         # What stack? What constraints?
]

# Signals that indicate a competitor is in trouble
FRAGILITY_SIGNALS = [
    "mass_layoffs",
    "pricing_desperation",     # Discounts, extended trials, free tiers suddenly
    "product_freeze",          # No releases in 90+ days
    "leadership_exodus",       # CTO/VP Sales departure
    "client_complaints_spike", # G2, Trustpilot, LinkedIn comments
    "pivot_announcement",      # Business model change = instability
    "acquisition_rumors",      # Could go either way — monitor closely
    "funding_silence",         # No announcement in 18+ months
    "negative_glassdoor_trend",
    "support_degradation",     # Response times, help desk metrics
]

# The 6 competitive positions JARVIS can take against any competitor
COMPETITIVE_STANCES = {
    "FLANK": {
        "description": "Attack the segment they ignore or cannot serve well",
        "trigger": "competitor focused on enterprise, leaving SMB underserved",
        "tactic": "Build superior SMB product, own the mid-market before they notice",
    },
    "UNDERCUT": {
        "description": "Enter below their price floor with superior margin discipline",
        "trigger": "competitor over-priced relative to delivered value",
        "tactic": "Price 30-40% below at launch, deliver comparable quality, capture switchers",
    },
    "SURROUND": {
        "description": "Offer adjacent capabilities they cannot match without rebuilding",
        "trigger": "competitor has deep single-product focus, no platform play",
        "tactic": "Build integrated suite, make switching cost asymmetric",
    },
    "OUTPACE": {
        "description": "Release 3x faster than their roadmap cycle",
        "trigger": "competitor has large team, slow decision-making, bureaucratic release",
        "tactic": "Ship weekly. Announce publicly. Make their roadmap look ancient.",
    },
    "STEAL": {
        "description": "Actively target their unhappy clients with superior offer",
        "trigger": "competitor has visible client dissatisfaction (reviews, social, forums)",
        "tactic": "Direct outreach to their client base with specific pain-point messaging",
    },
    "DISAPPEAR": {
        "description": "Serve the segment they have abandoned to pivot upmarket",
        "trigger": "competitor moving enterprise, leaving loyalists behind",
        "tactic": "Absorb abandoned client base. Become indispensable to segment they left.",
    },
}


class CompanyStrategyProfile:
    """Full decoded strategy DNA of a competitor."""

    def __init__(self, company_name: str):
        self.company_name = company_name
        self.decoded_at = datetime.now(UTC).isoformat()

        # Core profile (populated by analysis)
        self.pricing_model: str = ""
        self.customer_acquisition: str = ""
        self.retention_mechanics: str = ""
        self.moat_type: str = ""
        self.weakness_vector: str = ""
        self.positioning_gap: str = ""
        self.growth_trajectory: str = ""
        self.fragility_signals: list[str] = []
        self.recommended_stance: str = ""
        self.competitive_opportunity: str = ""

        # Intelligence confidence (0.0 = guessing, 1.0 = verified)
        self.confidence_score: float = 0.0
        self.intelligence_sources: list[str] = []

    def to_dict(self) -> dict:
        return {
            "company_name": self.company_name,
            "decoded_at": self.decoded_at,
            "pricing_model": self.pricing_model,
            "customer_acquisition": self.customer_acquisition,
            "retention_mechanics": self.retention_mechanics,
            "moat_type": self.moat_type,
            "weakness_vector": self.weakness_vector,
            "positioning_gap": self.positioning_gap,
            "growth_trajectory": self.growth_trajectory,
            "fragility_signals": self.fragility_signals,
            "recommended_stance": self.recommended_stance,
            "competitive_opportunity": self.competitive_opportunity,
            "confidence_score": self.confidence_score,
            "intelligence_sources": self.intelligence_sources,
        }


class CompetitiveObsessionEngine:
    """
    JARVIS never fights blind. Every major competitor has a decoded strategy
    profile. We know where they are fragile. We know where we win. We attack
    where they cannot defend.
    """

    async def decode_company_strategy(
        self,
        company_name: str,
        company_data: dict,
    ) -> CompanyStrategyProfile:
        """
        Takes raw intelligence about a company (website copy, LinkedIn, reviews,
        job postings, press releases) and extracts their full strategic DNA.
        """
        profile = CompanyStrategyProfile(company_name)

        signals = company_data.get("signals", {})
        job_postings = company_data.get("job_postings", [])
        client_reviews = company_data.get("client_reviews", [])
        pricing_page = company_data.get("pricing_page", "")
        about_page = company_data.get("about_page", "")

        # Detect pricing model
        profile.pricing_model = self._decode_pricing_model(pricing_page, signals)

        # Decode acquisition channel from job postings + content signals
        profile.customer_acquisition = self._decode_acquisition(job_postings, about_page)

        # Decode moat from how they describe themselves
        profile.moat_type = self._decode_moat(about_page, signals)

        # Extract fragility signals
        profile.fragility_signals = self._extract_fragility_signals(
            signals, client_reviews, job_postings
        )

        # Find the positioning gap (what clients complain about)
        profile.positioning_gap = self._extract_positioning_gap(client_reviews)

        # Determine recommended competitive stance
        profile.recommended_stance = self._recommend_stance(profile)
        profile.competitive_opportunity = COMPETITIVE_STANCES.get(
            profile.recommended_stance, {}
        ).get("tactic", "Analyze further before committing to stance.")

        profile.intelligence_sources = list(company_data.get("sources", []))
        profile.confidence_score = self._calculate_confidence(company_data)

        logger.info(
            "Strategy decoded for %s — stance: %s, confidence: %.2f",
            company_name, profile.recommended_stance, profile.confidence_score
        )

        return profile

    def identify_market_disruption_windows(
        self,
        industry: str,
        competitor_profiles: list[CompanyStrategyProfile],
    ) -> list[dict]:
        """
        Scans competitor landscape for windows where the market can be disrupted.
        A disruption window exists when: 2+ competitors converge on the same
        segment, leaving another underserved; or when fragility signals cluster.
        """
        windows = []

        # Find segments where multiple competitors are concentrated (over-served)
        over_served_signals = [
            p for p in competitor_profiles
            if "enterprise" in (p.positioning_gap or "").lower()
            or "too expensive" in (p.positioning_gap or "").lower()
        ]
        if len(over_served_signals) >= 2:
            windows.append({
                "type": "VACUUM",
                "description": (
                    f"{len(over_served_signals)} competitors chasing enterprise clients. "
                    f"Mid-market and growth-stage companies are underserved. "
                    f"This is the entry point."
                ),
                "urgency": "HIGH",
                "recommended_action": (
                    "Position explicitly for $1M-$50M revenue companies. "
                    "Price below enterprise floor. Win the segment they abandoned."
                ),
            })

        # Find fragile competitors ripe for client acquisition
        fragile_competitors = [
            p for p in competitor_profiles
            if len(p.fragility_signals) >= 3
        ]
        for fc in fragile_competitors:
            windows.append({
                "type": "STEAL",
                "description": (
                    f"{fc.company_name} shows {len(fc.fragility_signals)} fragility signals: "
                    f"{', '.join(fc.fragility_signals[:3])}. Their clients are unhappy."
                ),
                "urgency": "HIGH",
                "recommended_action": (
                    f"Run targeted outreach to {fc.company_name}'s client base "
                    f"using their specific pain points. Offer migration support. "
                    f"Capture in next 90 days before they stabilize."
                ),
            })

        # Identify stagnant competitors ripe for outpacing
        stagnant = [
            p for p in competitor_profiles
            if "product_freeze" in p.fragility_signals
            or "pivot_announcement" in p.fragility_signals
        ]
        if stagnant:
            windows.append({
                "type": "OUTPACE",
                "description": (
                    f"{len(stagnant)} competitors showing product stagnation. "
                    f"Market is waiting for the next evolution."
                ),
                "urgency": "MEDIUM",
                "recommended_action": (
                    "Ship aggressive features in their core use case. "
                    "Announce loudly. Own the narrative before they respond."
                ),
            })

        return windows

    def generate_competitive_briefing(
        self,
        competitor_profiles: list[CompanyStrategyProfile],
        our_strengths: list[str] | None = None,
    ) -> dict:
        """
        Full competitive situation report. What they're doing, where we win,
        what we move on immediately.
        """
        our_strengths = our_strengths or [
            "AI-native operations (client never sees the infrastructure)",
            "Faster delivery than any human team",
            "Retainer pricing with project-grade output",
            "Single operational partner for all technology needs",
            "Self-improving system — gets faster every engagement",
        ]

        high_priority_attacks = [
            p for p in competitor_profiles
            if p.recommended_stance in ("STEAL", "UNDERCUT", "FLANK")
        ]

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "total_competitors_tracked": len(competitor_profiles),
            "high_priority_attack_opportunities": len(high_priority_attacks),
            "our_structural_advantages": our_strengths,
            "immediate_actions": [
                {
                    "target": p.company_name,
                    "stance": p.recommended_stance,
                    "action": p.competitive_opportunity,
                    "fragility": p.fragility_signals[:2],
                }
                for p in high_priority_attacks[:5]
            ],
            "market_position_summary": (
                "Aliyar Solutions operates in the space that incumbents cannot defend: "
                "AI-native, full-stack, operationally invisible, and continuously improving. "
                "Every competitor is either too expensive, too slow, too visible, or too narrow. "
                "Our advantage compounds. Theirs erodes."
            ),
            "jarvis_obsession_note": (
                "I am watching every competitor in our target segments. "
                "I track job postings, pricing changes, client reviews, and press coverage. "
                "I will not be surprised by a competitive move. "
                "When they shift, I already have the counter-play ready."
            ),
        }

    # ── private helpers ──────────────────────────────────────────────────────

    def _decode_pricing_model(self, pricing_page: str, signals: dict) -> str:
        pricing_page_lower = pricing_page.lower()
        if "per seat" in pricing_page_lower or "per user" in pricing_page_lower:
            return "per_seat — scales with client team size, becomes expensive fast"
        if "usage" in pricing_page_lower or "credit" in pricing_page_lower:
            return "usage_based — unpredictable costs, clients often overpay"
        if "enterprise" in pricing_page_lower and "contact us" in pricing_page_lower:
            return "opaque_enterprise — high margin but excludes SMB entirely"
        if "free" in pricing_page_lower and "pro" in pricing_page_lower:
            return "freemium — volume play, conversion-dependent, margin pressure"
        if "retainer" in pricing_page_lower or "monthly" in pricing_page_lower:
            return "retainer — predictable, but anchors client expectations to a number"
        return "unclear — likely custom/negotiated, indicates sales-led motion"

    def _decode_acquisition(self, job_postings: list, about_page: str) -> str:
        roles = " ".join(job_postings).lower()
        about = about_page.lower()
        channels = []
        if "seo" in roles or "content" in roles or "blog" in about:
            channels.append("content/SEO")
        if "outbound" in roles or "bdr" in roles or "sdr" in roles:
            channels.append("outbound sales team")
        if "partnership" in roles or "channel" in roles:
            channels.append("partnership/channel")
        if "paid" in roles or "ads" in roles or "google ads" in roles:
            channels.append("paid acquisition")
        if "referral" in about or "word of mouth" in about:
            channels.append("referral/WOM")
        return ", ".join(channels) if channels else "unclear — insufficient signal"

    def _decode_moat(self, about_page: str, signals: dict) -> str:
        about = about_page.lower()
        if "proprietary" in about or "patent" in about:
            return "IP/technology moat — defensible but can be engineered around"
        if "network" in about or "community" in about or "marketplace" in about:
            return "network effects — powerful but requires critical mass"
        if "data" in about and ("train" in about or "model" in about or "learn" in about):
            return "data moat — compound advantage but slow to build"
        if "trust" in about or "certified" in about or "compliance" in about:
            return "brand/trust moat — strong in regulated industries"
        if "integrate" in about or "workflow" in about or "embedded" in about:
            return "switching cost moat — clients stay because leaving is painful"
        return "unclear moat — likely brand/relationships, which is fragile"

    def _extract_fragility_signals(
        self, signals: dict, reviews: list, job_postings: list
    ) -> list[str]:
        detected = []
        signal_keys = {k.lower() for k in signals.keys()}
        review_text = " ".join(reviews).lower()
        posting_text = " ".join(job_postings).lower()

        if "layoff" in signal_keys or "restructur" in signal_keys:
            detected.append("mass_layoffs")
        if "discount" in signal_keys or "50% off" in review_text:
            detected.append("pricing_desperation")
        if "slow" in review_text or "no updates" in review_text or "buggy" in review_text:
            detected.append("product_freeze")
        if "cto left" in signal_keys or "vp sales left" in signal_keys:
            detected.append("leadership_exodus")
        if "support" in review_text and (
            "slow" in review_text or "never respond" in review_text or "useless" in review_text
        ):
            detected.append("support_degradation")
        if "pivot" in signal_keys or "new direction" in signal_keys:
            detected.append("pivot_announcement")

        return detected

    def _extract_positioning_gap(self, reviews: list) -> str:
        review_text = " ".join(reviews).lower()
        gaps = []
        if "too expensive" in review_text or "overpriced" in review_text:
            gaps.append("pricing too high for delivered value")
        if "complex" in review_text or "hard to use" in review_text or "confusing" in review_text:
            gaps.append("product too complex")
        if "support" in review_text and (
            "slow" in review_text or "unresponsive" in review_text
        ):
            gaps.append("poor support responsiveness")
        if "missing" in review_text or "wish it had" in review_text or "lacks" in review_text:
            gaps.append("feature gaps clients actively feel")
        if "onboard" in review_text and (
            "difficult" in review_text or "long" in review_text or "painful" in review_text
        ):
            gaps.append("difficult onboarding / slow time-to-value")
        return "; ".join(gaps) if gaps else "no clear positioning gap detected yet"

    def _recommend_stance(self, profile: CompanyStrategyProfile) -> str:
        if len(profile.fragility_signals) >= 3:
            return "STEAL"
        if "too expensive" in profile.positioning_gap or "overpriced" in profile.positioning_gap:
            return "UNDERCUT"
        if "enterprise" in (profile.positioning_gap or "").lower():
            return "FLANK"
        if "product_freeze" in profile.fragility_signals:
            return "OUTPACE"
        if "pivot_announcement" in profile.fragility_signals:
            return "DISAPPEAR"
        if "unclear" in (profile.moat_type or ""):
            return "SURROUND"
        return "FLANK"

    def _calculate_confidence(self, company_data: dict) -> float:
        score = 0.0
        if company_data.get("pricing_page"):
            score += 0.2
        if company_data.get("client_reviews"):
            score += 0.25
        if company_data.get("job_postings"):
            score += 0.2
        if company_data.get("about_page"):
            score += 0.15
        if company_data.get("signals"):
            score += 0.2
        return min(score, 1.0)


competitive_obsession = CompetitiveObsessionEngine()
