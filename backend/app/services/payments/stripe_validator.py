"""
Stripe configuration validator — ensures all payment gateway requirements are met.
Run on startup to catch missing Stripe keys before revenue operations begin.
"""
import logging
import httpx
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class StripeValidator:
    """Validates Stripe configuration and connectivity."""

    def __init__(self):
        self.secret_key = settings.STRIPE_SECRET_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        self.is_configured = bool(self.secret_key and self.webhook_secret)

    async def validate_keys(self) -> dict[str, bool]:
        """Validate that Stripe keys are present and usable."""
        issues = {}

        if not self.secret_key:
            issues["secret_key_missing"] = True
            logger.error("STRIPE_SECRET_KEY not configured — payments cannot be processed")
        elif not self.secret_key.startswith(("sk_live_", "sk_test_")):
            issues["secret_key_invalid_format"] = True
            logger.error("STRIPE_SECRET_KEY has invalid format (should start with sk_live_ or sk_test_)")

        if not self.webhook_secret:
            issues["webhook_secret_missing"] = True
            logger.error("STRIPE_WEBHOOK_SECRET not configured — cannot verify Stripe webhooks")
        elif not self.webhook_secret.startswith("whsec_"):
            issues["webhook_secret_invalid_format"] = True
            logger.error("STRIPE_WEBHOOK_SECRET has invalid format (should start with whsec_)")

        if not issues:
            logger.info("✓ Stripe keys validated: production-ready")

        return {
            "configured": not issues,
            "issues": issues,
        }

    async def validate_connectivity(self) -> dict[str, bool]:
        """Test that Stripe API is reachable and keys work."""
        if not self.secret_key:
            return {"connected": False, "error": "secret_key_missing"}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    "https://api.stripe.com/v1/account",
                    headers={"Authorization": f"Bearer {self.secret_key}"},
                )
            if r.status_code == 200:
                logger.info("✓ Stripe API connectivity verified")
                return {"connected": True}
            elif r.status_code == 401:
                logger.error("Stripe API: Invalid secret key (401 Unauthorized)")
                return {"connected": False, "error": "invalid_key"}
            else:
                logger.error("Stripe API error %s", r.status_code)
                return {"connected": False, "error": f"http_{r.status_code}"}
        except Exception as e:
            logger.error("Stripe connectivity check failed: %s", e)
            return {"connected": False, "error": str(e)}

    async def full_validation(self) -> dict:
        """Run all validation checks."""
        keys = await self.validate_keys()
        connectivity = await self.validate_connectivity() if keys["configured"] else {}
        return {
            "stripe": {
                "configured": self.is_configured,
                "keys": keys,
                "connectivity": connectivity,
            }
        }


stripe_validator = StripeValidator()
