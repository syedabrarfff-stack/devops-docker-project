from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean
from sqlalchemy.sql import func
from app.models.base import JarvisBase as Base


class OAuthToken(Base):
    """Encrypted OAuth2 tokens — Gmail, Google Calendar, etc."""
    __tablename__ = "oauth_tokens"

    id            = Column(Integer, primary_key=True, index=True)
    provider      = Column(String(50), index=True)   # gmail | google_calendar
    account       = Column(String(200), index=True)  # the email/account identifier
    access_token  = Column(Text)                     # encrypted
    refresh_token = Column(Text, nullable=True)      # encrypted
    token_expiry  = Column(DateTime(timezone=True), nullable=True)
    scopes        = Column(Text, nullable=True)      # space-separated OAuth scopes
    is_valid      = Column(Boolean, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())


class SecureCredential(Base):
    """General-purpose encrypted key-value credential store."""
    __tablename__ = "secure_credentials"

    id         = Column(Integer, primary_key=True, index=True)
    key        = Column(String(200), unique=True, index=True)
    value      = Column(Text)       # encrypted
    source     = Column(String(50), default="local")  # local | aws_ssm
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
