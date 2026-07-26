from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin, TimestampMixin


class Subscription(Base, UUIDMixin, TimestampMixin):
    """Stripe billing subscription per clinic."""
    __tablename__ = "subscriptions"

    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), nullable=False, index=True, unique=True)

    stripe_subscription_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(100), nullable=True)

    plan: Mapped[str] = mapped_column(String(50), default="starter")  # starter/growth/enterprise
    monthly_price_usd: Mapped[float] = mapped_column(Float, default=299.0)
    status: Mapped[str] = mapped_column(String(50), default="trialing")  # trialing/active/past_due/canceled

    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
