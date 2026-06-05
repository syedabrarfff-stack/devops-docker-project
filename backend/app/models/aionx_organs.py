"""SQLAlchemy models for all AIONX Sovereign Organs."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, Index, Integer, SmallInteger, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JarvisBase


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


# ─── DECISION MEMORY ENGINE ──────────────────────────────────────────────────

class DecisionObject(JarvisBase):
    __tablename__ = "decision_objects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    mission_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tier: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2)
    decision_category: Mapped[str] = mapped_column(Text, nullable=False, default="GENERAL")
    trigger_event: Mapped[str] = mapped_column(Text, nullable=False)
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    executor_role: Mapped[str] = mapped_column(Text, nullable=False, default="JARVIS_AUTONOMOUS")
    final_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_flags: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    assumptions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    outcome_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pattern_approved_for_reuse: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class DecisionOption(JarvisBase):
    __tablename__ = "decision_options"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    was_chosen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    proponent_brains: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    opponent_brains: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    predicted_outcome_30d: Mapped[str | None] = mapped_column(Text, nullable=True)
    predicted_outcome_90d: Mapped[str | None] = mapped_column(Text, nullable=True)
    predicted_revenue_impact: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    predicted_reputation_impact: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    opportunity_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class DecisionOutcome(JarvisBase):
    __tablename__ = "decision_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    deployed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    actual_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    day_30_review: Mapped[str | None] = mapped_column(Text, nullable=True)
    day_30_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    day_90_review: Mapped[str | None] = mapped_column(Text, nullable=True)
    day_90_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence_validation: Mapped[str | None] = mapped_column(Text, nullable=True)
    lessons_learned: Mapped[str | None] = mapped_column(Text, nullable=True)
    pattern_approved_for_reuse: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class DecisionPattern(JarvisBase):
    __tablename__ = "decision_patterns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    pattern_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    pattern_category: Mapped[str] = mapped_column(Text, nullable=False)
    when_to_apply: Mapped[str] = mapped_column(Text, nullable=False)
    decision_template: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    historical_success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence_for_automation: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class DecisionRetrospective(JarvisBase):
    __tablename__ = "decision_retrospectives"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    week_of: Mapped[date] = mapped_column(Date, nullable=False)
    total_decisions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    incorrect_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pattern_insights: Mapped[str | None] = mapped_column(Text, nullable=True)
    council_weight_adjustments: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    recommended_playbooks: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    wisdom_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ─── COUNTERFACTUAL ENGINE ───────────────────────────────────────────────────

class CounterfactualSimulation(JarvisBase):
    __tablename__ = "counterfactual_simulations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    option_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    simulation_narrative: Mapped[str] = mapped_column(Text, nullable=False)
    predicted_revenue_impact: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    predicted_reputation_impact: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    opportunity_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    simulation_twin_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    simulated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class CounterfactualActualization(JarvisBase):
    __tablename__ = "counterfactual_actualizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    day_30_actual: Mapped[str | None] = mapped_column(Text, nullable=True)
    day_30_accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    day_90_actual: Mapped[str | None] = mapped_column(Text, nullable=True)
    day_90_accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_calibration: Mapped[float | None] = mapped_column(Float, nullable=True)
    learnings: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ─── DECISION DEBT ENGINE ────────────────────────────────────────────────────

class DecisionDebtAssessment(JarvisBase):
    __tablename__ = "decision_debt_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    debt_category: Mapped[str] = mapped_column(Text, nullable=False, default="TECHNICAL")
    debt_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_payoff_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    repayment_cost_estimate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    repayment_priority: Mapped[str] = mapped_column(Text, nullable=False, default="MEDIUM")
    is_paid_off: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    paid_off_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class InstitutionalDebtIndex(JarvisBase):
    __tablename__ = "institutional_debt_index"
    __table_args__ = (UniqueConstraint("week_of"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    week_of: Mapped[date] = mapped_column(Date, nullable=False)
    total_debt_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    technical_debt: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    operational_debt: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    complexity_debt: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    migration_debt: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    dependency_debt: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    critical_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_repayment_weeks: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    trend: Mapped[str] = mapped_column(Text, nullable=False, default="STABLE")
    refactoring_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ─── CLIENT DIGITAL TWINS ────────────────────────────────────────────────────

class ClientDigitalTwin(JarvisBase):
    __tablename__ = "client_digital_twins"
    __table_args__ = (UniqueConstraint("client_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    communication_preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    decision_speed: Mapped[str] = mapped_column(Text, nullable=False, default="methodical")
    risk_tolerance: Mapped[str] = mapped_column(Text, nullable=False, default="moderate")
    budget_authority: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    internal_politics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    buying_psychology: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_maturity: Mapped[str] = mapped_column(Text, nullable=False, default="traditional")
    support_expectation: Mapped[str] = mapped_column(Text, nullable=False, default="collaborative")
    preferred_hia_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    historical_objections: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    successful_strategies: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    trust_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    relationship_age_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stakeholder_map: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    churn_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    upsell_opportunity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    renewal_probability: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    last_interaction_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class ClientTwinInteraction(JarvisBase):
    __tablename__ = "client_twin_interactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    twin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    interaction_type: Mapped[str] = mapped_column(Text, nullable=False, default="EMAIL")
    hia_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment: Mapped[str] = mapped_column(Text, nullable=False, default="neutral")
    trust_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_updates: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    raw_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class ClientTwinPrediction(JarvisBase):
    __tablename__ = "client_twin_predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    twin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    model_type: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    prediction_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    prediction_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    historical_accuracy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ─── INSTITUTIONAL WISDOM INDEX ──────────────────────────────────────────────

class ClientPipelineState(JarvisBase):
    __tablename__ = "client_pipeline_states"
    __table_args__ = (
        UniqueConstraint("client_id"),
        Index("idx_client_pipeline_states_tenant_stage", "tenant_id", "current_stage"),
        Index("idx_client_pipeline_states_created", "created_at"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    current_stage: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    stage_name: Mapped[str] = mapped_column(Text, nullable=False, default="Lead discovery")
    phase: Mapped[str] = mapped_column(Text, nullable=False, default="Lead discovery & qualification")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="ACTIVE")
    engagement_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    previous_engagement_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    stage_entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    mission_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    council_gate_status: Mapped[str] = mapped_column(Text, nullable=False, default="NOT_REQUIRED")
    validation_status: Mapped[str] = mapped_column(Text, nullable=False, default="PENDING")
    qa_status: Mapped[str] = mapped_column(Text, nullable=False, default="PENDING")
    repair_loop_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ClientPipelineMilestone(JarvisBase):
    __tablename__ = "client_pipeline_milestones"
    __table_args__ = (
        Index("idx_client_pipeline_milestones_tenant_stage", "tenant_id", "stage_number"),
        Index("idx_client_pipeline_milestones_client_status", "client_id", "status"),
        Index("idx_client_pipeline_milestones_created", "created_at"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    pipeline_state_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    stage_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    milestone_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    department: Mapped[str] = mapped_column(Text, nullable=False, default="JARVIS")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="PENDING")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class WisdomIndexSnapshot(JarvisBase):
    __tablename__ = "wisdom_index_snapshots"
    __table_args__ = (UniqueConstraint("week_of"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    week_of: Mapped[date] = mapped_column(Date, nullable=False)
    wisdom_score: Mapped[float] = mapped_column(Float, nullable=False, default=500.0)
    previous_score: Mapped[float] = mapped_column(Float, nullable=False, default=500.0)
    delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    decision_accuracy_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    calibration_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    counterfactual_precision_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    provider_authority_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pattern_reuse_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    client_retention_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    debt_burden_penalty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    knowledge_freshness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    convergence_efficiency_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    self_mod_success_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendations: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ─── PROVIDER SOVEREIGN COUNCIL ──────────────────────────────────────────────

class ProviderCalibrationRecord(JarvisBase):
    __tablename__ = "provider_calibration_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(Text, nullable=False)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_at_claim: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    was_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    brier_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    domain_authority_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class ProviderCouncilSession(JarvisBase):
    __tablename__ = "provider_council_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    trigger_type: Mapped[str] = mapped_column(Text, nullable=False, default="SCHEDULED")
    trigger_signal: Mapped[str | None] = mapped_column(Text, nullable=True)
    participants: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    agenda_items: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    debate_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    convergence_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendations: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    improvement_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    technology_adoption_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    competitive_threat_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    jarvis_decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_consumed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    session_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ShelvedDiscovery(JarvisBase):
    __tablename__ = "shelved_discoveries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    wake_condition: Mapped[str] = mapped_column(Text, nullable=False)
    wake_metric: Mapped[str | None] = mapped_column(Text, nullable=True)
    wake_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority: Mapped[str] = mapped_column(Text, nullable=False, default="MEDIUM")
    roi_estimate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_estimate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_activated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shelved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ─── GRAND CONVERGENCE COUNCIL ───────────────────────────────────────────────

class ConvergenceCouncilSession(JarvisBase):
    __tablename__ = "convergence_council_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    trigger_event: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_type: Mapped[str] = mapped_column(Text, nullable=False, default="OPPORTUNITY")
    session_phase: Mapped[str] = mapped_column(Text, nullable=False, default="SIGNAL")
    participants: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    context_loaded: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    simulation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    convergence_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    dissenting_opinions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    jarvis_decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    captain_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_consumed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    session_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConvergenceCouncilMessage(JarvisBase):
    __tablename__ = "convergence_council_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    speaker: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(Text, nullable=False, default="STATEMENT")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evidence_refs: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    prediction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_falsifiable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ─── MISSION AUTOPSY ENGINE ──────────────────────────────────────────────────

class MissionAutopsy(JarvisBase):
    __tablename__ = "mission_autopsies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    mission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    failure_type: Mapped[str] = mapped_column(Text, nullable=False, default="MISSION_FAILURE")
    failure_summary: Mapped[str] = mapped_column(Text, nullable=False)
    causal_chain: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    what_failed: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_it_failed: Mapped[str | None] = mapped_column(Text, nullable=True)
    who_detected: Mapped[str | None] = mapped_column(Text, nullable=True)
    who_missed: Mapped[str | None] = mapped_column(Text, nullable=True)
    which_assumption_broke: Mapped[str | None] = mapped_column(Text, nullable=True)
    which_warning_ignored: Mapped[str | None] = mapped_column(Text, nullable=True)
    alternative_path_that_would_succeed: Mapped[str | None] = mapped_column(Text, nullable=True)
    institutional_doctrine: Mapped[str | None] = mapped_column(Text, nullable=True)
    doctrine_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ─── SENTINEL LAYER ──────────────────────────────────────────────────────────

class SentinelObservation(JarvisBase):
    __tablename__ = "sentinel_observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False, default="TECHNOLOGY")
    signal_strength: Mapped[str] = mapped_column(Text, nullable=False, default="WEAK")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    escalated_to: Mapped[str | None] = mapped_column(Text, nullable=True)
    council_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    council_session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class SentinelThreat(JarvisBase):
    __tablename__ = "sentinel_threat_registry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    threat_type: Mapped[str] = mapped_column(Text, nullable=False, default="COMPETITIVE")
    threat_name: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False, default="LOW")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="ACTIVE")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ─── EXECUTIVE ACCOUNTABILITY ────────────────────────────────────────────────

class MissionOwnershipRecord(JarvisBase):
    __tablename__ = "mission_ownership_records"
    __table_args__ = (UniqueConstraint("mission_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    mission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    executive_owner: Mapped[str] = mapped_column(Text, nullable=False, default="JARVIS")
    primary_hia: Mapped[str | None] = mapped_column(Text, nullable=True)
    council_lead: Mapped[str | None] = mapped_column(Text, nullable=True)
    department_leads: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    profitability_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    client_satisfaction_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    delivery_on_time: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    repair_loops_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delay_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    root_causes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    mission_status: Mapped[str] = mapped_column(Text, nullable=False, default="ACTIVE")
    mission_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ─── SELF-MODIFICATION REGISTRY ──────────────────────────────────────────────

class SelfModificationRecord(JarvisBase):
    __tablename__ = "self_modification_registry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    mod_type: Mapped[str] = mapped_column(Text, nullable=False, default="PROMPT")
    blast_radius: Mapped[str] = mapped_column(Text, nullable=False, default="CONFIG")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_by: Mapped[str] = mapped_column(Text, nullable=False, default="PROVIDER_COUNCIL")
    simulation_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    council_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    shadow_deployed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ab_winner: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    canary_stage: Mapped[str] = mapped_column(Text, nullable=False, default="PROPOSED")
    rollback_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rollback_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    promoted_to_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_object_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
