from sqlalchemy import Column, String, Integer, Float, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(200), nullable=False)
    email       = Column(String(200), unique=True, index=True)
    phone       = Column(String(50))
    linkedin    = Column(String(300))
    title       = Column(String(150))      # Job title
    company_id  = Column(Integer, ForeignKey("companies.id"), nullable=True)
    country     = Column(String(100))
    timezone    = Column(String(60))
    status      = Column(String(30), default="lead", index=True)   # lead/prospect/qualified/client/churned
    score       = Column(Integer, default=0)                         # 0-100 AI score
    tags        = Column(JSON, default=list)
    notes       = Column(Text)
    last_contacted = Column(DateTime(timezone=True), nullable=True)
    next_action    = Column(String(300))
    source      = Column(String(100))       # apollo/manual/linkedin/referral
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    company  = relationship("Company", back_populates="contacts")
    deals    = relationship("Deal", back_populates="contact")
    emails   = relationship("OutreachEmail", back_populates="contact")


class Company(Base):
    __tablename__ = "companies"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    name          = Column(String(200), nullable=False)
    domain        = Column(String(200), unique=True, index=True)
    industry      = Column(String(100))
    country       = Column(String(100))
    size          = Column(String(50))    # 1-10 / 11-50 / 51-200 / 201-1000 / 1000+
    revenue_range = Column(String(50))    # <1M / 1-10M / 10-50M / 50M+
    tech_stack    = Column(JSON, default=list)
    pain_points   = Column(JSON, default=list)
    status        = Column(String(30), default="prospect")
    score         = Column(Integer, default=0)
    notes         = Column(Text)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    contacts = relationship("Contact", back_populates="company")
    deals    = relationship("Deal", back_populates="company")


class Deal(Base):
    __tablename__ = "deals"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    title        = Column(String(300), nullable=False)
    contact_id   = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    company_id   = Column(Integer, ForeignKey("companies.id"), nullable=True)
    value        = Column(Float, default=0.0)
    currency     = Column(String(10), default="USD")
    stage        = Column(String(50), default="discovery", index=True)
    # discovery / proposal / negotiation / closed_won / closed_lost
    probability  = Column(Integer, default=10)   # 0-100%
    service_type = Column(String(100))           # AI automation / DevOps / Cloud migration etc.
    expected_close = Column(DateTime(timezone=True), nullable=True)
    notes        = Column(Text)
    ai_analysis  = Column(Text)   # Gemini analysis of the deal
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())

    contact = relationship("Contact", back_populates="deals")
    company = relationship("Company", back_populates="deals")
