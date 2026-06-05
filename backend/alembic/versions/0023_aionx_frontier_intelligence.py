"""AIONX frontier intelligence persistence.

Revision ID: 0023_aionx_frontier
Revises: 0022_aionx_mission_validation
Create Date: 2026-06-05
"""
from __future__ import annotations

from alembic import op

revision = "0023_aionx_frontier"
down_revision = "0022_aionx_mission_validation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_captain_decisions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            action TEXT NOT NULL,
            context JSONB NOT NULL DEFAULT '{}'::jsonb,
            reasoning TEXT,
            outcome TEXT,
            decision TEXT NOT NULL DEFAULT 'unknown',
            confidence NUMERIC NOT NULL DEFAULT 0.5,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_captain_decisions_decision ON aionx_captain_decisions(decision)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_experiments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            name TEXT NOT NULL,
            target_metric TEXT NOT NULL,
            variants JSONB NOT NULL DEFAULT '[]'::jsonb,
            default_variant TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            winner TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_experiment_outcomes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            experiment_id UUID NOT NULL,
            prospect_id TEXT,
            variant TEXT NOT NULL,
            outcome TEXT NOT NULL,
            metric_value NUMERIC NOT NULL DEFAULT 0,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_experiment_outcomes_exp ON aionx_experiment_outcomes(experiment_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_service_concepts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            target_client TEXT NOT NULL,
            pricing TEXT NOT NULL,
            delivery_method TEXT NOT NULL,
            sales_script TEXT NOT NULL,
            proposal_template TEXT NOT NULL,
            source_signals JSONB NOT NULL DEFAULT '[]'::jsonb,
            status TEXT NOT NULL DEFAULT 'captain_review',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_psychology_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            lead_id TEXT NOT NULL,
            communication_style TEXT NOT NULL,
            decision_pattern TEXT NOT NULL,
            price_sensitivity TEXT NOT NULL,
            risk_tolerance TEXT NOT NULL,
            motivator TEXT NOT NULL,
            response_pattern TEXT NOT NULL,
            profile JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_psychology_profiles_lead ON aionx_psychology_profiles(lead_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_threat_alerts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            threat_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            confidence NUMERIC NOT NULL DEFAULT 0.5,
            summary TEXT NOT NULL,
            recommended_action TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            resolved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_threat_alerts_status ON aionx_threat_alerts(status)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_intelligence_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            source_department TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            propagated_to JSONB NOT NULL DEFAULT '[]'::jsonb,
            audit_trail JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_knowledge_artifacts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            artifact_type TEXT NOT NULL,
            content TEXT NOT NULL,
            tags JSONB NOT NULL DEFAULT '[]'::jsonb,
            importance_score NUMERIC NOT NULL DEFAULT 0.5,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            immutable BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_agent_capacity (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            department TEXT NOT NULL,
            tasks_queued INTEGER NOT NULL DEFAULT 0,
            response_time_minutes NUMERIC NOT NULL DEFAULT 0,
            backlog_size INTEGER NOT NULL DEFAULT 0,
            capacity_percent NUMERIC NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'normal',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_agent_proposals (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            department TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            role TEXT NOT NULL,
            responsibilities JSONB NOT NULL DEFAULT '[]'::jsonb,
            kpis JSONB NOT NULL DEFAULT '[]'::jsonb,
            status TEXT NOT NULL DEFAULT 'captain_review',
            proposal JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS aionx_agent_proposals")
    op.execute("DROP TABLE IF EXISTS aionx_agent_capacity")
    op.execute("DROP TABLE IF EXISTS aionx_knowledge_artifacts")
    op.execute("DROP TABLE IF EXISTS aionx_intelligence_events")
    op.execute("DROP TABLE IF EXISTS aionx_threat_alerts")
    op.execute("DROP TABLE IF EXISTS aionx_psychology_profiles")
    op.execute("DROP TABLE IF EXISTS aionx_service_concepts")
    op.execute("DROP TABLE IF EXISTS aionx_experiment_outcomes")
    op.execute("DROP TABLE IF EXISTS aionx_experiments")
    op.execute("DROP TABLE IF EXISTS aionx_captain_decisions")
