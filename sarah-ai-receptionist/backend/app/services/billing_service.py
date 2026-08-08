"""
Stripe billing — customer/subscription creation on clinic onboarding, and the
webhook handler that keeps Subscription/Clinic status in sync with Stripe.

Previously Subscription/stripe_customer_id existed only as columns nothing
wrote to; this wires them to the actual Stripe SDK so a clinic can be billed.
"""

import logging
from datetime import datetime, timedelta, timezone

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.models.clinic import Clinic
from app.models.subscription import Subscription

logger = logging.getLogger(__name__)
settings = get_settings()

TRIAL_DAYS = 14
DEFAULT_PLAN = "starter"
# Saudi Arabia / GCC is now the primary go-to-market (see CLAUDE.md) -- new
# clinics default to SAR pricing. This is local tracking only; the currency
# actually charged comes from whatever Stripe Price `settings.stripe_price_id`
# points at, which must itself be a SAR-denominated Price created in the
# Stripe Dashboard before this reflects reality.
DEFAULT_MONTHLY_PRICE = 1099.0
DEFAULT_CURRENCY = "SAR"


class BillingSetupResult:
    """Outcome of the billing side of onboarding, so the caller can tell
    'billed for real' from 'local-only tracking' from 'Stripe blew up' -- the
    original returned Subscription lost that distinction, so the API had no
    way to warn a human 'this clinic isn't actually being charged'."""

    def __init__(self, subscription: Subscription, stripe_created: bool, error: str | None = None):
        self.subscription = subscription
        self.stripe_created = stripe_created
        self.error = error


async def create_stripe_customer_and_subscription(
    db: AsyncSession, clinic: Clinic, admin_email: str
) -> BillingSetupResult:
    """Creates the local Subscription row and, if Stripe is configured, a real
    Stripe Customer + Subscription against the configured Price so the clinic
    is actually charged after the trial.

    The previous implementation created a Customer only -- no Product, no
    Price, no Subscription -- so `customer.subscription.*` webhooks would
    never fire and no clinic ever got billed. That was a silent revenue leak
    disguised as working billing code.

    Never raises out to the caller: onboarding an *organization* is the value
    the user paid for with their time; a Stripe API blip must not block it,
    but must be surfaced in the return so a human sees the gap.
    """
    now = datetime.now(timezone.utc)
    trial_ends_at = now + timedelta(days=TRIAL_DAYS)

    subscription = Subscription(
        clinic_id=clinic.id,
        plan=DEFAULT_PLAN,
        monthly_price=DEFAULT_MONTHLY_PRICE,
        currency=DEFAULT_CURRENCY,
        status="trialing",
        current_period_start=now,
        current_period_end=trial_ends_at,
        trial_ends_at=trial_ends_at,
    )
    db.add(subscription)
    await db.flush()

    if not settings.stripe_secret_key:
        logger.warning("STRIPE_SECRET_KEY not configured — clinic %s tracked locally only", clinic.id)
        return BillingSetupResult(subscription, stripe_created=False,
                                  error="stripe_secret_key not configured")
    if not settings.stripe_price_id:
        # Distinct from missing api key: an operator forgot to point at a
        # Price, so nothing charges even though Stripe is "wired up".
        logger.error(
            "STRIPE_PRICE_ID not configured — cannot start real subscription for clinic %s; "
            "created Customer only will not be billed", clinic.id,
        )
        return BillingSetupResult(subscription, stripe_created=False,
                                  error="stripe_price_id not configured")

    try:
        stripe.api_key = settings.stripe_secret_key
        customer = stripe.Customer.create(
            email=admin_email,
            name=clinic.name,
            metadata={"clinic_id": clinic.id},
        )
        stripe_sub = stripe.Subscription.create(
            customer=customer.id,
            items=[{"price": settings.stripe_price_id}],
            trial_period_days=TRIAL_DAYS,
            # Straight to canceled on failed payment: dental practices are
            # low-touch; a past_due state that lingers indefinitely while
            # Sarah keeps answering their phone is worse than a hard stop
            # they'll notice and call about.
            payment_behavior="default_incomplete",
            metadata={"clinic_id": clinic.id},
        )
        clinic.stripe_customer_id = customer.id
        clinic.stripe_subscription_id = stripe_sub.id
        subscription.stripe_customer_id = customer.id
        subscription.stripe_subscription_id = stripe_sub.id
        await db.flush()
        logger.info("Stripe subscription %s created for clinic %s", stripe_sub.id, clinic.id)
        return BillingSetupResult(subscription, stripe_created=True)
    except Exception as e:
        # The local Subscription is already flushed; Stripe just didn't line
        # up. Log the specifics for reconciliation, but do not raise.
        logger.exception("Failed to create Stripe subscription for clinic %s", clinic.id)
        return BillingSetupResult(subscription, stripe_created=False, error=str(e))


async def handle_stripe_event(db: AsyncSession, event: dict) -> None:
    """Applies a verified Stripe webhook event to the local Subscription/Clinic rows."""
    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    if event_type.startswith("customer.subscription."):
        stripe_customer_id = data.get("customer")
        status_map = {
            "trialing": "trialing",
            "active": "active",
            "past_due": "past_due",
            "unpaid": "past_due",
            "canceled": "canceled",
            "incomplete_expired": "canceled",
        }
        new_status = status_map.get(data.get("status"), None)
        if not stripe_customer_id or not new_status:
            return

        result = await db.execute(
            select(Subscription).where(Subscription.stripe_customer_id == stripe_customer_id)
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            logger.warning(f"No local subscription for Stripe customer {stripe_customer_id}")
            return

        subscription.status = new_status
        subscription.stripe_subscription_id = data.get("id")

        clinic_result = await db.execute(select(Clinic).where(Clinic.id == subscription.clinic_id))
        clinic = clinic_result.scalar_one_or_none()
        if clinic:
            clinic.is_active = new_status in ("trialing", "active")
            clinic.stripe_subscription_id = data.get("id")

        logger.info(f"Subscription {subscription.id} for clinic {subscription.clinic_id} -> {new_status}")

    elif event_type == "invoice.payment_failed":
        stripe_customer_id = data.get("customer")
        result = await db.execute(
            select(Subscription).where(Subscription.stripe_customer_id == stripe_customer_id)
        )
        subscription = result.scalar_one_or_none()
        if subscription:
            subscription.status = "past_due"
            logger.warning(f"Payment failed for clinic {subscription.clinic_id}, marked past_due")
