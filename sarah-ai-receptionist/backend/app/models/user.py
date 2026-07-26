from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class User(Base, UUIDMixin, TimestampMixin):
    """Dashboard login. clinic_id scoped; org-level admins have clinic_id=None + organization_id set."""
    __tablename__ = "users"

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # role: "platform_admin" (Captain), "org_admin" (chain admin), "clinic_manager" (location manager)
    role: Mapped[str] = mapped_column(String(50), default="clinic_manager")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="users")
    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="users")
