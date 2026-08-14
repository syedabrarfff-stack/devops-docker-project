from sqlalchemy import Column, Index, String, Text, DateTime, Integer, JSON
from sqlalchemy.sql import func
from app.models.base import JarvisBase as Base


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_tenant_session_id", "tenant_id", "session_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True)
    role = Column(String(20))          # "user" | "jarvis"
    content = Column(Text)
    model_used = Column(String(100), nullable=True)
    task_type = Column(String(50), nullable=True)
    tokens_used = Column(Integer, default=0)
    metadata_ = Column("metadata", JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
