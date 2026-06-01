from sqlalchemy import Column, Integer, String, Text, Boolean, JSON, DateTime
from datetime import datetime

from app.models.base import JarvisBase


class ServiceDivision(JarvisBase):
    __tablename__ = "service_divisions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(60), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    division_group = Column(String(100), nullable=False)   # Sales & Marketing, Cloud & DevOps, etc.
    description = Column(Text, nullable=False)
    deliverables = Column(JSON, default=list)              # list[str]
    technologies = Column(JSON, default=list)              # list[str]
    target_industries = Column(JSON, default=list)         # SaaS, clinics, ecomm, logistics, etc.
    pricing_model = Column(String(50), default="project")  # project | retainer | hourly | subscription
    price_range_usd = Column(JSON, default=dict)           # {"min": 500, "max": 5000}
    duration_estimate = Column(String(100), default="")    # "2–4 weeks"
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
