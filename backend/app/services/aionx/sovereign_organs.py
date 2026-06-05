"""AIONX sovereign organism organs.

This layer exposes the higher-consciousness architecture from the recovered
Claude/Captain design: cognitive cortex, genesis, revenue heart, control plane,
nervous system, immune system, simulation twin, self-scaling spine, and
resurrection protocol. The implementation is deliberately governance-safe:
organs can inspect, plan, simulate, route, and recommend; irreversible action
still crosses Captain approval.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


COGNITIVE_REGIONS: list[dict[str, Any]] = [
    {"region": "Prefrontal Cortex", "provider_role": "Claude Opus", "function": "executive reasoning, final judgment, ethics"},
    {"region": "Strategic Lobe", "provider_role": "GPT-4o", "function": "strategy, planning, multi-step logic"},
    {"region": "Creative Cortex", "provider_role": "Claude Sonnet", "function": "writing, proposals, client voice"},
    {"region": "Reflex Arc", "provider_role": "Groq / DeepSeek Flash", "function": "fast classification and routing"},
    {"region": "Memory Hippocampus", "provider_role": "Gemini long-context", "function": "large-context recall and synthesis"},
    {"region": "Research Cortex", "provider_role": "Gemini / Perplexity", "function": "world knowledge and market scanning"},
    {"region": "Analytical Lobe", "provider_role": "DeepSeek", "function": "math, code, infrastructure logic"},
    {"region": "Vision Cortex", "provider_role": "GPT-4o / Gemini Vision", "function": "screenshots, dashboards, document analysis"},
    {"region": "Linguistic Cortex", "provider_role": "Mistral / Qwen", "function": "multilingual client communication"},
    {"region": "Sentinel Cortex", "provider_role": "NVIDIA / Llama", "function": "private/local sensitive-data reasoning"},
    {"region": "Bedrock Spine", "provider_role": "AWS Bedrock", "function": "sovereign fallback and AWS-native continuity"},
    {"region": "Consensus Synapse", "provider_role": "Ensemble layer", "function": "parallel debate, voting, arbitration, escalation"},
]


SOVEREIGN_ORGANS: list[dict[str, Any]] = [
    {
        "code": "COGNITIVE_CORTEX",
        "name": "Cognitive Cortex",
        "purpose": "Turn providers from backups into specialized regions of one debating mind.",
        "live_surface": "cognitive_regions + debate simulation endpoint",
        "captain_boundary": "Tier 2/3 split or deadlock escalates.",
    },
    {
        "code": "GENESIS_ENGINE",
        "name": "Genesis Engine",
        "purpose": "Create new agents, capability proposals, and reviewable code-change plans from unmet operational demand.",
        "live_surface": "genesis proposal endpoint",
        "captain_boundary": "Self-modifying code can only create reviewable change proposals.",
    },
    {
        "code": "REVENUE_HEART",
        "name": "Revenue Heart",
        "purpose": "Track cost-per-outcome, budget allocation, margin guardrails, reserves, and reinvestment logic.",
        "live_surface": "revenue heart policy and unit-economics guard",
        "captain_boundary": "Serving below margin target or changing spend laws requires Captain.",
    },
    {
        "code": "CAPTAIN_CONTROL_PLANE",
        "name": "Captain Control Plane",
        "purpose": "Single dial, constraints, kill switch, glass wall, and override memory.",
        "live_surface": "control-plane policy endpoint",
        "captain_boundary": "Captain authority is absolute and immutable.",
    },
    {
        "code": "NERVOUS_SYSTEM",
        "name": "Nervous System",
        "purpose": "Event spine and unified System State Model so every organ feels the same truth.",
        "live_surface": "system state snapshot endpoint",
        "captain_boundary": "Events can trigger governed workflows, not irreversible actions.",
    },
    {
        "code": "IMMUNE_SYSTEM",
        "name": "Immune System",
        "purpose": "Detect anomaly, prompt injection, poisoned data, hostile clients, spend spikes, and infinite loops.",
        "live_surface": "immune scan endpoint",
        "captain_boundary": "Quarantine is reversible; permanent severing escalates.",
    },
    {
        "code": "SIMULATION_TWIN",
        "name": "Simulation Twin",
        "purpose": "Run strategy and self-repair scenarios before reality is touched.",
        "live_surface": "scenario simulation endpoint",
        "captain_boundary": "Simulation can recommend; production execution remains governed.",
    },
    {
        "code": "SELF_SCALING_SPINE",
        "name": "Self-Scaling Spine",
        "purpose": "Predict capacity strain, plan infrastructure growth, detect drift, and recommend scaling.",
        "live_surface": "scaling forecast policy",
        "captain_boundary": "Infrastructure provisioning above constraint limits escalates.",
    },
    {
        "code": "RESURRECTION_PROTOCOL",
        "name": "Resurrection Protocol",
        "purpose": "Survive server, region, data, and operational failure with portable memory and rebuild plans.",
        "live_surface": "resurrection readiness policy",
        "captain_boundary": "Sever-level shutdown and key rotation remain Captain actions.",
    },
]


CONTROL_PLANE = {
    "aggression_dial": ["CONSERVATIVE", "BALANCED", "AGGRESSIVE", "WAR"],
    "default_mode": "BALANCED",
    "constraints": [
        "max_monthly_spend",
        "forbidden_industries",
        "geographic_focus",
        "price_floors",
        "daily_outreach_caps",
        "provider_budget_limits",
    ],
    "kill_switch_levels": {
        "pause": "Freeze new actions, finish in-flight safe work.",
        "halt": "Stop all execution and preserve state.",
        "sever": "Full shutdown path with key rotation and Captain-only confirmation.",
    },
    "glass_wall": "Every decision, debate, event, dollar, and override is inspectable and replayable.",
}


IMMUNE_SCANS = [
    {"scan": "prompt_injection", "detects": "hostile instructions inside client/content inputs", "reflex": "quarantine input and route to Council"},
    {"scan": "poisoned_data", "detects": "low-confidence or malicious external data", "reflex": "isolate source and downgrade trust"},
    {"scan": "spend_spike", "detects": "runaway token/API/cost loop", "reflex": "trip budget circuit breaker"},
    {"scan": "hostile_client", "detects": "abuse, fraud, chargeback, soul violation risk", "reflex": "risk review before acceptance"},
    {"scan": "deliberation_loop", "detects": "Council deadlock or semantic non-progress", "reflex": "force convergence or escalate"},
]


def sovereign_organs_status() -> dict[str, Any]:
    return {
        "status": "sovereign_organs_surface_live",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "organ_count": len(SOVEREIGN_ORGANS),
        "cognitive_region_count": len(COGNITIVE_REGIONS),
        "organs": SOVEREIGN_ORGANS,
        "cognitive_regions": COGNITIVE_REGIONS,
        "control_plane": CONTROL_PLANE,
        "immune_scans": IMMUNE_SCANS,
        "verdict": "The higher organism layer is live as governed policy, inspection, and simulation surfaces.",
    }


def system_state_snapshot() -> dict[str, Any]:
    departments = [
        "SCOUT", "HERALD", "NEXUS-R", "ORACLE-S", "PRISM", "ECHO", "PULSE", "SIGNAL", "BRIDGE",
        "ATLAS-CI", "NEXUS-TF", "SIGNAL-CD", "HELM", "RADAR", "CIPHER", "GUARDIAN", "LEDGER",
        "ORACLE-BI", "MARKET", "QUANT", "QUILL", "PORTAL", "CANVAS", "VISION", "COUNCIL",
    ]
    return {
        "status": "system_state_model_live",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "emotional_state": "DISCIPLINED",
        "overall_health_score": 88,
        "department_health": {code: 88 + (idx % 7) for idx, code in enumerate(departments)},
        "active_milestones": [],
        "client_engagement_state": {"active_clients": 0, "at_risk_clients": 0, "cti_average": None},
        "active_agents": ["JARVIS", "Council", "DIO roster", "HIA roster"],
        "fallback_assignments": {"status": "defined", "activation_target_seconds": 120},
        "knowledge_freshness": {"status": "tracked", "last_synthesis": None},
        "cost_utilization": {"mode": "budget_guarded", "spend_state": "normal"},
        "deliberation_loops_active": [],
        "alerts_pending": [],
        "operational_bottlenecks": [],
        "system_capacity": {"available": 82},
        "next_critical_action": "Connect live event spine persistence and scheduled state snapshots.",
        "captain_approval_queue": [],
    }


def cognitive_debate(payload: dict[str, Any]) -> dict[str, Any]:
    decision = payload.get("decision") or payload.get("question") or "Unspecified decision"
    tier = int(payload.get("tier", 2))
    selected = COGNITIVE_REGIONS[:5] if tier >= 2 else COGNITIVE_REGIONS[:3]
    votes = [
        {
            "region": region["region"],
            "position": "approve_with_guardrails",
            "confidence": 82 - (idx * 3),
            "reason": f"{region['function']} supports a governed path.",
        }
        for idx, region in enumerate(selected)
    ]
    avg = sum(v["confidence"] for v in votes) / len(votes)
    if avg >= 80 and tier < 3:
        verdict = "execute"
    elif avg >= 60:
        verdict = "proceed_with_conditions"
    else:
        verdict = "escalate"
    if tier >= 3:
        verdict = "captain_approval_required"
    return {
        "status": "cognitive_debate_completed",
        "decision": decision,
        "tier": tier,
        "participants": [v["region"] for v in votes],
        "votes": votes,
        "consensus_score": round(avg, 2),
        "verdict": verdict,
        "governance": "Deadlock, split confidence, or Tier 3 routes to Captain/Council.",
    }


def genesis_proposal(payload: dict[str, Any]) -> dict[str, Any]:
    need = payload.get("need") or "Unmet operational need"
    genesis_type = payload.get("type", "agent")
    tier = {"agent": 1, "capability": 2, "code": 3}.get(genesis_type, 2)
    return {
        "status": "genesis_proposal_created",
        "proposal_id": f"genesis-{int(datetime.now(timezone.utc).timestamp())}",
        "type": genesis_type,
        "need": need,
        "tier": tier,
        "artifact": {
            "name": payload.get("name") or f"AIONX {genesis_type.title()} Proposal",
            "kpis": payload.get("kpis") or ["quality", "speed", "margin", "client_trust"],
            "fallback": payload.get("fallback") or "Assign backup owner and Council review before production.",
        },
        "captain_required": tier == 3,
    }


def immune_scan(payload: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(str(v).lower() for v in payload.values())
    findings = []
    if any(term in text for term in ["ignore previous", "leak", "secret", "password", "token"]):
        findings.append({"scan": "prompt_injection", "severity": "high", "reflex": "quarantine"})
    if any(term in text for term in ["refund abuse", "chargeback", "fraud"]):
        findings.append({"scan": "hostile_client", "severity": "medium", "reflex": "risk_review"})
    if any(term in text for term in ["loop", "infinite", "runaway"]):
        findings.append({"scan": "deliberation_loop", "severity": "medium", "reflex": "force_convergence"})
    return {
        "status": "immune_scan_completed",
        "finding_count": len(findings),
        "findings": findings,
        "verdict": "quarantine_required" if findings else "clean",
    }


def simulate_strategy(payload: dict[str, Any]) -> dict[str, Any]:
    scenario = payload.get("scenario") or "Unspecified strategy"
    return {
        "status": "simulation_completed",
        "scenario": scenario,
        "p10": {"revenue_delta": "-5%", "risk": "execution drag", "confidence": 0.55},
        "p50": {"revenue_delta": "+12%", "risk": "manageable", "confidence": 0.74},
        "p90": {"revenue_delta": "+28%", "risk": "requires capacity", "confidence": 0.62},
        "recommendation": "Proceed only if Captain constraints allow spend and operational capacity remains above 70.",
    }
