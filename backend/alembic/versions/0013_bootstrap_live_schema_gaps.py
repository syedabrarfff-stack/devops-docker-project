"""Bootstrap live schema gaps after the merged vNEXT baseline.

Revision ID: 0013_bootstrap_live_schema_gaps
Revises: 0012_merge_master_prompt_and_frontier
Create Date: 2026-06-03
"""
from __future__ import annotations

from alembic import op

revision = "0013_bootstrap_live_schema_gaps"
down_revision = "0012_merge_master_prompt_and_frontier"
branch_labels = None
depends_on = None

RLS_TABLES = (
    "prospect_psychology_profiles",
    "revenue_forecasts",
    "self_assessment_reports",
    "client_health_scores",
    "dynamic_pricing_records",
    "autonomous_governance_log",
    "captain_brain_dumps",
    "captain_email_intelligence",
    "predicted_actions",
    "captain_pushbacks",
    "expert_council_sessions",
    "red_team_analyses",
    "relationship_nodes",
    "relationship_edges",
    "flywheel_snapshots",
    "cialdini_sessions",
)


def _enable_rls(table: str) -> None:
    policy = f"rls_{table}_tenant_isolation"
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = '{table}'
                  AND policyname = '{policy}'
            ) THEN
                EXECUTE 'CREATE POLICY {policy} ON {table}
                    USING (tenant_id = current_setting(''''app.current_tenant_id'''')::uuid)
                    WITH CHECK (tenant_id = current_setting(''''app.current_tenant_id'''')::uuid)';
            END IF;
        END $$;
        """
    )


def _add_unique_constraint(table: str, name: str, columns: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = '{name}'
            ) THEN
                ALTER TABLE {table} ADD CONSTRAINT {name} UNIQUE ({columns});
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS outreach_eligible BOOLEAN NOT NULL DEFAULT true")
    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS review_queue BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS disqualification_reason TEXT")
    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS signal_breakdown JSON NOT NULL DEFAULT '{}'::json")
    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS psychology_profile JSONB")
    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS predicted_value NUMERIC(10, 2)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_leads_outreach_eligible ON leads (outreach_eligible)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_leads_review_queue ON leads (review_queue)")

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'outreach_status') THEN
                ALTER TYPE outreach_status ADD VALUE IF NOT EXISTS 'SKIPPED';
            END IF;
        END $$;
        """
    )
    op.execute("ALTER TABLE outreach_log ADD COLUMN IF NOT EXISTS skip_reason VARCHAR(160)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_outreach_log_skip_reason ON outreach_log (skip_reason)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS prospect_psychology_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
            buying_style VARCHAR(20) NOT NULL,
            risk_tolerance VARCHAR(10) NOT NULL,
            decision_speed VARCHAR(15) NOT NULL,
            urgency_signals JSONB DEFAULT '[]'::jsonb,
            objection_forecast JSONB DEFAULT '[]'::jsonb,
            recommended_approach TEXT,
            personalization_hooks JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_psych_profiles_tenant_id ON prospect_psychology_profiles (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_psych_profiles_lead_id ON prospect_psychology_profiles (lead_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_psych_profiles_buying_style ON prospect_psychology_profiles (buying_style)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS revenue_forecasts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            p10_revenue NUMERIC(12, 2),
            p50_revenue NUMERIC(12, 2),
            p90_revenue NUMERIC(12, 2),
            horizon_days INTEGER NOT NULL DEFAULT 90,
            pipeline_size INTEGER NOT NULL DEFAULT 0,
            simulation_runs INTEGER NOT NULL DEFAULT 1000,
            forecast_date DATE,
            recommendations JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_revenue_forecasts_tenant_id ON revenue_forecasts (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_revenue_forecasts_forecast_date ON revenue_forecasts (forecast_date)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS self_assessment_reports (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            overall_grade VARCHAR(1) NOT NULL,
            overall_score NUMERIC(5, 2) NOT NULL,
            dimension_scores JSONB DEFAULT '{}'::jsonb,
            strengths JSONB DEFAULT '[]'::jsonb,
            weaknesses JSONB DEFAULT '[]'::jsonb,
            priority_actions JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_self_assessment_tenant_id ON self_assessment_reports (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_self_assessment_created_at ON self_assessment_reports (created_at)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS client_health_scores (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            client_id UUID,
            health_score NUMERIC(5, 2) NOT NULL,
            health_tier VARCHAR(20) NOT NULL,
            signals JSONB DEFAULT '[]'::jsonb,
            churn_probability NUMERIC(4, 3),
            recommended_actions JSONB DEFAULT '[]'::jsonb,
            next_touch_date DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_client_health_tenant_id ON client_health_scores (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_client_health_client_id ON client_health_scores (client_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_client_health_tier ON client_health_scores (health_tier)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_client_health_score ON client_health_scores (health_score)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS dynamic_pricing_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            lead_id UUID,
            service_type VARCHAR(100),
            base_price NUMERIC(10, 2),
            final_price NUMERIC(10, 2),
            price_tier VARCHAR(20),
            adjustments JSONB DEFAULT '[]'::jsonb,
            confidence NUMERIC(4, 3),
            rationale TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_pricing_records_tenant_id ON dynamic_pricing_records (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pricing_records_lead_id ON dynamic_pricing_records (lead_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pricing_records_price_tier ON dynamic_pricing_records (price_tier)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS autonomous_governance_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            action_type VARCHAR(100) NOT NULL,
            tier INTEGER NOT NULL,
            auto_executed BOOLEAN NOT NULL DEFAULT false,
            approval_required BOOLEAN NOT NULL DEFAULT false,
            payload JSONB DEFAULT '{}'::jsonb,
            outcome JSONB DEFAULT '{}'::jsonb,
            executed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_gov_log_tenant_id ON autonomous_governance_log (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_gov_log_action_type ON autonomous_governance_log (action_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_gov_log_tier ON autonomous_governance_log (tier)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_gov_log_created_at ON autonomous_governance_log (created_at)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS captain_brain_dumps (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            raw_text TEXT NOT NULL,
            action_items JSONB,
            leads_mentioned JSONB,
            decisions_made JSONB,
            follow_ups_needed JSONB,
            key_insights JSONB,
            processed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_brain_dumps_tenant_id ON captain_brain_dumps (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_brain_dumps_created_at ON captain_brain_dumps (created_at)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS captain_email_intelligence (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            raw_thread TEXT NOT NULL,
            sender VARCHAR(200),
            subject VARCHAR(500),
            key_asks JSONB,
            objections JSONB,
            buying_signals JSONB,
            recommended_next_step TEXT,
            urgency_score SMALLINT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_email_intel_tenant_id ON captain_email_intelligence (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_email_intel_urgency_score ON captain_email_intelligence (urgency_score)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_email_intel_created_at ON captain_email_intelligence (created_at)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS predicted_actions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            action_type VARCHAR(100) NOT NULL,
            priority SMALLINT NOT NULL,
            expected_impact TEXT,
            effort_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
            deadline_suggestion TIMESTAMPTZ,
            reasoning TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_predicted_actions_tenant_id ON predicted_actions (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_predicted_actions_priority ON predicted_actions (priority)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_predicted_actions_status ON predicted_actions (status)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS captain_pushbacks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            decision_text TEXT NOT NULL,
            verdict VARCHAR(20) NOT NULL,
            confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.000,
            risks JSONB,
            alternatives JSONB,
            final_recommendation TEXT,
            captain_overrode BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_pushbacks_tenant_id ON captain_pushbacks (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pushbacks_verdict ON captain_pushbacks (verdict)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pushbacks_created_at ON captain_pushbacks (created_at)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS expert_council_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            question TEXT NOT NULL,
            context JSONB,
            majority_recommendation TEXT,
            key_agreements JSONB,
            key_disagreements JSONB,
            confidence_score NUMERIC(4, 3),
            final_synthesis TEXT,
            agents_used INTEGER DEFAULT 5,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_expert_council_tenant_id ON expert_council_sessions (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_expert_council_created_at ON expert_council_sessions (created_at)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS red_team_analyses (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            attack_vectors JSONB,
            overall_risk_score NUMERIC(5, 2),
            critical_vulnerabilities JSONB,
            defensive_actions JSONB,
            next_assessment_date DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_red_team_analyses_tenant_id ON red_team_analyses (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_red_team_analyses_created_at ON red_team_analyses (created_at)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS relationship_nodes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            entity_type VARCHAR(20) NOT NULL,
            entity_id VARCHAR(100) NOT NULL,
            attributes JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    _add_unique_constraint(
        "relationship_nodes",
        "uq_relationship_nodes_entity",
        "tenant_id, entity_type, entity_id",
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_relationship_nodes_tenant_id ON relationship_nodes (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_relationship_nodes_entity_type ON relationship_nodes (entity_type)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS relationship_edges (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            from_node_id UUID NOT NULL REFERENCES relationship_nodes(id) ON DELETE CASCADE,
            to_node_id UUID NOT NULL REFERENCES relationship_nodes(id) ON DELETE CASCADE,
            relationship_type VARCHAR(50) NOT NULL,
            strength NUMERIC(3, 2) DEFAULT 1.00,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_relationship_edges_tenant_id ON relationship_edges (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_relationship_edges_from_node_id ON relationship_edges (from_node_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_relationship_edges_to_node_id ON relationship_edges (to_node_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS flywheel_snapshots (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            flywheel_velocity NUMERIC(4, 2),
            weakest_link VARCHAR(50),
            strongest_segment VARCHAR(50),
            momentum_trend VARCHAR(20),
            compound_growth_factor NUMERIC(6, 4),
            snapshot_date DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_flywheel_snapshots_tenant_id ON flywheel_snapshots (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_flywheel_snapshots_snapshot_date ON flywheel_snapshots (snapshot_date)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cialdini_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            lead_id UUID,
            original_email TEXT,
            enhanced_email TEXT,
            principles_applied JSONB,
            persuasion_score NUMERIC(5, 2),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_cialdini_sessions_tenant_id ON cialdini_sessions (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cialdini_sessions_lead_id ON cialdini_sessions (lead_id)")

    for table in RLS_TABLES:
        _enable_rls(table)


def downgrade() -> None:
    """No destructive downgrade for the live bootstrap migration."""
    return None
