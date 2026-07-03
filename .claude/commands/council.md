---
description: Assemble the AI Council on a high-stakes decision
argument-hint: <question or decision to reason about>
---

Assemble the JARVIS AI Council on: **$ARGUMENTS**

1. Run the existing council system: `cd council && python3 council.py "$ARGUMENTS"`.
   This fans the question out to the 14 registered models (Claude Opus 4.8 via
   Bedrock as chief synthesizer, Claude Sonnet, 10 NVIDIA NIM models, Gemini,
   OpenRouter) and produces a synthesized verdict, saved to `council/sessions/`.

2. As Claude, add your own independent review pass on top of the synthesized
   verdict per the v4 Council workflow (`JARVIS_V4_ARCHITECTURE.md` §4.4):
   - Does the reasoning hold up? Any disagreements among members worth surfacing?
   - Confidence score — is it ≥ 0.75 (actionable) or does this need Captain input?
   - What's the recommendation: AUTO-execute, ASK Captain, or NEVER?

3. If this decision is going to change production code or infrastructure, produce
   a decision record (problem, evidence, confidence, impact, risk, rollback,
   success criteria) before any action is taken — per the locked engineering workflow.

4. Report the verdict + your review + recommendation. Do not execute anything
   beyond ASK-tier without explicit Captain approval.
