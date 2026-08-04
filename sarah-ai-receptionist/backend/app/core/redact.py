"""
PII redaction helpers for log lines.

The system logs to CloudWatch, whose default retention (per the current
Terraform) is longer than most PHI-retention policies. Logging a patient's
phone number verbatim in an SMS-failure line puts that phone in log
archives forever, indexable by anyone with CloudWatch read.

These helpers give a call site one obvious way to log identifiers without
disclosing the whole value: `redact_phone("+15551234567") == "+15***4567"`.
Enough for an operator to correlate a specific number with another log line
about the same call (still-unique for their small caller volume), without
exposing the full identifier at scale.
"""

from __future__ import annotations


def redact_phone(phone: str | None) -> str:
    """Keeps the first 2 and last 4 characters, masks the middle.

    A phone number is not sensitive in isolation, but tens of thousands
    aggregated across a HIPAA covered entity's callers is a leak we don't
    want writing itself into CloudWatch logs. This preserves enough for a
    human to notice "same person as line 47" without preserving the whole
    identifier.
    """
    if not phone:
        return "<none>"
    s = str(phone)
    if len(s) <= 6:
        return "***"
    return f"{s[:2]}***{s[-4:]}"


def redact_email(email: str | None) -> str:
    """Keeps first char of local part + domain: 'j***@example.com'."""
    if not email or "@" not in email:
        return "<none>"
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}" if local else f"***@{domain}"
