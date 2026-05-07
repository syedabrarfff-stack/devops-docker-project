from sqlalchemy import Column, String, Text, DateTime, Integer, JSON, Boolean, Float
from sqlalchemy.sql import func
from app.core.database import Base


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id           = Column(Integer, primary_key=True, index=True)
    job_id       = Column(String(100), unique=True, index=True)   # APScheduler job ID
    name         = Column(String(200))
    description  = Column(Text, nullable=True)
    trigger_type = Column(String(20))  # cron | interval | date
    trigger_args = Column(JSON, default=dict)  # e.g. {"hour": 8, "minute": 0}
    agent        = Column(String(100), default="jarvis")
    task_type    = Column(String(100))   # lead_scoring | outreach | briefing | custom
    payload      = Column(JSON, default=dict)
    enabled      = Column(Boolean, default=True)
    last_run_at  = Column(DateTime(timezone=True), nullable=True)
    next_run_at  = Column(DateTime(timezone=True), nullable=True)
    last_status  = Column(String(30), nullable=True)   # success | failed | skipped
    run_count    = Column(Integer, default=0)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())
