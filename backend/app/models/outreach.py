from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class OutreachSequence(Base):
    """Multi-step email/outreach sequences targeting ICP segments."""
    __tablename__ = "outreach_sequences"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    name             = Column(String(200), nullable=False)
    target_industry  = Column(String(100))
    target_country   = Column(String(100))
    target_company_size = Column(String(50))
    service_offered  = Column(String(200))   # what Aliyar is pitching
    status           = Column(String(30), default="draft")   # draft/active/paused/completed
    total_steps      = Column(Integer, default=3)
    emails_sent      = Column(Integer, default=0)
    emails_opened    = Column(Integer, default=0)
    replies_received = Column(Integer, default=0)
    meetings_booked  = Column(Integer, default=0)
    steps            = Column(JSON, default=list)
    # [{step, delay_days, subject_template, body_template}]
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())

    emails = relationship("OutreachEmail", back_populates="sequence")


class OutreachEmail(Base):
    """Individual email records within outreach sequences."""
    __tablename__ = "outreach_emails"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    sequence_id  = Column(Integer, ForeignKey("outreach_sequences.id"), nullable=True)
    contact_id   = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    to_email     = Column(String(200), nullable=False)
    to_name      = Column(String(200))
    subject      = Column(String(500))
    body         = Column(Text)
    step_number  = Column(Integer, default=1)
    status       = Column(String(30), default="scheduled", index=True)
    # scheduled / sent / opened / replied / bounced / failed
    personalized = Column(Boolean, default=False)   # was body AI-personalized?
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    sent_at      = Column(DateTime(timezone=True), nullable=True)
    opened_at    = Column(DateTime(timezone=True), nullable=True)
    replied_at   = Column(DateTime(timezone=True), nullable=True)
    error        = Column(Text, nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    sequence = relationship("OutreachSequence", back_populates="emails")
    contact  = relationship("Contact", back_populates="emails")
