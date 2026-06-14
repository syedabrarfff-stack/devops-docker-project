"""
Credential validation system — monitors all API keys, tokens, and secrets.
Reports missing or invalid credentials to dashboard and Captain via Slack/Telegram.
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class CredentialSeverity(str, Enum):
    """Credential severity levels."""
    CRITICAL = "critical"  # Blocks core revenue operations
    HIGH = "high"         # Degrades important capabilities
    MEDIUM = "medium"     # Nice-to-have; not blocking
    LOW = "low"           # Optional enhancements


@dataclass
class CredentialStatus:
    """Status of a single credential."""
    name: str
    env_var: str
    configured: bool
    severity: CredentialSeverity
    impact: str


class CredentialValidator:
    """Validates all configured credentials against requirements."""

    CREDENTIALS = [
        # ─── CRITICAL (Revenue Operations) ─────────────────────────────
        CredentialStatus(
            name="Stripe Secret Key",
            env_var="STRIPE_SECRET_KEY",
            configured=bool(settings.STRIPE_SECRET_KEY),
            severity=CredentialSeverity.CRITICAL,
            impact="Payment processing — cannot invoice or collect revenue without this",
        ),
        CredentialStatus(
            name="Stripe Webhook Secret",
            env_var="STRIPE_WEBHOOK_SECRET",
            configured=bool(settings.STRIPE_WEBHOOK_SECRET),
            severity=CredentialSeverity.CRITICAL,
            impact="Payment webhook verification — cannot safely process Stripe payments",
        ),
        CredentialStatus(
            name="Slack Webhook URL",
            env_var="SLACK_WEBHOOK_URL",
            configured=bool(settings.SLACK_WEBHOOK_URL) and not settings.SLACK_WEBHOOK_URL.endswith("test"),
            severity=CredentialSeverity.CRITICAL,
            impact="Captain notifications — cannot alert on critical events",
        ),

        # ─── HIGH (Core Automation) ────────────────────────────────────
        CredentialStatus(
            name="Telegram Bot Token",
            env_var="TELEGRAM_BOT_TOKEN",
            configured=bool(settings.TELEGRAM_BOT_TOKEN) and not settings.TELEGRAM_BOT_TOKEN.startswith("test"),
            severity=CredentialSeverity.HIGH,
            impact="Bot messaging — cannot send alerts via Telegram",
        ),
        CredentialStatus(
            name="Telegram Chat ID",
            env_var="TELEGRAM_CHAT_ID",
            configured=bool(settings.TELEGRAM_CHAT_ID),
            severity=CredentialSeverity.HIGH,
            impact="Bot targeting — Telegram bot cannot send messages to Captain",
        ),
        CredentialStatus(
            name="Anthropic API Key",
            env_var="ANTHROPIC_API_KEY",
            configured=bool(settings.ANTHROPIC_API_KEY),
            severity=CredentialSeverity.HIGH,
            impact="Strategic AI reasoning — cannot use Claude for proposals/strategy",
        ),

        # ─── MEDIUM (Enhanced Capabilities) ────────────────────────────
        CredentialStatus(
            name="NVIDIA NIM Keys",
            env_var="NVIDIA_API_KEY*",
            configured=bool(settings.NVIDIA_API_KEY),
            severity=CredentialSeverity.MEDIUM,
            impact="Multi-model AI routing — cannot use Llama/DeepSeek/Qwen via NIM",
        ),
        CredentialStatus(
            name="Google Maps API Key",
            env_var="GOOGLE_MAPS_API_KEY",
            configured=bool(settings.GOOGLE_MAPS_API_KEY),
            severity=CredentialSeverity.MEDIUM,
            impact="Lead discovery — cannot discover local business prospects",
        ),
        CredentialStatus(
            name="AWS Credentials",
            env_var="AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY",
            configured=bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY),
            severity=CredentialSeverity.MEDIUM,
            impact="SES email + S3 storage — cannot send outreach emails or backup data",
        ),

        # ─── LOW (Optional) ────────────────────────────────────────────
        CredentialStatus(
            name="OpenAI API Key",
            env_var="OPENAI_API_KEY",
            configured=bool(settings.OPENAI_API_KEY) and not settings.OPENAI_API_KEY.startswith("sk-test"),
            severity=CredentialSeverity.LOW,
            impact="GPT-4o fallback — nice-to-have but not required with NIM + Claude",
        ),
    ]

    @classmethod
    def validate_all(cls) -> dict:
        """Return complete credential validation report."""
        by_severity = {
            CredentialSeverity.CRITICAL: [],
            CredentialSeverity.HIGH: [],
            CredentialSeverity.MEDIUM: [],
            CredentialSeverity.LOW: [],
        }

        for cred in cls.CREDENTIALS:
            if not cred.configured:
                by_severity[cred.severity].append(cred)

        return {
            "configured_count": len([c for c in cls.CREDENTIALS if c.configured]),
            "missing_count": len([c for c in cls.CREDENTIALS if not c.configured]),
            "critical_missing": by_severity[CredentialSeverity.CRITICAL],
            "high_missing": by_severity[CredentialSeverity.HIGH],
            "medium_missing": by_severity[CredentialSeverity.MEDIUM],
            "low_missing": by_severity[CredentialSeverity.LOW],
        }

    @classmethod
    def can_process_revenue(cls) -> tuple[bool, list[str]]:
        """Check if system can process revenue (all CRITICAL creds present)."""
        report = cls.validate_all()
        if report["critical_missing"]:
            reasons = [c.impact for c in report["critical_missing"]]
            return False, reasons
        return True, []

    @classmethod
    def alert_message(cls) -> Optional[str]:
        """Generate alert message for missing CRITICAL/HIGH credentials."""
        report = cls.validate_all()
        critical = report["critical_missing"]
        high = report["high_missing"]

        if not critical and not high:
            return None

        lines = ["⚠️ *Missing Credentials Alert*\n"]
        if critical:
            lines.append("*CRITICAL (Block Revenue):*")
            for c in critical:
                lines.append(f"  • {c.name} ({c.env_var})")
                lines.append(f"    → {c.impact}")
        if high:
            lines.append("\n*HIGH (Degrade Ops):*")
            for c in high:
                lines.append(f"  • {c.name} ({c.env_var})")
                lines.append(f"    → {c.impact}")

        return "\n".join(lines)


validator = CredentialValidator()
