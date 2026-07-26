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
DEFAULT_MONTHLY_PRICE_USD = 299.0


async def create_stripe_customer_and_subscription(
    db: AsyncSession, clinic: Clinic, admin_email: str
) -> Subscription:
    """Creates a Stripe customer for a newly onboarded clinic and starts a local
    trial subscription record. If Stripe isn't configured (local/dev), the
    subscription is still tracked locally in `trialing` status so the rest of
    the app (billing UI, dunning) has something real to read."""
    now = datetime.now(timezone.utc)
    trial_ends_at = now + timedelta(days=TRIAL_DAYS)

    stripe_customer_id = None
    if settings.stripe_secret_key:
        try:
            stripe.api_key = settings.stripe_secret_key
            customer = stripe.Customer.create(
                email=admin_email,
                name=clinic.name,
                metadata={"clinic_id": clinic.id},
            )
            stripe_customer_id = customer.id
            clinic.stripe_customer_id = stripe_customer_id
        except Exception as e:
            logger.error(f"Failed to create Stripe customer for clinic {clinic.id}: {e}")
    else:
        logger.warning("STRIPE_SECRET_KEY not configured — subscription tracked locally only")

    subscription = Subscription(
        clinic_id=clinic.id,
        stripe_customer_id=stripe_customer_id,
        plan=DEFAULT_PLAN,
        monthly_price_usd=DEFAULT_MONTHLY_PRICE_USD,
        status="trialing",
        current_period_start=now,
        current_period_end=trial_ends_at,
        trial_ends_at=trial_ends_at,
    )
    db.add(subscription)
    await db.flush()
    return subscription


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
