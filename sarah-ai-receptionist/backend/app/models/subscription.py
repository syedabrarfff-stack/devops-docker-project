from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Subscription(Base, UUIDMixin, TimestampMixin):
    """Stripe billing subscription per clinic."""
    __tablename__ = "subscriptions"

    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), nullable=False, index=True, unique=True)

    stripe_subscription_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(100), nullable=True)

    plan: Mapped[str] = mapped_column(String(50), default="starter")  # starter/growth/enterprise
    # Local tracking only -- the currency actually charged is whatever
    # `settings.stripe_price_id` is denominated in on the Stripe side, since
    # Stripe derives a Subscription's currency from its Price object, not
    # from anything passed at Subscription-creation time. Keep this in sync
    # by hand with whichever Price is configured.
    monthly_price: Mapped[float] = mapped_column(Float, default=1099.0)
    currency: Mapped[str] = mapped_column(String(3), default="SAR")  # ISO 4217
    status: Mapped[str] = mapped_column(String(50), default="trialing")  # trialing/active/past_due/canceled

    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
