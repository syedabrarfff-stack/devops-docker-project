"""AIONX omni registry and mission control.

Revision ID: 0024_aionx_omni
Revises: 0023_aionx_frontier
Create Date: 2026-06-05
"""
from __future__ import annotations

from alembic import op

revision = "0024_aionx_omni"
down_revision = "0023_aionx_frontier"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_omni_system_registry (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            system_number INTEGER NOT NULL,
            system_key TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'DESIGN_GOVERNED',
            capability_level TEXT NOT NULL DEFAULT 'doctrine',
            description TEXT NOT NULL,
            live_endpoint TEXT,
            persistence_table TEXT,
            scheduler_job TEXT,
            governance_boundary TEXT NOT NULL,
            dependencies JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_omni_registry_category ON aionx_omni_system_registry(category)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_omni_registry_status ON aionx_omni_system_registry(status)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_mission_control_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            agent TEXT NOT NULL,
            status TEXT NOT NULL,
            action TEXT NOT NULL,
            result TEXT NOT NULL DEFAULT 'observing',
            severity TEXT NOT NULL DEFAULT 'INFO',
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_mission_control_created ON aionx_mission_control_events(created_at)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_system_hud_snapshots (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            operational_iq NUMERIC NOT NULL DEFAULT 50,
            backend_status TEXT NOT NULL DEFAULT 'unknown',
            database_status TEXT NOT NULL DEFAULT 'unknown',
            redis_status TEXT NOT NULL DEFAULT 'unknown',
            scheduler_jobs INTEGER NOT NULL DEFAULT 0,
            aionx_jobs INTEGER NOT NULL DEFAULT 0,
            systems_total INTEGER NOT NULL DEFAULT 227,
            systems_live INTEGER NOT NULL DEFAULT 0,
            systems_governed INTEGER NOT NULL DEFAULT 0,
            alerts JSONB NOT NULL DEFAULT '[]'::jsonb,
            snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_stability_runbooks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            risk_key TEXT NOT NULL UNIQUE,
            risk_name TEXT NOT NULL,
            severity TEXT NOT NULL,
            diagnosis TEXT NOT NULL,
            mitigation TEXT NOT NULL,
            captain_alert_required BOOLEAN NOT NULL DEFAULT true,
            automation_level TEXT NOT NULL DEFAULT 'governed',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_self_healing_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            component TEXT NOT NULL,
            symptom TEXT NOT NULL,
            diagnosis TEXT NOT NULL,
            action_taken TEXT NOT NULL,
            automation_level TEXT NOT NULL DEFAULT 'non_destructive',
            result TEXT NOT NULL DEFAULT 'recorded',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS aionx_self_healing_records")
    op.execute("DROP TABLE IF EXISTS aionx_stability_runbooks")
    op.execute("DROP TABLE IF EXISTS aionx_system_hud_snapshots")
    op.execute("DROP TABLE IF EXISTS aionx_mission_control_events")
    op.execute("DROP TABLE IF EXISTS aionx_omni_system_registry")
