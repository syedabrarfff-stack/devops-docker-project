from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Boolean
from sqlalchemy.sql import func
from app.models.base import JarvisBase as Base


class SOPDocument(Base):
    """Standard Operating Procedure — reusable workflow playbooks."""
    __tablename__ = "sop_documents"

    id = Column(Integer, primary_key=True)
    title = Column(String(400), nullable=False)
    category = Column(String(100))              # onboarding|outreach|deployment|security|sales|support
    summary = Column(Text)
    steps = Column(JSON)                        # [{step, description, agent_responsible, tools}]
    triggers = Column(JSON)                     # conditions that activate this SOP
    estimated_duration = Column(String(50))
    version = Column(String(20), default="1.0")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LearningRecord(Base):
    """Captures lessons from execution outcomes — feeds JARVIS continuous improvement."""
    __tablename__ = "learning_records"

    id = Column(Integer, primary_key=True)
    category = Column(String(100))              # proposal|outreach|infrastructure|sales|client
    event_type = Column(String(100))            # success|failure|near_miss|insight
    title = Column(String(400), nullable=False)
    what_happened = Column(Text)
    what_worked = Column(Text)
    what_failed = Column(Text)
    lesson = Column(Text)                       # actionable takeaway
    applied_to = Column(JSON)                   # list of systems/agents this was applied to
    impact_score = Column(Integer, default=0)   # 1-10 significance
    source = Column(String(100))                # agent name, human, or system that logged this
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class KnowledgeBase(Base):
    """Centralized operational knowledge — persistent memory for JARVIS."""
    __tablename__ = "knowledge_base"

    id = Column(Integer, primary_key=True)
    title = Column(String(400), nullable=False)
    category = Column(String(100))              # client|technology|market|process|pricing
    content = Column(Text)
    tags = Column(JSON)                         # list of searchable tags
    source = Column(String(200))
    is_verified = Column(Boolean, default=False)
    use_count = Column(Integer, default=0)      # how many times retrieved
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
