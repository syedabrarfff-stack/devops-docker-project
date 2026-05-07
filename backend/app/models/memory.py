from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Float
from sqlalchemy.sql import func
from app.core.database import Base


class Memory(Base):
    """Long-term memory store for JARVIS across sessions."""
    __tablename__ = "memories"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    session_id   = Column(String(100), index=True, nullable=True)  # null = global memory
    memory_type  = Column(String(30), default="episodic", index=True)
    # episodic  = specific event/interaction
    # semantic  = extracted fact / knowledge
    # working   = current session context
    # instruction = Captain's standing orders
    key          = Column(String(300), index=True)       # searchable label
    value        = Column(Text, nullable=False)           # the memory content
    importance   = Column(Float, default=0.5)             # 0.0 - 1.0 (Gemini-scored)
    access_count = Column(Integer, default=0)
    tags         = Column(JSON, default=list)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed = Column(DateTime(timezone=True), nullable=True)


class ConversationSummary(Base):
    """AI-generated summaries of long conversations to compress context."""
    __tablename__ = "conversation_summaries"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    session_id  = Column(String(100), index=True, nullable=False)
    summary     = Column(Text, nullable=False)
    topics      = Column(JSON, default=list)
    turn_count  = Column(Integer, default=0)
    token_count = Column(Integer, default=0)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
