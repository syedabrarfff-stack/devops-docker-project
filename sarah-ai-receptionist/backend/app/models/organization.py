from sqlalchemy import String, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class Organization(Base, UUIDMixin, TimestampMixin):
    """Dental chain or group (e.g. Manipal Dental Group). Parent of multiple clinics."""
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="starter")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    clinics: Mapped[list["Clinic"]] = relationship("Clinic", back_populates="organization")
    users: Mapped[list["User"]] = relationship("User", back_populates="organization")
