from sqlalchemy import Boolean, Column, Float, Integer, String, Text, JSON, DateTime
from sqlalchemy.sql import func
from app.models.base import JarvisBase as Base


class TechRadarEntry(Base):
    __tablename__ = "tech_radar_entries"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)   # AI/ML, Cloud/AWS, DevOps, Security, Automation, Frameworks
    status = Column(String(20), nullable=False, default="assess")  # adopt | trial | assess | hold
    summary = Column(Text)
    recommendation = Column(Text)
    why_it_matters = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class OptimizationRecommendation(Base):
    __tablename__ = "optimization_recommendations"

    id = Column(Integer, primary_key=True)
    area = Column(String(100), nullable=False)       # architecture, ai_routing, security, performance, etc.
    title = Column(String(400), nullable=False)
    current_state = Column(Text)
    recommended_state = Column(Text)
    estimated_impact = Column(Text)
    priority = Column(String(20), nullable=False, default="medium")  # critical | high | medium | low
    status = Column(String(20), nullable=False, default="pending")   # pending | approved | implemented | dismissed
    action_steps = Column(JSON)                      # list[str]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ResearchReport(Base):
    __tablename__ = "research_reports"

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    category = Column(String(100))                   # market | technology | competitor | niche | infrastructure
    summary = Column(Text)
    findings = Column(JSON)                          # list[str]
    opportunities = Column(JSON)                     # list[str]
    risks = Column(JSON)                             # list[str]
    action_items = Column(JSON)                      # list[str]
    confidence_level = Column(String(20))            # high | medium | low
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MarketIntelligence(Base):
    __tablename__ = "market_intelligence"

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    topics = Column(JSON, default=list)
    report_content = Column(Text, nullable=False)
    summary = Column(Text)
    opportunities = Column(JSON, default=list)
    risks = Column(JSON, default=list)
    confidence_score = Column(Float, default=0.0)
    evidence_refs = Column(JSON, default=list)
    generated_by = Column(String(100), default="gemini-pro")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CompetitorProfile(Base):
    __tablename__ = "competitor_profiles"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    website_url = Column(String(500), default="")
    linkedin_url = Column(String(500), default="")
    pricing_url = Column(String(500), default="")
    last_website_hash = Column(String(64), default="")
    last_linkedin_hash = Column(String(64), default="")
    last_pricing_hash = Column(String(64), default="")
    last_change_summary = Column(Text, default="")
    last_checked_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, index=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BriefingHistory(Base):
    __tablename__ = "briefing_history"

    id = Column(Integer, primary_key=True)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    channels = Column(JSON, default=list)
    status = Column(String(30), nullable=False, default="generated")
    metrics = Column(JSON, default=dict)
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
