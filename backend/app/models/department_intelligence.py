"""
Department Intelligence Models — 6-Layer Autonomous Intelligence System
"""
import enum
from sqlalchemy import Column, String, Text, JSON, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import JarvisBase
import uuid
from datetime import datetime


class DepartmentCode(str, enum.Enum):
    ENGINEERING       = "engineering"
    AI_ML             = "ai_ml"
    CLOUD_INFRA       = "cloud_infra"
    DEVOPS            = "devops"
    SECURITY          = "security"
    ARCHITECTURE      = "architecture"
    REVENUE_GROWTH    = "revenue_growth"
    MARKETING         = "marketing"
    CREATIVE          = "creative"
    CLIENT_SERVICES   = "client_services"
    CLIENT_DELIVERY   = "client_delivery"
    CUSTOMER_SUPPORT  = "customer_support"
    INTELLIGENCE      = "intelligence"
    PEOPLE_OPS        = "people_ops"
    PMO               = "pmo"
    FINANCE           = "finance"
    TECH_EVOLUTION    = "tech_evolution"
    STRATEGY          = "strategy"


class MilestoneStatus(str, enum.Enum):
    ACHIEVED      = "achieved"
    IN_REVIEW     = "in_review"
    COUNCIL_QUEUE = "council_queue"
    IMPROVING     = "improving"
    IMPLEMENTED   = "implemented"
    CLOSED        = "closed"


class CallStatus(str, enum.Enum):
    SCHEDULED     = "scheduled"
    BRIEFING      = "briefing"
    COUNCIL_REVIEW= "council_review"
    READY         = "ready"
    IN_PROGRESS   = "in_progress"
    COMPLETED     = "completed"
    DEBRIEFING    = "debriefing"


class TechStatus(str, enum.Enum):
    DISCOVERED    = "discovered"
    EVALUATING    = "evaluating"
    COUNCIL_QUEUE = "council_queue"
    APPROVED      = "approved"
    IMPLEMENTING  = "implementing"
    DEPLOYED      = "deployed"
    REJECTED      = "rejected"


class DepartmentIntelligenceOfficer(JarvisBase):
    """One DIO per department — monitors all operations, generates milestone PDFs, interfaces with Council."""
    __tablename__ = "department_intelligence_officers"

    department_code   = Column(String(50), nullable=False, unique=True)
    department_name   = Column(String(100), nullable=False)
    division          = Column(String(100), nullable=False)
    agent_name        = Column(String(100), nullable=False)
    agent_persona     = Column(String(100), nullable=False)
    agent_email       = Column(String(150), nullable=False)

    # Responsibilities
    monitored_systems = Column(JSON, default=list)   # list of system names
    kpi_targets       = Column(JSON, default=dict)   # kpi_name -> target value
    escalation_rules  = Column(JSON, default=dict)   # condition -> action

    # Performance
    milestones_submitted  = Column(Integer, default=0)
    improvements_received = Column(Integer, default=0)
    improvements_implemented = Column(Integer, default=0)
    performance_score     = Column(Float, default=1.0)

    # State
    last_report_at    = Column(DateTime, nullable=True)
    next_report_at    = Column(DateTime, nullable=True)
    is_active         = Column(Boolean, default=True)

    # Relationships
    milestones        = relationship("DepartmentMilestone", back_populates="dio", lazy="dynamic")
    call_briefs       = relationship("ClientCallIntelligence", back_populates="dio", lazy="dynamic")


class DepartmentMilestone(JarvisBase):
    """A milestone achieved by a department — goes through Council review loop."""
    __tablename__ = "department_milestones"

    dio_id            = Column(UUID(as_uuid=True), ForeignKey("department_intelligence_officers.id"), nullable=False)
    department_code   = Column(String(50), nullable=False)
    title             = Column(String(300), nullable=False)
    description       = Column(Text, nullable=False)
    milestone_type    = Column(String(50), nullable=False)  # achievement/blocker/insight/metric

    # Evidence
    metrics           = Column(JSON, default=dict)    # actual numbers
    evidence_data     = Column(JSON, default=dict)    # raw data
    impact_score      = Column(Float, default=0.0)    # 0-100

    # PDF tracking
    milestone_pdf_url = Column(String(500), nullable=True)   # PDF Captain submitted
    improvement_pdf_url = Column(String(500), nullable=True) # Council improvement PDF

    # Council session
    council_session_id = Column(UUID(as_uuid=True), nullable=True)
    council_score      = Column(Float, nullable=True)
    council_verdict    = Column(Text, nullable=True)
    council_recommendations = Column(JSON, default=list)

    # Implementation
    status            = Column(String(30), default=MilestoneStatus.ACHIEVED)
    implementation_notes = Column(Text, nullable=True)
    implemented_at    = Column(DateTime, nullable=True)

    dio               = relationship("DepartmentIntelligenceOfficer", back_populates="milestones")


class TechnologyDiscovery(JarvisBase):
    """24/7 Technology Evolution Engine — discovers, evaluates, presents to Council."""
    __tablename__ = "technology_discoveries"

    # Discovery
    technology_name   = Column(String(200), nullable=False)
    source            = Column(String(100), nullable=False)  # github/openai/anthropic/arxiv/etc
    source_url        = Column(String(500), nullable=True)
    discovered_at     = Column(DateTime, default=datetime.utcnow)

    # Classification
    category          = Column(String(100), nullable=False)  # llm/infra/tools/agents/etc
    provider          = Column(String(100), nullable=True)   # OpenAI/Anthropic/DeepSeek/etc
    relevance_score   = Column(Float, default=0.0)           # 0-100 relevance to JARVIS
    priority          = Column(String(20), default="medium") # critical/high/medium/low

    # Analysis
    summary           = Column(Text, nullable=True)
    capabilities      = Column(JSON, default=list)
    integration_feasibility = Column(Float, default=0.0)     # 0-100
    estimated_impact  = Column(Text, nullable=True)
    adoption_guide    = Column(Text, nullable=True)          # full guide

    # Council
    council_session_id = Column(UUID(as_uuid=True), nullable=True)
    council_strategy  = Column(Text, nullable=True)
    implementation_roadmap = Column(JSON, default=dict)
    council_pdf_url   = Column(String(500), nullable=True)

    status            = Column(String(30), default=TechStatus.DISCOVERED)
    deployed_at       = Column(DateTime, nullable=True)


class ClientCallIntelligence(JarvisBase):
    """Client Call Intelligence — pre-call briefing, Council review, ElevenLabs voice agent."""
    __tablename__ = "client_call_intelligence"

    dio_id            = Column(UUID(as_uuid=True), ForeignKey("department_intelligence_officers.id"), nullable=False)
    department_code   = Column(String(50), nullable=False)

    # Call details
    client_name       = Column(String(200), nullable=False)
    client_company    = Column(String(200), nullable=False)
    client_email      = Column(String(200), nullable=True)
    scheduled_at      = Column(DateTime, nullable=False)
    call_topic        = Column(String(300), nullable=False)
    call_objective    = Column(Text, nullable=True)

    # Pre-call briefing (generated 1 hour before)
    briefing_pdf_url  = Column(String(500), nullable=True)
    briefing_content  = Column(Text, nullable=True)         # full briefing text
    what_to_say       = Column(JSON, default=list)          # key talking points
    what_not_to_say   = Column(JSON, default=list)          # forbidden topics/prices
    objection_handlers = Column(JSON, default=dict)         # objection -> response
    context_summary   = Column(Text, nullable=True)         # full client context

    # Council review
    council_session_id = Column(UUID(as_uuid=True), nullable=True)
    council_refinements = Column(JSON, default=list)        # council improvements
    council_approved  = Column(Boolean, default=False)
    refined_briefing_pdf_url = Column(String(500), nullable=True)

    # Voice agent
    voice_agent_id    = Column(String(100), nullable=True)  # ElevenLabs agent ID
    voice_personality = Column(String(200), nullable=True)
    elevenlabs_voice_id = Column(String(100), nullable=True)
    call_script       = Column(Text, nullable=True)         # final approved script
    humanization_notes = Column(Text, nullable=True)        # how to sound human

    # Post-call
    call_recording_url = Column(String(500), nullable=True)
    call_transcript   = Column(Text, nullable=True)
    outcome           = Column(String(50), nullable=True)   # demo_booked/proposal_requested/not_interested
    post_call_debrief = Column(Text, nullable=True)
    council_debrief_pdf_url = Column(String(500), nullable=True)
    improvements_for_next = Column(JSON, default=list)

    status            = Column(String(30), default=CallStatus.SCHEDULED)
    dio               = relationship("DepartmentIntelligenceOfficer", back_populates="call_briefs")


class StrategyReport(JarvisBase):
    """Daily strategy report from Strategy Oversight Team — all departments → Council → cascade."""
    __tablename__ = "strategy_reports"

    report_date       = Column(DateTime, nullable=False)
    report_type       = Column(String(50), default="daily")  # daily/weekly/monthly

    # Operations summary across all departments
    operations_summary = Column(JSON, default=dict)          # dept -> summary
    kpi_snapshot      = Column(JSON, default=dict)           # all KPIs
    alerts            = Column(JSON, default=list)           # critical issues
    achievements      = Column(JSON, default=list)           # wins
    blockers          = Column(JSON, default=list)           # what's stuck

    # Revenue intelligence
    mrr               = Column(Float, default=0.0)
    pipeline_value    = Column(Float, default=0.0)
    leads_this_week   = Column(Integer, default=0)
    demos_scheduled   = Column(Integer, default=0)
    proposals_sent    = Column(Integer, default=0)
    outreach_sent     = Column(Integer, default=0)
    reply_rate        = Column(Float, default=0.0)

    # Council
    council_session_id = Column(UUID(as_uuid=True), nullable=True)
    scaling_strategy  = Column(Text, nullable=True)
    council_directives = Column(JSON, default=list)         # instructions to each dept
    strategy_pdf_url  = Column(String(500), nullable=True)

    # Cascade
    cascaded_to_departments = Column(JSON, default=list)
    cascade_completed_at = Column(DateTime, nullable=True)
