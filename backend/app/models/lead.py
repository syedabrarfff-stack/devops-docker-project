from sqlalchemy import Column, String, Text, DateTime, Integer, JSON, Boolean, Float
from sqlalchemy.sql import func
from app.core.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id               = Column(Integer, primary_key=True, index=True)
    company          = Column(String(200), index=True)      # renamed from company_name
    company_name     = Column(String(200), nullable=True)   # legacy alias
    contact_name     = Column(String(200), nullable=True)
    email            = Column(String(200), nullable=True, index=True)
    contact_email    = Column(String(200), nullable=True)   # legacy alias
    website          = Column(String(500), nullable=True)
    company_website  = Column(String(500), nullable=True)   # legacy alias
    industry         = Column(String(100), nullable=True, index=True)
    country          = Column(String(100), nullable=True, index=True)
    pain_points      = Column(JSON, default=list)
    opportunity_type = Column(String(100), nullable=True)
    status           = Column(String(50), default="new", index=True)
    # new / qualified / contacted / replied / interested / proposal / closed / disqualified
    score            = Column(Integer, default=0, index=True)   # 0-100 Gemini score
    tier             = Column(String(5), default="C")            # A/B/C/D
    ai_analysis      = Column(Text, nullable=True)               # Gemini reasoning
    outreach_sent    = Column(Boolean, default=False)
    last_contacted   = Column(DateTime(timezone=True), nullable=True)
    source           = Column(String(100), default="manual")     # manual/apollo/linkedin
    notes            = Column(Text, nullable=True)
    metadata_        = Column("metadata", JSON, default=dict)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id            = Column(Integer, primary_key=True, index=True)
    workflow_id   = Column(String(100), index=True)
    workflow_name = Column(String(200))
    status        = Column(String(30), default="running")
    steps_total   = Column(Integer, default=0)
    steps_done    = Column(Integer, default=0)
    result        = Column(Text, nullable=True)
    error         = Column(Text, nullable=True)
    metadata_     = Column("metadata", JSON, default=dict)
    started_at    = Column(DateTime(timezone=True), server_default=func.now())
    completed_at  = Column(DateTime(timezone=True), nullable=True)
