from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Boolean, Float
from sqlalchemy import UUID as SUUID
from sqlalchemy.sql import func
from app.models.base import JarvisBase as Base


class TruthEvent(Base):
    __tablename__ = "truth_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(SUUID(as_uuid=True), nullable=True, index=True)
    prediction_type = Column(String(80), nullable=True, index=True)
    entity_type = Column(String(80), nullable=True)
    entity_id = Column(String(120), nullable=True)
    predicted_value = Column(Float, nullable=True)
    predicted_label = Column(String(200), nullable=True)
    predicted_by = Column(String(100), nullable=True)
    confidence_score = Column(Float, nullable=True)
    metadata_json = Column(JSON, default=dict)
    outcome_recorded = Column(Boolean, default=False, index=True)
    outcome_value = Column(Float, nullable=True)
    outcome_label = Column(String(200), nullable=True)
    outcome_recorded_at = Column(DateTime(timezone=True), nullable=True)
    accuracy_delta = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PredictionAccuracy(Base):
    __tablename__ = "prediction_accuracy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(SUUID(as_uuid=True), nullable=True, index=True)
    prediction_type = Column(String(80), nullable=True, index=True)
    period_date = Column(DateTime(timezone=True), nullable=True, index=True)
    total_predictions = Column(Integer, default=0)
    scored_predictions = Column(Integer, default=0)
    mean_absolute_error = Column(Float, nullable=True)
    accuracy_score = Column(Float, nullable=True)
    calibration_score = Column(Float, nullable=True)
    trend = Column(String(20), nullable=True)
    weight_adjustment = Column(Float, default=1.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RealityCheck(Base):
    __tablename__ = "reality_checks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(SUUID(as_uuid=True), nullable=True, index=True)
    check_type = Column(String(80), nullable=True, index=True)
    prediction_summary = Column(JSON, default=dict)
    reality_summary = Column(JSON, default=dict)
    accuracy_pct = Column(Float, nullable=True)
    gap_analysis = Column(Text, nullable=True)
    auto_corrective_actions = Column(JSON, default=list)
    captain_report_sent = Column(Boolean, default=False)
    report_content = Column(Text, nullable=True)
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ResilienceEvent(Base):
    __tablename__ = "resilience_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(SUUID(as_uuid=True), nullable=True, index=True)
    incident_type = Column(String(80), nullable=True, index=True)
    severity = Column(String(20), nullable=True, index=True)
    status = Column(String(30), default="detected", index=True)
    playbook_used = Column(String(120), nullable=True)
    escalation_path = Column(JSON, default=list)
    fallback_systems_activated = Column(JSON, default=list)
    recovery_steps_taken = Column(JSON, default=list)
    estimated_recovery_minutes = Column(Integer, nullable=True)
    actual_recovery_minutes = Column(Integer, nullable=True)
    captain_notified = Column(Boolean, default=False)
    impact_summary = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FinancialHealth(Base):
    __tablename__ = "financial_health"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(SUUID(as_uuid=True), nullable=True, index=True)
    snapshot_date = Column(DateTime(timezone=True), nullable=True, index=True)
    mrr = Column(Float, default=0.0)
    arr = Column(Float, default=0.0)
    gross_margin_pct = Column(Float, nullable=True)
    client_acquisition_cost = Column(Float, nullable=True)
    avg_lifetime_value = Column(Float, nullable=True)
    revenue_concentration_risk = Column(Float, nullable=True)
    cash_flow_30d = Column(Float, nullable=True)
    runway_months = Column(Float, nullable=True)
    financial_health_score = Column(Float, nullable=True)
    active_clients = Column(Integer, default=0)
    churned_clients_30d = Column(Integer, default=0)
    new_clients_30d = Column(Integer, default=0)
    service_line_breakdown = Column(JSON, default=dict)
    risk_alerts = Column(JSON, default=list)
    expansion_alerts = Column(JSON, default=list)
    cfo_briefing = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CashflowForecast(Base):
    __tablename__ = "cashflow_forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(SUUID(as_uuid=True), nullable=True, index=True)
    forecast_date = Column(DateTime(timezone=True), nullable=True, index=True)
    horizon_days = Column(Integer, nullable=True, index=True)
    projected_revenue = Column(Float, default=0.0)
    projected_expenses = Column(Float, default=0.0)
    projected_net = Column(Float, default=0.0)
    confidence_low = Column(Float, nullable=True)
    confidence_high = Column(Float, nullable=True)
    assumptions = Column(JSON, default=dict)
    risk_factors = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ImprovementRecommendation(Base):
    __tablename__ = "improvement_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(SUUID(as_uuid=True), nullable=True, index=True)
    recommendation_type = Column(String(80), nullable=True, index=True)
    source_type = Column(String(80), nullable=True)
    source_id = Column(String(120), nullable=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), default="medium")
    implementation_status = Column(String(30), default="pending", index=True)
    estimated_impact = Column(String(200), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    applied_by = Column(String(100), nullable=True)
    outcome_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DeliveryLesson(Base):
    __tablename__ = "delivery_lessons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(SUUID(as_uuid=True), nullable=True, index=True)
    project_type = Column(String(120), nullable=True, index=True)
    client_industry = Column(String(120), nullable=True)
    lesson_category = Column(String(80), nullable=True, index=True)
    lesson_title = Column(String(300), nullable=False)
    lesson_body = Column(Text, nullable=False)
    what_worked = Column(Text, nullable=True)
    what_failed = Column(Text, nullable=True)
    do_next_time = Column(Text, nullable=True)
    estimated_effort_days = Column(Float, nullable=True)
    actual_effort_days = Column(Float, nullable=True)
    effort_accuracy_pct = Column(Float, nullable=True)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DependencyScore(Base):
    __tablename__ = "dependency_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(SUUID(as_uuid=True), nullable=True, index=True)
    snapshot_date = Column(DateTime(timezone=True), nullable=True, index=True)
    overall_dependency_score = Column(Float, nullable=False)
    approval_dependency = Column(Float, nullable=True)
    revenue_dependency = Column(Float, nullable=True)
    client_dependency = Column(Float, nullable=True)
    decision_dependency = Column(Float, nullable=True)
    operational_dependency = Column(Float, nullable=True)
    automation_coverage_pct = Column(Float, nullable=True)
    pending_approval_count = Column(Integer, default=0)
    automation_opportunities = Column(JSON, default=list)
    delegation_opportunities = Column(JSON, default=list)
    single_point_alerts = Column(JSON, default=list)
    target_score = Column(Float, default=20.0)
    trend = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MoatMetrics(Base):
    __tablename__ = "moat_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(SUUID(as_uuid=True), nullable=True, index=True)
    snapshot_date = Column(DateTime(timezone=True), nullable=True, index=True)
    moat_score = Column(Float, nullable=True)
    proprietary_data_score = Column(Float, nullable=True)
    case_study_count = Column(Integer, default=0)
    delivery_intelligence_score = Column(Float, nullable=True)
    relationship_graph_score = Column(Float, nullable=True)
    institutional_wisdom_score = Column(Float, nullable=True)
    automation_advantage_score = Column(Float, nullable=True)
    operational_speed_score = Column(Float, nullable=True)
    competitive_threat_score = Column(Float, nullable=True)
    defensibility_report = Column(Text, nullable=True)
    threats_identified = Column(JSON, default=list)
    strengths_identified = Column(JSON, default=list)
    strategic_actions = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
