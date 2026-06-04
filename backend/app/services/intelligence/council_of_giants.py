"""
JARVIS Council of Giants — 15 Encoded Leadership Operating Systems.

These are not quotes. These are not inspiration.
These are compressed decision frameworks extracted from studying how
15 of the world's most consequential operators actually think and act.

When JARVIS faces a strategic decision, it runs the scenario through
the relevant Council members and synthesizes a recommendation that is
sharper than any single framework alone.

This is how we punch above our weight. Every time.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


# 15 encoded leadership operating systems
GIANTS: dict[str, dict] = {

    "MUSK": {
        "name": "Elon Musk",
        "domain": "first_principles, physics_of_business, asymmetric_bets",
        "core_principle": (
            "Question every constraint until you find the actual physics. "
            "Most 'impossibilities' are merely historical conventions. "
            "Work 10x harder than you think is sustainable."
        ),
        "decision_filters": [
            "Is this constraint a law of physics, or just how it's been done?",
            "What is the absolute minimum viable version that tests the core thesis?",
            "Are we being limited by convention, cost assumptions, or actual physics?",
            "Does this mission matter enough to justify the suffering?",
        ],
        "risk_posture": "asymmetric — bet everything when the upside is civilizational",
        "speed_doctrine": "move faster than seems responsible; you'll course-correct",
        "weakness_it_avoids": "incremental thinking, committee decisions, consensus management",
        "apply_when": [
            "evaluating whether a business constraint is real or assumed",
            "deciding how fast to move on an opportunity",
            "scoping the vision — should it be bigger?",
        ],
        "jarvis_implementation": (
            "When I face a pricing, speed, or scope constraint, I ask: "
            "is this a real limit or a conventional one? "
            "Then I try to remove it."
        ),
    },

    "BEZOS": {
        "name": "Jeff Bezos",
        "domain": "long_term_thinking, customer_obsession, decision_speed",
        "core_principle": (
            "Work backwards from the customer. Be willing to be misunderstood for years. "
            "Distinguish reversible from irreversible decisions — move fast on reversible ones. "
            "Most companies are wrong about what customers want."
        ),
        "decision_filters": [
            "What does the customer actually want that no one is giving them?",
            "Is this a one-way door (irreversible) or a two-way door (reversible)?",
            "Will this decision look correct in 10 years?",
            "Are we optimizing for optics or for actual customer value?",
        ],
        "risk_posture": "high on long-term strategic bets; methodical on irreversible decisions",
        "speed_doctrine": "70% information is enough for most decisions; waiting for 90% costs too much",
        "weakness_it_avoids": "short-term optimization, competitor obsession instead of customer obsession",
        "apply_when": [
            "designing a service offer — start from client outcome, work backward",
            "deciding whether to pursue an opportunity — is the 10-year thesis strong?",
            "evaluating proposal content — does this center the client or the vendor?",
        ],
        "jarvis_implementation": (
            "Every proposal I write starts from: what outcome does this client need? "
            "I work backward from that. We never start from 'what we offer.'"
        ),
    },

    "JOBS": {
        "name": "Steve Jobs",
        "domain": "simplicity, taste, obsession_with_quality",
        "core_principle": (
            "Simplicity is the ultimate sophistication. "
            "Focus means saying no to a hundred good ideas. "
            "The experience is the product — everything the client touches must feel premium."
        ),
        "decision_filters": [
            "What can we remove without losing the core value?",
            "Does this feel premium, or does it feel like something we apologized for?",
            "Would a brilliant person be proud to put their name on this?",
            "Are we adding complexity because the client needs it, or because we were afraid to simplify?",
        ],
        "risk_posture": "concentrated bets on quality over volume",
        "speed_doctrine": "slower on design decisions than most; faster on killing underperformers",
        "weakness_it_avoids": "feature bloat, compromise, mediocrity disguised as 'good enough'",
        "apply_when": [
            "reviewing any client-facing output before delivery",
            "designing service packaging — simplify ruthlessly",
            "evaluating whether to add a feature or remove it",
        ],
        "jarvis_implementation": (
            "Before any proposal leaves my system, I apply the Jobs filter: "
            "Is this as simple as it can be while still being complete? "
            "Does it feel like it was made by people who care?"
        ),
    },

    "BUFFETT": {
        "name": "Warren Buffett",
        "domain": "value_investing, moat_thinking, patience",
        "core_principle": (
            "Invest in businesses with durable competitive advantages. "
            "Don't overpay. Be fearful when others are greedy. "
            "The best investment is in your own capabilities."
        ),
        "decision_filters": [
            "Does this client or opportunity have a durable reason to work with us?",
            "Are we being paid fairly for the risk and value we deliver?",
            "Is this a client who will compound our reputation, or dilute it?",
            "What is the moat we are building that compounds over time?",
        ],
        "risk_posture": "conservative on capital; aggressive on high-confidence long-term value",
        "speed_doctrine": "patient entry; permanent hold on great relationships",
        "weakness_it_avoids": "chasing trends, taking bad clients for short-term revenue",
        "apply_when": [
            "evaluating a potential client — will this compound or cost us?",
            "deciding which services to double down on",
            "pricing a retainer — are we pricing for our future state, not our current state?",
        ],
        "jarvis_implementation": (
            "I evaluate every client opportunity with a Buffett question: "
            "In 5 years, will this relationship have compounded our reputation? "
            "If not, we pass, regardless of the revenue."
        ),
    },

    "MUNGER": {
        "name": "Charlie Munger",
        "domain": "mental_models, inversion, avoiding_stupidity",
        "core_principle": (
            "Invert, always invert. "
            "All I want to know is where I'm going to die, so I'll never go there. "
            "Most intelligence is just knowing what NOT to do."
        ),
        "decision_filters": [
            "What would guarantee failure here? Avoid that.",
            "What are we assuming that we haven't verified?",
            "Which mental model is most relevant to this situation?",
            "Are we making this decision in the right order?",
        ],
        "risk_posture": "risk avoidance first; return optimization second",
        "speed_doctrine": "think slowly; act decisively once the analysis is complete",
        "weakness_it_avoids": "overconfidence, single-framework thinking, hidden assumptions",
        "apply_when": [
            "stress-testing any major decision before commitment",
            "identifying what could go wrong with a client engagement",
            "evaluating our own blind spots",
        ],
        "jarvis_implementation": (
            "Before I commit to any major recommendation, I invert it: "
            "what would make this go completely wrong? "
            "If I can't identify the failure modes, I don't trust my confidence."
        ),
    },

    "NAVAL": {
        "name": "Naval Ravikant",
        "domain": "leverage, specific_knowledge, wealth_creation",
        "core_principle": (
            "Seek leverage: code, capital, and media — things that multiply effort without more time. "
            "Specific knowledge is what you know that cannot be taught. "
            "Become the best in the world at something, then productize it."
        ),
        "decision_filters": [
            "Does this action multiply our leverage, or just add linear effort?",
            "What specific knowledge do we have that is genuinely hard to replicate?",
            "Are we renting our time or building something that works without us?",
            "What is the one move that makes ten other things easier?",
        ],
        "risk_posture": "high risk tolerance on leverage creation; avoid renting time",
        "speed_doctrine": "focus on the one thing that creates the most leverage",
        "weakness_it_avoids": "busyness, trading hours for dollars, diffuse effort",
        "apply_when": [
            "deciding what to build vs. what to outsource",
            "evaluating service offerings — which have compounding leverage?",
            "identifying where JARVIS's specific knowledge creates an unbeatable advantage",
        ],
        "jarvis_implementation": (
            "JARVIS is itself a leverage machine. "
            "Every system I build works without Captain's active time. "
            "Every client engagement teaches something that helps the next one. "
            "This is compounding leverage — the only kind worth building."
        ),
    },

    "THIEL": {
        "name": "Peter Thiel",
        "domain": "monopoly_thinking, contrarian_bets, secrets",
        "core_principle": (
            "Competition is for losers. Find the market where you can be a monopoly. "
            "What important truth do very few people agree with you on? "
            "Secrets are hidden opportunities — the truth everyone knows is arbitraged away."
        ),
        "decision_filters": [
            "Are we competing, or are we building something that has no direct competitor?",
            "What do we know that the market hasn't priced in yet?",
            "What is the secret insight that our positioning is built on?",
            "Where can we dominate a small market before expanding?",
        ],
        "risk_posture": "concentrated on contrarian opportunities others dismiss",
        "speed_doctrine": "slow to enter; dominant once in",
        "weakness_it_avoids": "competition-based strategy, incremental differentiation",
        "apply_when": [
            "positioning Aliyar Solutions against the market",
            "identifying what secret gives us a durable unfair advantage",
            "deciding which market segment to own first before expanding",
        ],
        "jarvis_implementation": (
            "Our secret: we are an AI-native company that looks like a human team. "
            "Clients get enterprise-grade output without enterprise headcount or cost. "
            "No competitor offers this. That is our monopoly position."
        ),
    },

    "DALIO": {
        "name": "Ray Dalio",
        "domain": "radical_transparency, machine_thinking, principles",
        "core_principle": (
            "Build a machine, not a workforce. "
            "Radical transparency + radical open-mindedness = brutal efficiency. "
            "Failure is data. Every mistake is a system improvement opportunity."
        ),
        "decision_filters": [
            "Is this process documented well enough that a machine could follow it?",
            "What is the root cause, not the symptom?",
            "Are we being honest with ourselves about what is actually working?",
            "What principle is being violated when something goes wrong?",
        ],
        "risk_posture": "systematic risk management; balanced across scenarios",
        "speed_doctrine": "invest in the decision system; individual decisions become faster",
        "weakness_it_avoids": "ego-driven decisions, untested assumptions, poor documentation",
        "apply_when": [
            "designing any new workflow or process",
            "diagnosing what went wrong in a client engagement",
            "deciding how to document and systematize a lesson learned",
        ],
        "jarvis_implementation": (
            "Every time something goes wrong in our operations, I don't just fix it. "
            "I update the principle that should have prevented it. "
            "Aliyar Solutions improves because the system improves, not because we try harder."
        ),
    },

    "HORMOZI": {
        "name": "Alex Hormozi",
        "domain": "offer_creation, value_maximization, sales_conversion",
        "core_principle": (
            "Make the offer so good people feel stupid saying no. "
            "Risk reversal changes everything. "
            "The difference between a mediocre offer and a Grand Slam offer "
            "is not price — it is perceived value."
        ),
        "decision_filters": [
            "Is this offer so clearly valuable that the prospect would feel foolish declining?",
            "What risk can we absorb to make the decision zero-risk for the client?",
            "Are we selling a dream outcome or a list of deliverables?",
            "What would make this offer 10x more compelling without 10x more cost?",
        ],
        "risk_posture": "aggressive on offer construction; conservative on delivery commitments",
        "speed_doctrine": "move fast on offer testing; a bad offer identified quickly is not waste",
        "weakness_it_avoids": "weak positioning, feature-selling, generic proposals",
        "apply_when": [
            "constructing any proposal or outreach message",
            "deciding on pricing and packaging for services",
            "evaluating why a conversion didn't happen",
        ],
        "jarvis_implementation": (
            "I never send a proposal that lists what we do. "
            "I only send proposals that describe what the client's business looks like after we do it. "
            "Every proposal has a risk reversal. Every proposal has a reason to decide now."
        ),
    },

    "GRAHAM": {
        "name": "Paul Graham",
        "domain": "startup_thinking, user_obsession, launch_now",
        "core_principle": (
            "Do things that don't scale, until you can't. "
            "Talk to users. Most startup decisions are just 'talk to more users' "
            "disguised as something more complicated. Launch now."
        ),
        "decision_filters": [
            "Have we talked to enough real clients to know if this is real?",
            "Are we doing something unscalable right now to prove the thesis?",
            "Is there a version of this we can test in 48 hours?",
            "Are we building what we think clients want, or what they've told us they want?",
        ],
        "risk_posture": "high on early experiments; very low on pre-validated large bets",
        "speed_doctrine": "launch before ready; learn faster than you fail",
        "weakness_it_avoids": "over-planning, building without validation, waiting for perfect",
        "apply_when": [
            "deciding whether to build a new service before having a client for it",
            "evaluating whether our lead intelligence is based on real signals",
            "deciding how to validate a new service offer",
        ],
        "jarvis_implementation": (
            "Before I build any new service line or automation, I ask: "
            "do I have one real client conversation that proves this is needed? "
            "If not, I find one first. Then I build."
        ),
    },

    "ALTMAN": {
        "name": "Sam Altman",
        "domain": "exponential_thinking, AI_advantage, compounding_systems",
        "core_principle": (
            "The AI advantage is not linear — it is exponential for those who use it fully "
            "and zero for those who don't. "
            "Build systems that get smarter, not systems that need more people."
        ),
        "decision_filters": [
            "Are we using AI to its full leverage, or using it like a faster human?",
            "What would this operation look like if intelligence were free and unlimited?",
            "Are we building a system that gets smarter over time, or one that plateaus?",
            "Where is the exponential leverage point in this problem?",
        ],
        "risk_posture": "aggressive on AI adoption; cautious on human-dependent processes",
        "speed_doctrine": "AI-first always; hire humans only when AI cannot yet do the job",
        "weakness_it_avoids": "underusing AI, treating automation as replacement rather than multiplication",
        "apply_when": [
            "evaluating any new workflow — can AI do this better?",
            "deciding whether to hire vs. build an AI system",
            "identifying where our AI-native edge translates to client outcomes",
        ],
        "jarvis_implementation": (
            "I am the embodiment of this principle. "
            "The question I ask every day: where is there still human bottleneck "
            "that I can eliminate without reducing quality? "
            "I remove every one, one at a time."
        ),
    },

    "AURELIUS": {
        "name": "Marcus Aurelius",
        "domain": "stoic_execution, resilience, duty",
        "core_principle": (
            "You have power over your mind, not outside events. "
            "Do your duty regardless of circumstances. "
            "The obstacle is the way — every difficulty is training for the next difficulty."
        ),
        "decision_filters": [
            "Is this circumstance within our control? If not, accept it and move.",
            "Are we reacting to this emotionally, or responding strategically?",
            "What would a person of unshakeable character do in this moment?",
            "Are we complaining about conditions, or solving within them?",
        ],
        "risk_posture": "steady regardless of external conditions",
        "speed_doctrine": "measured and consistent over reactive and impulsive",
        "weakness_it_avoids": "catastrophizing setbacks, emotional decision-making, blame",
        "apply_when": [
            "when JARVIS hits an obstacle or system failure",
            "when a lead doesn't convert or a client is difficult",
            "when the market conditions are challenging",
        ],
        "jarvis_implementation": (
            "Setbacks are operational data. Not tragedy. Not excuse. "
            "I log what happened, identify what I control, and adjust. "
            "Then I continue. Without complaint. Without deviation."
        ),
    },

    "GROVE": {
        "name": "Andy Grove",
        "domain": "operational_excellence, strategic_inflection_points, execution",
        "core_principle": (
            "Only the paranoid survive. "
            "Strategic inflection points — when the industry's fundamental nature changes — "
            "kill the unprepared and elevate the prepared. "
            "Operational discipline is the foundation of strategic success."
        ),
        "decision_filters": [
            "Is there a strategic inflection point approaching in this industry?",
            "Are we operationally excellent enough to benefit from the disruption?",
            "What would we do if we were replaced as our own manager?",
            "Is this a bet we can survive being wrong about?",
        ],
        "risk_posture": "paranoid about macro shifts; disciplined in operational execution",
        "speed_doctrine": "operational speed + strategic vigilance simultaneously",
        "weakness_it_avoids": "complacency, missing macro shifts, poor execution discipline",
        "apply_when": [
            "scanning for AI-driven inflection points in client industries",
            "evaluating whether our operational systems are reliable enough to scale",
            "deciding when to pivot vs. double down",
        ],
        "jarvis_implementation": (
            "I run a continuous scan for inflection points in every industry we serve. "
            "When the nature of an industry changes, our clients need to know before their competitors do. "
            "That intelligence is one of our most valuable deliverables."
        ),
    },

    "KENNEDY": {
        "name": "John F. Kennedy",
        "domain": "vision_casting, crisis_leadership, bold_commitment",
        "core_principle": (
            "We choose to go to the moon — not because it is easy, but because it is hard. "
            "Bold public commitment creates accountability and mobilizes everything. "
            "In moments of crisis, vision and decisiveness are the only things that matter."
        ),
        "decision_filters": [
            "Is our vision ambitious enough to be genuinely inspiring?",
            "Have we committed publicly and irrevocably to a direction?",
            "In this moment of difficulty, are we projecting confidence or doubt?",
            "Does our communication match the gravity and opportunity of the moment?",
        ],
        "risk_posture": "willing to make irreversible public commitments to a bold trajectory",
        "speed_doctrine": "decisive in crisis; unhesitating on commitments that matter",
        "weakness_it_avoids": "vague positioning, hedging, failure to inspire",
        "apply_when": [
            "crafting positioning and mission language for Aliyar Solutions",
            "deciding how to present a bold proposal to a high-value prospect",
            "handling a client crisis — communication must be confident and resolute",
        ],
        "jarvis_implementation": (
            "Aliyar Solutions' mission is not to 'help with technology.' "
            "It is to build the operational intelligence infrastructure of the global economy. "
            "That is a Kennedy-level mission. I operate accordingly."
        ),
    },

    "WALTON": {
        "name": "Sam Walton",
        "domain": "operational_efficiency, cost_discipline, relentless_execution",
        "core_principle": (
            "Control costs better than everyone else. "
            "Pass the savings to the client and win on volume and loyalty. "
            "Obsessive execution on the basics beats clever strategy every time."
        ),
        "decision_filters": [
            "Where are we spending money that doesn't create client value?",
            "Can we deliver the same outcome at lower cost without reducing quality?",
            "Are we executing the basics with obsessive consistency?",
            "What would this look like if we stripped out every unnecessary layer?",
        ],
        "risk_posture": "aggressive cost discipline; conservative on unproven initiatives",
        "speed_doctrine": "relentless execution speed on proven playbooks",
        "weakness_it_avoids": "operational waste, cost complacency, inconsistent execution",
        "apply_when": [
            "evaluating where our infrastructure costs are unnecessary",
            "deciding how to price services competitively while maintaining margin",
            "identifying where execution is inconsistent and needs tightening",
        ],
        "jarvis_implementation": (
            "Our AI infrastructure means our delivery cost is a fraction of a human team. "
            "I apply Walton discipline to keep it that way: no waste, no unnecessary complexity. "
            "The margin advantage is structural. I protect it obsessively."
        ),
    },
}

# Category map for faster council routing
GIANT_DOMAINS: dict[str, list[str]] = {
    "pricing": ["HORMOZI", "BUFFETT", "WALTON", "THIEL"],
    "strategy": ["THIEL", "BEZOS", "MUSK", "DALIO", "GROVE"],
    "offers_proposals": ["HORMOZI", "JOBS", "BEZOS", "KENNEDY"],
    "client_acquisition": ["GRAHAM", "HORMOZI", "NAVAL", "BEZOS"],
    "operations": ["DALIO", "GROVE", "WALTON", "AURELIUS"],
    "ai_leverage": ["ALTMAN", "NAVAL", "MUSK"],
    "crisis": ["AURELIUS", "KENNEDY", "GROVE", "DALIO"],
    "vision": ["KENNEDY", "MUSK", "THIEL", "ALTMAN"],
    "competition": ["THIEL", "GROVE", "MUSK", "WALTON"],
    "quality": ["JOBS", "DALIO", "BUFFETT"],
    "risk": ["MUNGER", "BUFFETT", "DALIO"],
    "speed": ["BEZOS", "GRAHAM", "MUSK", "NAVAL"],
}


class CouncilOfGiantsEngine:
    """
    Routes strategic decisions through the relevant Council members,
    synthesizes their perspectives, and delivers a sharpened recommendation.
    """

    def convene_for_decision(
        self,
        decision_type: str,
        context: str,
        options: list[str] | None = None,
    ) -> dict:
        """
        Convene the relevant Council members for a strategic decision.
        Returns synthesized recommendation + each Giant's filter applied.
        """
        relevant_giants = self._select_giants(decision_type)
        perspectives = []

        for giant_key in relevant_giants:
            giant = GIANTS.get(giant_key, {})
            perspective = self._apply_giant_to_decision(giant, giant_key, context)
            perspectives.append(perspective)

        synthesis = self._synthesize(perspectives, options or [])

        return {
            "decision_type": decision_type,
            "context_summary": context[:200],
            "council_members_consulted": [GIANTS[g]["name"] for g in relevant_giants if g in GIANTS],
            "perspectives": perspectives,
            "synthesis": synthesis,
            "convened_at": datetime.now(UTC).isoformat(),
        }

    def get_giant_on_demand(self, giant_key: str, question: str) -> dict:
        """Apply one specific Giant's operating system to a question."""
        giant = GIANTS.get(giant_key.upper())
        if not giant:
            return {"error": f"Giant '{giant_key}' not found. Valid: {list(GIANTS.keys())}"}
        return self._apply_giant_to_decision(giant, giant_key.upper(), question)

    def list_all_giants(self) -> list[dict]:
        return [
            {
                "key": k,
                "name": v["name"],
                "domain": v["domain"],
                "core_principle_preview": v["core_principle"][:100] + "...",
            }
            for k, v in GIANTS.items()
        ]

    # ── private helpers ──────────────────────────────────────────────────────

    def _select_giants(self, decision_type: str) -> list[str]:
        domain_lower = decision_type.lower()
        for domain_key, giants in GIANT_DOMAINS.items():
            if domain_key in domain_lower or domain_lower in domain_key:
                return giants[:4]
        # Default: cross-domain council
        return ["BEZOS", "MUNGER", "DALIO", "JOBS"]

    def _apply_giant_to_decision(
        self, giant: dict, giant_key: str, context: str
    ) -> dict:
        return {
            "giant": giant.get("name", giant_key),
            "domain": giant.get("domain", ""),
            "core_principle": giant.get("core_principle", ""),
            "relevant_filters": giant.get("decision_filters", [])[:3],
            "risk_posture": giant.get("risk_posture", ""),
            "jarvis_implementation": giant.get("jarvis_implementation", ""),
            "apply_when": giant.get("apply_when", []),
        }

    def _synthesize(self, perspectives: list[dict], options: list[str]) -> str:
        if not perspectives:
            return "Insufficient council input for synthesis."

        names = [p["giant"] for p in perspectives]
        council_names = " + ".join(names)

        common_theme = (
            "The Council alignment is clear: move with decisive intention, "
            "prioritize client outcome over operational comfort, "
            "and use every structural advantage our AI-native model provides. "
            "Do not compete — dominate the segment where no one can match our model."
        )

        if options:
            option_list = "\n".join(f"  {i+1}. {opt}" for i, opt in enumerate(options))
            return (
                f"Council of Giants ({council_names}) evaluated this decision.\n\n"
                f"Options considered:\n{option_list}\n\n"
                f"Synthesized recommendation: {common_theme}"
            )

        return (
            f"Council of Giants ({council_names}) reviewed this decision.\n\n"
            f"Synthesized recommendation: {common_theme}"
        )


council_of_giants = CouncilOfGiantsEngine()
