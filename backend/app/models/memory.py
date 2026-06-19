from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Float, Boolean, ForeignKey, UniqueConstraint, Index
from sqlalchemy import UUID as SUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.models.base import JarvisBase

Base = JarvisBase


class OutcomeRecord(Base):
    """Tracks what happened after JARVIS actions — makes JARVIS learn from results."""
    __tablename__ = "outcome_records"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    action_type   = Column(String(50), index=True)   # proposal_sent, lead_contacted, recommendation_made, idea_enhanced
    action_ref    = Column(String(200), nullable=True)  # reference ID or description
    action_detail = Column(Text, nullable=True)       # what was done
    outcome       = Column(String(50), nullable=True, index=True)  # won, lost, replied, ignored, accepted, rejected, pending
    outcome_note  = Column(Text, nullable=True)       # Captain's note on the outcome
    learning      = Column(Text, nullable=True)       # AI-extracted lesson
    importance    = Column(Float, default=0.5)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at   = Column(DateTime(timezone=True), nullable=True)


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


class MemoryOperational(JarvisBase):
    __tablename__ = "memory_operational"
    __table_args__ = (
        Index("ix_memory_operational_tenant_created", "tenant_id", "created_at"),
    )

    category: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class MemoryStrategic(JarvisBase):
    __tablename__ = "memory_strategic"
    __table_args__ = (
        Index("ix_memory_strategic_tenant_created", "tenant_id", "created_at"),
    )

    category: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    embedding: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_operational_id: Mapped[uuid.UUID | None] = mapped_column(
        SUUID(as_uuid=True),
        ForeignKey("memory_operational.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class CivilizationMemory(JarvisBase):
    __tablename__ = "civilization_memory"

    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class MemoryGraphNode(JarvisBase):
    """Enterprise memory node used for semantic search and cross-agent recall."""

    __tablename__ = "memory_graph_nodes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source_table", "source_id", name="uq_memory_graph_source"),
        Index("ix_memory_graph_nodes_tenant_updated", "tenant_id", "updated_at"),
    )

    node_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_table: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    embedding: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class MemoryGraphEdge(JarvisBase):
    """Relationship between two enterprise memory nodes."""

    __tablename__ = "memory_graph_edges"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "source_node_id",
            "target_node_id",
            "relationship_type",
            name="uq_memory_graph_edge",
        ),
    )

    source_node_id: Mapped[uuid.UUID] = mapped_column(
        SUUID(as_uuid=True),
        ForeignKey("memory_graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        SUUID(as_uuid=True),
        ForeignKey("memory_graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
