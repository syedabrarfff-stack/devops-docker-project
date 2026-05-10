from sqlalchemy import Column, String, Text, DateTime, Integer, JSON, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    action_type = Column(String(100))          # "email_send" | "deploy" | "outreach" etc.
    summary = Column(Text)
    risk_level = Column(String(20), default="medium")   # low | medium | high | critical
    estimated_cost = Column(String(50), nullable=True)
    benefits = Column(Text, nullable=True)
    risks = Column(Text, nullable=True)
    rollback_plan = Column(Text, nullable=True)
    payload = Column(JSON, default={})         # full action data
    status = Column(String(20), default="pending")  # pending | approved | rejected
    captain_note = Column(Text, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(200))
    actor = Column(String(100), default="JARVIS")
    details = Column(JSON, default={})
    approval_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
