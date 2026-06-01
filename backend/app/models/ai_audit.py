from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from datetime import datetime

from app.models.base import JarvisBase


class AIRequestLog(JarvisBase):
    __tablename__ = "ai_request_logs"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False, index=True)
    model = Column(String(100), nullable=False)
    task_type = Column(String(50), nullable=False, index=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    cost_estimate_usd = Column(Float, default=0.0)
    success = Column(Boolean, default=True, index=True)
    error_message = Column(Text, nullable=True)
    session_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
