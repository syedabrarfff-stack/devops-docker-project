from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class NotificationLog(Base):
    """Persistent log of all JARVIS notifications sent to Captain."""
    __tablename__ = "notification_logs"

    id          = Column(Integer, primary_key=True, index=True)
    channel     = Column(String(30), index=True)    # telegram | slack | websocket | email
    title       = Column(String(300))
    body        = Column(Text)
    level       = Column(String(20), default="info")  # info | warning | critical | success
    category    = Column(String(50), nullable=True)   # lead | outreach | approval | system | task
    reference   = Column(String(100), nullable=True)  # e.g. "lead:42" or "approval:7"
    delivered   = Column(Boolean, default=False)
    read        = Column(Boolean, default=False)
    metadata_   = Column("metadata", JSON, default=dict)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
