from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import JarvisBase as Base


class AgentTask(Base):
    """Tasks created by Captain or agents for the AI task queue."""
    __tablename__ = "agent_tasks"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    title        = Column(String(300), nullable=False)
    description  = Column(Text)
    task_type    = Column(String(50), index=True)
    # research / write / analyze / outreach / crm_update / lead_score / summarize / custom
    assigned_to  = Column(String(100), default="jarvis")    # agent name
    created_by   = Column(String(100), default="captain")
    priority     = Column(Integer, default=5)               # 1=critical, 10=low
    status       = Column(String(30), default="queued", index=True)
    # queued / running / completed / failed / cancelled
    payload      = Column(JSON, default=dict)               # task input data
    result       = Column(Text, nullable=True)              # task output
    error        = Column(Text, nullable=True)
    model_used   = Column(String(100), nullable=True)
    tokens_used  = Column(Integer, default=0)
    parent_id    = Column(Integer, ForeignKey("agent_tasks.id"), nullable=True)
    started_at   = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    subtasks = relationship("AgentTask", backref="parent", remote_side=[id])
    messages = relationship("AgentMessage", back_populates="task")


class AgentMessage(Base):
    """Agent-to-agent communication channel."""
    __tablename__ = "agent_messages"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    from_agent   = Column(String(100), nullable=False, index=True)
    to_agent     = Column(String(100), nullable=False, index=True)
    message_type = Column(String(50), default="request")
    # request / response / update / delegate / broadcast
    content      = Column(Text, nullable=False)
    payload      = Column(JSON, default=dict)
    task_id      = Column(Integer, ForeignKey("agent_tasks.id"), nullable=True)
    status       = Column(String(30), default="sent")    # sent / read / acted
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    read_at      = Column(DateTime(timezone=True), nullable=True)

    task = relationship("AgentTask", back_populates="messages")
