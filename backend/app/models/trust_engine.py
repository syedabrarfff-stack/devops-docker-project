from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Boolean, Float, ForeignKey
from sqlalchemy import UUID as SUUID
from sqlalchemy.sql import func
from app.models.base import JarvisBase as Base


class ExecutiveOpportunityBrief(Base):
    __tablename__ = "executive_briefs"

    id = Column(Integer, primary_key=True)
    lead_id = Column(SUUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    company_name = Column(String(300), nullable=False)
    industry = Column(String(150), nullable=True)
    pain_points = Column(JSON, default=list)
    bottlenecks = Column(JSON, default=list)
    opportunities = Column(JSON, default=list)
    quick_wins = Column(JSON, default=list)
    risk_factors = Column(JSON, default=list)
    estimated_roi = Column(String(500), nullable=True)
    narrative = Column(Text, nullable=True)
    trust_score_at_creation = Column(Float, default=0.0)
    status = Column(String(30), default="generated", index=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    viewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LeadEngagementEvent(Base):
    __tablename__ = "lead_engagement_events"

    id = Column(Integer, primary_key=True)
    lead_id = Column(SUUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(80), nullable=False, index=True)
    weight = Column(Float, nullable=False, default=1.0)
    source = Column(String(100), nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ReferralRequest(Base):
    __tablename__ = "referral_requests"

    id = Column(Integer, primary_key=True)
    client_id = Column(SUUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    request_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=True)
    status = Column(String(30), default="draft", index=True)
    response = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
