"""
JARVIS Prospect Psychology Engine — profiles buying styles, decision dynamics,
and personalisation hooks from raw lead data using keyword analysis + AI.
"""
from __future__ import annotations

import logging
from typing import Any
from datetime import datetime, timezone

from app.services.ai.base_provider import Message

logger = logging.getLogger(__name__)

# ── Keyword maps ──────────────────────────────────────────────────────────────

_STYLE_KEYWORDS: dict[str, list[str]] = {
    "ANALYTICAL": ["data", "metrics", "roi", "compliance", "audit", "analytics",
                   "reporting", "kpi", "benchmark", "forecast", "evidence", "measurement"],
    "DRIVER":     ["growth", "scale", "fast", "revenue", "results", "profit",
                   "expand", "aggressive", "performance", "dominate", "speed", "execute"],
    "AMIABLE":    ["team", "culture", "partnership", "relationship", "support",
                   "collaboration", "trust", "community", "together", "friendly", "care"],
    "EXPRESSIVE": ["innovative", "creative", "vision", "brand", "award", "disruptive",
                   "cutting-edge", "unique", "story", "design", "experience", "imagination"],
}

_APPROACH_MAP: dict[str, str] = {
    "ANALYTICAL": (
        "Lead with data, case studies, and measurable ROI. Provide detailed breakdowns, "
        "comparison matrices, and evidence-backed projections. Allow adequate evaluation time."
    ),
    "DRIVER": (
        "Lead with speed, outcomes, and competitive advantage. Keep it brief and results-focused. "
        "Propose a fast-start engagement with clear milestones and 30-day wins."
    ),
    "AMIABLE": (
        "Lead with relationship, trust-building, and team alignment. Emphasise long-term "
        "partnership, dedicated support, and seamless onboarding. Involve their stakeholders early."
    ),
    "EXPRESSIVE": (
        "Lead with vision, innovation, and brand impact. Use storytelling, bold ideas, "
        "and showcase creative possibilities. Spark enthusiasm before presenting details."
    ),
}

_HOOKS_MAP: dict[str, list[str]] = {
    "ANALYTICAL": [
        "Share a metrics dashboard mockup for their industry",
        "Reference a comparable ROI case study",
        "Offer a free audit or diagnostic report",
        "Provide a structured implementation timeline",
    ],
    "DRIVER": [
        "Highlight fastest time-to-value among comparable solutions",
        "Open with a bold revenue impact statement",
        "Propose a 30-day sprint to prove results",
        "Name-drop a high-growth client in their space",
    ],
    "AMIABLE": [
        "Assign a dedicated account lead from day one",
        "Offer a trial partnership with no long-term lock-in",
        "Reference testimonials focused on team experience",
        "Propose a collaborative kickoff workshop",
    ],
    "EXPRESSIVE": [
        "Present a vision board or concept design for their brand",
        "Share an innovative feature not available elsewhere",
        "Use narrative — tell the story of a transformation",
        "Invite them to co-create the solution with our team",
    ],
}

_OBJECTION_MAP: dict[str, list[str]] = {
    "ANALYTICAL": [
        "Insufficient data to prove ROI before commitment",
        "Unclear SLAs or performance guarantees",
        "Integration complexity with existing reporting stack",
    ],
    "DRIVER": [
        "Implementation timeline feels too slow",
        "Unclear who owns outcomes on our team",
        "Competitors may offer faster deployment",
    ],
    "AMIABLE": [
        "Concerned about disruption to current team dynamics",
        "Wants reassurance of ongoing dedicated support",
        "Risk aversion — prefers proven over innovative",
    ],
    "EXPRESSIVE": [
        "Solution feels too generic or off-the-shelf",
        "Needs to see creative differentiation before buying",
        "May stall waiting for internal champion buy-in",
    ],
}


def _extract_text(lead: dict[str, Any]) -> str:
    """Flatten relevant fields into a single searchable string."""
    fields = [
        lead.get("company_name", ""),
        lead.get("company", ""),
        lead.get("industry", ""),
        lead.get("notes", ""),
        " ".join(str(p) for p in (lead.get("pain_points") or [])),
        str(lead.get("enrichment_data", {})),
        lead.get("opportunity_type", ""),
    ]
    return " ".join(str(f) for f in fields if f).lower()


def _score_style(text: str) -> dict[str, int]:
    scores: dict[str, int] = {style: 0 for style in _STYLE_KEYWORDS}
    for style, keywords in _STYLE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[style] += 1
    return scores


def _infer_risk_tolerance(style: str, lead: dict[str, Any]) -> str:
    text = _extract_text(lead)
    if any(w in text for w in ["startup", "seed", "series a", "early"]):
        return "HIGH"
    if any(w in text for w in ["enterprise", "fortune", "regulated", "compliance", "bank"]):
        return "LOW"
    if style in ("DRIVER", "EXPRESSIVE"):
        return "MEDIUM"
    return "LOW"


def _infer_decision_speed(style: str, lead: dict[str, Any]) -> str:
    text = _extract_text(lead)
    if any(w in text for w in ["urgent", "asap", "immediately", "this quarter", "fast"]):
        return "FAST"
    if style == "DRIVER":
        return "FAST"
    if style == "ANALYTICAL":
        return "METHODICAL"
    return "METHODICAL"


def _extract_urgency_signals(lead: dict[str, Any]) -> list[str]:
    signals: list[str] = []
    text = _extract_text(lead)
    urgency_phrases = {
        "budget approved": "Budget already approved — purchase intent high",
        "q4": "Q4 timing pressure — fiscal year deadline",
        "launch": "Upcoming product launch creating urgency",
        "replacing": "Replacing existing solution — active pain",
        "asap": "Explicitly requested fast turnaround",
        "losing": "Competitive loss risk driving urgency",
        "deadline": "Hard deadline mentioned",
        "already decided": "Decision already made — needs execution partner",
    }
    for phrase, signal in urgency_phrases.items():
        if phrase in text:
            signals.append(signal)
    if lead.get("score", 0) >= 80:
        signals.append("High lead score (≥80) signals strong fit and intent")
    return signals or ["No explicit urgency signals detected — nurture cadence recommended"]


class ProspectPsychologyEngine:
    """Profiles a prospect's psychological buying style from lead data."""

    def profile(self, lead: dict[str, Any]) -> dict[str, Any]:
        text = _extract_text(lead)
        style_scores = _score_style(text)
        buying_style = max(style_scores, key=lambda s: style_scores[s])
        # Default to DRIVER if all scores are zero
        if all(v == 0 for v in style_scores.values()):
            buying_style = "DRIVER"

        risk_tolerance = _infer_risk_tolerance(buying_style, lead)
        decision_speed = _infer_decision_speed(buying_style, lead)
        urgency_signals = _extract_urgency_signals(lead)

        return {
            "buying_style": buying_style,
            "style_scores": style_scores,
            "risk_tolerance": risk_tolerance,
            "decision_speed": decision_speed,
            "urgency_signals": urgency_signals,
            "objection_forecast": _OBJECTION_MAP[buying_style],
            "recommended_approach": _APPROACH_MAP[buying_style],
            "personalization_hooks": _HOOKS_MAP[buying_style],
            "profiled_at": datetime.now(timezone.utc).isoformat(),
        }

    async def analyze_with_ai(self, lead: dict[str, Any], tenant_id: Any) -> dict[str, Any]:
        """Augments the heuristic profile with an AI-generated deep analysis."""
        from app.services.ai.router import ai_router

        base_profile = self.profile(lead)
        lead_summary = (
            f"Company: {lead.get('company_name') or lead.get('company', 'Unknown')}\n"
            f"Industry: {lead.get('industry', 'Unknown')}\n"
            f"Pain Points: {lead.get('pain_points', [])}\n"
            f"Notes: {lead.get('notes', '')}\n"
            f"Lead Score: {lead.get('score', 0)}\n"
            f"Initial Profile: {base_profile['buying_style']} / {base_profile['risk_tolerance']} risk"
        )
        system_prompt = (
            "You are JARVIS, the operational intelligence of Aliyar Solutions. "
            "Analyse this B2B prospect's psychological profile for a high-value technology sale. "
            "Return ONLY valid JSON with keys: executive_summary (str), "
            "emotional_triggers (list[str]), hidden_fears (list[str]), "
            "ideal_pitch_opening (str), closing_strategy (str), "
            "cultural_context (str), confidence_score (float 0-1)."
        )
        messages = [Message(role="user", content=f"Prospect profile:\n{lead_summary}")]
        try:
            response, _ = await ai_router.chat(
                messages,
                system_prompt=system_prompt,
                task_type="REASONING",
            )
            import json as _json
            ai_insights = _json.loads(response.content or "{}")
        except Exception as exc:
            logger.warning("AI psychology analysis failed: %s", exc)
            ai_insights = {"executive_summary": "AI analysis unavailable", "confidence_score": 0.0}

        return {**base_profile, "ai_insights": ai_insights}


prospect_psychology_engine = ProspectPsychologyEngine()
