from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Boolean, Float
from sqlalchemy.sql import func
from app.models.base import JarvisBase as Base


class GmailMessage(Base):
    """Every email in the Aliyar Solutions Gmail inbox — tracked by JARVIS."""
    __tablename__ = "gmail_messages"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    gmail_id        = Column(String(100), unique=True, index=True)      # Gmail message ID
    thread_id       = Column(String(100), index=True, nullable=True)    # Gmail thread ID
    from_email      = Column(String(300), index=True, nullable=False)
    from_name       = Column(String(300), nullable=True)
    to_email        = Column(String(300), nullable=True)
    subject         = Column(String(500), nullable=True)
    body_text       = Column(Text, nullable=True)
    body_html       = Column(Text, nullable=True)
    snippet         = Column(String(500), nullable=True)
    direction       = Column(String(10), default="inbound")             # inbound | outbound
    category        = Column(String(50), default="uncategorized", index=True)
    # categories: client_reply, new_inquiry, follow_up, spam, internal, notification, other
    sentiment       = Column(String(20), nullable=True)                 # positive, neutral, negative, urgent
    ai_summary      = Column(Text, nullable=True)                       # JARVIS one-line summary
    ai_action       = Column(String(200), nullable=True)                # JARVIS recommended action
    lead_id         = Column(Integer, nullable=True, index=True)        # linked lead if found
    contact_id      = Column(Integer, nullable=True, index=True)        # linked CRM contact
    is_read         = Column(Boolean, default=False)
    is_replied      = Column(Boolean, default=False)
    is_starred      = Column(Boolean, default=False)
    needs_action    = Column(Boolean, default=False, index=True)
    received_at     = Column(DateTime(timezone=True), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
