from sqlalchemy import Column, Integer, String, Text, JSON, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


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
