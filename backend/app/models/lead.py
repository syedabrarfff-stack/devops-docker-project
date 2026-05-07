from sqlalchemy import Column, String, Text, DateTime, Integer, JSON, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(200), index=True)
    contact_name = Column(String(200), nullable=True)
    contact_email = Column(String(200), nullable=True)
    company_website = Column(String(500), nullable=True)
    industry = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    pain_points = Column(Text, nullable=True)
    opportunity_type = Column(String(100), nullable=True)  # cloud | ai | devops | automation
    status = Column(String(50), default="identified")      # identified | contacted | replied | interested | proposal | closed
    outreach_sent = Column(Boolean, default=False)
    last_contacted = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(String(100), index=True)
    workflow_name = Column(String(200))
    status = Column(String(30), default="running")   # running | completed | failed | pending_approval
    steps_total = Column(Integer, default=0)
    steps_done = Column(Integer, default=0)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, default={})
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
