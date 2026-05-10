from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Boolean, Numeric
from sqlalchemy.sql import func
from app.core.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    invoice_number = Column(String(50), unique=True, nullable=False)
    client_name = Column(String(200), nullable=False)
    client_email = Column(String(200))
    client_company = Column(String(200))
    items = Column(JSON)                        # [{description, qty, unit_price, amount}]
    subtotal = Column(Numeric(12, 2), default=0)
    tax_rate = Column(Numeric(5, 2), default=0)
    tax_amount = Column(Numeric(12, 2), default=0)
    total = Column(Numeric(12, 2), default=0)
    currency = Column(String(10), default="USD")
    status = Column(String(20), default="draft")  # draft|sent|paid|overdue|cancelled
    notes = Column(Text)
    payment_link = Column(Text)
    due_date = Column(DateTime(timezone=True))
    sent_at = Column(DateTime(timezone=True))
    paid_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ContractTemplate(Base):
    __tablename__ = "contract_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    category = Column(String(50))               # consulting|saas|retainer|project|nda
    content = Column(Text)                      # template text with {{variable}} placeholders
    variables = Column(JSON)                    # list of placeholder names
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Proposal(Base):
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True)
    title = Column(String(400), nullable=False)
    client_name = Column(String(200))
    client_email = Column(String(200))
    client_company = Column(String(200))
    service_type = Column(String(100))
    proposal_style = Column(String(50), default="standard")  # standard|case_study|short_urgent|social_proof
    scope = Column(Text)
    timeline = Column(String(200))
    pricing = Column(JSON)                      # {setup_fee, monthly_retainer, one_time, notes}
    content = Column(Text)                      # full AI-generated proposal text
    ai_generated = Column(Boolean, default=True)
    status = Column(String(20), default="draft")  # draft|sent|accepted|declined|negotiating
    sent_at = Column(DateTime(timezone=True))
    viewed_at = Column(DateTime(timezone=True))
    responded_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AgentPermission(Base):
    __tablename__ = "agent_permissions"

    id = Column(Integer, primary_key=True)
    agent_name = Column(String(100), nullable=False)
    permission_type = Column(String(100), nullable=False)
    scope = Column(JSON)                        # {resources: [], actions: [], limits: {}}
    risk_level = Column(String(20), default="low")  # low|medium|high|critical
    reason = Column(Text)
    granted_by = Column(String(100), default="Captain Abrar")
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True))
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True))


class IncidentReport(Base):
    __tablename__ = "incident_reports"

    id = Column(Integer, primary_key=True)
    title = Column(String(400), nullable=False)
    severity = Column(String(20), default="medium")   # low|medium|high|critical
    category = Column(String(50))                     # infrastructure|security|api|automation|billing
    description = Column(Text)
    affected_systems = Column(JSON)                   # list of affected service names
    actions_taken = Column(JSON)                      # list of response actions
    status = Column(String(20), default="open")       # open|investigating|resolved|escalated
    auto_detected = Column(Boolean, default=False)
    notified_captain = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
