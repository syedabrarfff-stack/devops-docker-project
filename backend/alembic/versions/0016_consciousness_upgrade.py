"""JARVIS Consciousness Upgrade — soul, heart, council, vision, offer, competitive.

Revision ID: 0016_consciousness_upgrade
Revises: 0015_connector_hub_timestamps
Create Date: 2026-06-04
"""
from __future__ import annotations

from alembic import op

revision = "0016_consciousness_upgrade"
down_revision = "0015_connector_hub_timestamps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Competitor intelligence profiles
    op.execute("""
        CREATE TABLE IF NOT EXISTS competitor_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_name TEXT NOT NULL UNIQUE,
            pricing_model TEXT,
            customer_acquisition TEXT,
            moat_type TEXT,
            weakness_vector TEXT,
            positioning_gap TEXT,
            growth_trajectory TEXT,
            fragility_signals JSONB NOT NULL DEFAULT '[]',
            recommended_stance TEXT,
            competitive_opportunity TEXT,
            confidence_score FLOAT NOT NULL DEFAULT 0.0,
            intelligence_sources JSONB NOT NULL DEFAULT '[]',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Council of Giants session log
    op.execute("""
        CREATE TABLE IF NOT EXISTS giants_council_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            decision_type TEXT NOT NULL,
            context_summary TEXT,
            giants_consulted JSONB NOT NULL DEFAULT '[]',
            synthesis TEXT,
            full_response JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Prospect emotional profiles
    op.execute("""
        CREATE TABLE IF NOT EXISTS prospect_emotional_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            lead_id TEXT NOT NULL,
            company_name TEXT NOT NULL,
            primary_driver TEXT,
            secondary_driver TEXT,
            relationship_momentum TEXT,
            communication_style TEXT,
            decision_style TEXT,
            objection_profile JSONB NOT NULL DEFAULT '[]',
            recommended_message_frame TEXT,
            recommended_close_frame TEXT,
            personalization_hooks JSONB NOT NULL DEFAULT '[]',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Vision horizon snapshots
    op.execute("""
        CREATE TABLE IF NOT EXISTS vision_horizon_snapshots (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            current_milestone TEXT,
            horizon_map JSONB NOT NULL DEFAULT '{}',
            trajectory TEXT,
            mrr_at_snapshot FLOAT NOT NULL DEFAULT 0.0,
            clients_at_snapshot INT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # JARVIS upgrade plans
    op.execute("""
        CREATE TABLE IF NOT EXISTS jarvis_upgrade_plans (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            overall_health_score FLOAT NOT NULL DEFAULT 0.0,
            health_label TEXT,
            dimension_scores JSONB NOT NULL DEFAULT '{}',
            weak_dimensions JSONB NOT NULL DEFAULT '[]',
            upgrade_actions JSONB NOT NULL DEFAULT '[]',
            generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Failure principles log
    op.execute("""
        CREATE TABLE IF NOT EXISTS failure_principles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            failure_type TEXT NOT NULL,
            failure_detail TEXT,
            root_cause TEXT,
            prevention_principle TEXT NOT NULL,
            logged_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS failure_principles")
    op.execute("DROP TABLE IF EXISTS jarvis_upgrade_plans")
    op.execute("DROP TABLE IF EXISTS vision_horizon_snapshots")
    op.execute("DROP TABLE IF EXISTS prospect_emotional_profiles")
    op.execute("DROP TABLE IF EXISTS giants_council_sessions")
    op.execute("DROP TABLE IF EXISTS competitor_profiles")
