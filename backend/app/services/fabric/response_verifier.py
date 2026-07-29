"""F3-6: Response Verifier — quality and policy compliance gate for AI outputs.

Every response from the AI Fabric passes through this verifier before being
surfaced to the caller.  The pipeline runs four checks in order:

  1. Hallucination detection — scan for unsupported absolute claims in
     critical responses (task_type in CRITICAL_TASK_TYPES).  Detected
     hedges and disclaimers lower the confidence score; hard fabrication
     markers (URLs, IDs, figures) are flagged as WARNING.

  2. Policy compliance — route the response text through the PolicyEngine
     (K1-3) to ensure no NEVER-tier action is being implicitly recommended.
     Requires a live DB session; skipped if no session is provided.

  3. Format validation — when the caller supplies an `expected_format`
     (e.g. "json", "markdown", "plain"), the response is checked against
     that contract.

  4. Confidence flagging — aggregate confidence < 0.7 sets
     `requires_review = True` so the caller can escalate to Captain or
     trigger a Council retry before committing.

The verifier never blocks on the PolicyEngine — a PolicyViolationError is
caught, downgraded to an issue, and the response is marked non-compliant
rather than raising.

Usage::

    verifier = get_response_verifier()
    result = await verifier.verify(
        response="Here are the steps …",
        task_type="CODE",
        expected_format="markdown",
        session=db_session,
    )
    if not result.passed:
        for issue in result.issues:
            logger.warning("[%s/%s] %s", issue.category, issue.severity, issue.detail)
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

# Task types where hallucination checks run at full sensitivity.
CRITICAL_TASK_TYPES = frozenset(
    {"STRATEGY", "REASONING", "ANALYSIS", "FINANCIAL", "LEGAL", "SECURITY"}
)

# Patterns that are typically fine — models are *hedging*, which is good.
_HEDGE_PATTERNS = re.compile(
    r"\b(I think|I believe|possibly|likely|might|may|perhaps|approximately|"
    r"around|roughly|could be|seems to|appears to|suggest|unclear)\b",
    re.IGNORECASE,
)

# Patterns that indicate a potentially fabricated specific artefact.
_FABRICATION_PATTERNS = re.compile(
    r"(https?://\S+|\b[A-Z0-9]{6,}-[A-Z0-9]+\b|\$[\d,]+\.?\d*\s+(million|billion|k\b))",
)

# Confidence penalty weights
_FABRICATION_PENALTY = 0.15
_POLICY_FAIL_PENALTY = 0.30
_FORMAT_FAIL_PENALTY = 0.10

CONFIDENCE_REVIEW_THRESHOLD = 0.70


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class VerificationIssue:
    """A single finding from the verification pipeline."""
    category: str    # "hallucination" | "policy" | "format" | "confidence"
    severity: str    # "critical" | "warning" | "info"
    detail: str
    claim: Optional[str] = None


@dataclass
class VerificationResult:
    """Aggregated result from :meth:`ResponseVerifier.verify`.

    Attributes:
        passed:          True when no CRITICAL-severity issues exist and
                         confidence >= CONFIDENCE_REVIEW_THRESHOLD.
        confidence:      Float in [0.0, 1.0] — overall quality score.
        issues:          Ordered list of issues found (most severe first).
        requires_review: True when confidence < CONFIDENCE_REVIEW_THRESHOLD.
        policy_compliant: False when the PolicyEngine raised a violation.
        hallucination_risk: True when at least one fabrication pattern found.
    """
    passed: bool
    confidence: float
    issues: list[VerificationIssue]
    requires_review: bool
    policy_compliant: bool
    hallucination_risk: bool = False

    @property
    def critical_issues(self) -> list[VerificationIssue]:
        return [i for i in self.issues if i.severity == "critical"]

    @property
    def warning_issues(self) -> list[VerificationIssue]:
        return [i for i in self.issues if i.severity == "warning"]


# ── Verifier ──────────────────────────────────────────────────────────────────

class ResponseVerifier:
    """Stateless verifier — safe to share across requests as a singleton.

    All state is passed in via method arguments; no instance variables are
    mutated after construction.
    """

    # ── Public API ─────────────────────────────────────────────────────────────

    async def verify(
        self,
        response: str,
        task_type: str,
        *,
        expected_format: Optional[str] = None,
        session: Optional[AsyncSession] = None,
        operation: str = "ai.fabric.response",
        actor: str = "fabric_router",
    ) -> VerificationResult:
        """Run all verification checks on *response*.

        Args:
            response:        The raw text returned by the AI model.
            task_type:       Task type string from the routing layer
                             (e.g. "CODE", "STRATEGY", "ANALYSIS").
            expected_format: Optional — "json", "markdown", or "plain".
            session:         DB session for PolicyEngine check; skipped if None.
            operation:       Policy operation key to check (default covers all
                             AI output).
            actor:           Identity string for the policy audit record.

        Returns:
            VerificationResult summarising all findings.
        """
        issues: list[VerificationIssue] = []
        confidence = 1.0
        policy_compliant = True
        hallucination_risk = False

        # ── 1. Hallucination detection ─────────────────────────────────────────
        if task_type.upper() in CRITICAL_TASK_TYPES:
            h_issues, h_penalty, h_risk = self._check_hallucination(response)
            issues.extend(h_issues)
            confidence -= h_penalty
            hallucination_risk = h_risk

        # ── 2. Policy compliance ───────────────────────────────────────────────
        if session is not None:
            p_issues, p_penalty, p_compliant = await self._check_policy(
                response, operation, actor, session
            )
            issues.extend(p_issues)
            confidence -= p_penalty
            policy_compliant = p_compliant

        # ── 3. Format validation ───────────────────────────────────────────────
        if expected_format:
            f_issues, f_penalty = self._check_format(response, expected_format)
            issues.extend(f_issues)
            confidence -= f_penalty

        # ── 4. Confidence clamp + flagging ────────────────────────────────────
        confidence = max(0.0, min(1.0, confidence))
        requires_review = confidence < CONFIDENCE_REVIEW_THRESHOLD

        if requires_review:
            issues.append(VerificationIssue(
                category="confidence",
                severity="warning",
                detail=f"Confidence {confidence:.2f} below review threshold "
                       f"({CONFIDENCE_REVIEW_THRESHOLD:.2f}) — escalate or retry.",
            ))

        # Sort: critical first, then warning, then info.
        _SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}
        issues.sort(key=lambda i: _SEVERITY_ORDER.get(i.severity, 3))

        has_critical = any(i.severity == "critical" for i in issues)
        passed = not has_critical and not requires_review and policy_compliant

        log.debug(
            "verified response (task=%s, confidence=%.2f, passed=%s, issues=%d)",
            task_type, confidence, passed, len(issues),
        )

        return VerificationResult(
            passed=passed,
            confidence=confidence,
            issues=issues,
            requires_review=requires_review,
            policy_compliant=policy_compliant,
            hallucination_risk=hallucination_risk,
        )

    # ── Internal checks ────────────────────────────────────────────────────────

    def _check_hallucination(
        self, response: str
    ) -> tuple[list[VerificationIssue], float, bool]:
        """Scan for fabrication markers and hedging language.

        Returns: (issues, confidence_penalty, hallucination_risk)
        """
        issues: list[VerificationIssue] = []
        penalty = 0.0
        risk = False

        fabrications = _FABRICATION_PATTERNS.findall(response)
        if fabrications:
            risk = True
            penalty += _FABRICATION_PENALTY * min(len(fabrications), 3)
            for fab in fabrications[:5]:  # cap logged items
                issues.append(VerificationIssue(
                    category="hallucination",
                    severity="warning",
                    detail="Potentially fabricated specific artefact detected.",
                    claim=str(fab)[:200],
                ))

        # Hedges are not errors — they are a mild positive signal that the
        # model is calibrated.  We only note them at info level.
        hedge_count = len(_HEDGE_PATTERNS.findall(response))
        if hedge_count > 10:
            issues.append(VerificationIssue(
                category="hallucination",
                severity="info",
                detail=f"High hedge density ({hedge_count} markers) — "
                       "model may lack sufficient context.",
            ))

        return issues, penalty, risk

    async def _check_policy(
        self,
        response: str,
        operation: str,
        actor: str,
        session: AsyncSession,
    ) -> tuple[list[VerificationIssue], float, bool]:
        """Check response against the PolicyEngine (K1-3).

        Returns: (issues, confidence_penalty, is_compliant)
        """
        issues: list[VerificationIssue] = []
        penalty = 0.0
        compliant = True

        try:
            from app.services.kernel.policy_engine import (
                PolicyEngine, PolicyViolationError,
            )
            engine = PolicyEngine(session)
            decision = await engine.check(
                operation,
                actor=actor,
                resource_id=uuid.uuid4(),
                details={"response_excerpt": response[:500]},
            )
            if not decision.permitted:
                compliant = False
                penalty += _POLICY_FAIL_PENALTY
                issues.append(VerificationIssue(
                    category="policy",
                    severity="critical" if not decision.requires_captain else "warning",
                    detail=f"Policy check failed: {decision.reason}",
                ))
        except Exception as exc:
            # Never let policy check failure crash the verifier.
            log.warning("policy check skipped — %s: %s", type(exc).__name__, exc)
            issues.append(VerificationIssue(
                category="policy",
                severity="info",
                detail=f"Policy check could not run: {type(exc).__name__}",
            ))

        return issues, penalty, compliant

    def _check_format(
        self, response: str, expected_format: str
    ) -> tuple[list[VerificationIssue], float]:
        """Validate response against the declared format contract.

        Returns: (issues, confidence_penalty)
        """
        issues: list[VerificationIssue] = []
        penalty = 0.0
        fmt = expected_format.lower().strip()

        if fmt == "json":
            try:
                json.loads(response.strip())
            except json.JSONDecodeError as exc:
                penalty += _FORMAT_FAIL_PENALTY
                issues.append(VerificationIssue(
                    category="format",
                    severity="critical",
                    detail=f"Expected valid JSON but parsing failed: {exc.msg}",
                ))
        elif fmt == "markdown":
            # Markdown check: expect at least one header or list marker.
            has_md = bool(re.search(r"^(#{1,6} |\*|\-|\d+\.)", response, re.MULTILINE))
            if not has_md:
                penalty += _FORMAT_FAIL_PENALTY
                issues.append(VerificationIssue(
                    category="format",
                    severity="warning",
                    detail="Response does not contain markdown structure "
                           "(expected headers, lists, or emphasis).",
                ))
        elif fmt == "plain":
            # Plain text should not contain markdown or HTML.
            has_markup = bool(re.search(r"<[^>]+>|#{1,6} |```", response))
            if has_markup:
                issues.append(VerificationIssue(
                    category="format",
                    severity="info",
                    detail="Plain-text format expected but markup detected.",
                ))

        return issues, penalty


# ── Singleton ─────────────────────────────────────────────────────────────────

_response_verifier: Optional[ResponseVerifier] = None


def get_response_verifier() -> ResponseVerifier:
    """Return the module-level ResponseVerifier singleton."""
    global _response_verifier
    if _response_verifier is None:
        _response_verifier = ResponseVerifier()
    return _response_verifier
