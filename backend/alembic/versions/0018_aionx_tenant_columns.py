"""AIONX schema repair — guarantee all JarvisBase columns on every organ table.

JarvisBase (app/models/base.py) declares id, tenant_id, created_at, updated_at on
EVERY model. The ORM therefore SELECTs all four on all AIONX tables. The 0017
migration created tenant_id/updated_at on only a few tables, so reads 500 with
"column does not exist" (Postgres reports tenant_id first, updated_at next).

This migration adds tenant_id, created_at, updated_at (all idempotent, nullable
tenant_id since organ records may be system-level) to every AIONX table.
Safe to re-run on the already-migrated EC2 database.

Revision ID: 0018_aionx_tenant_columns
Revises: 0017_aionx_sovereign_organs
Create Date: 2026-06-04
"""
from __future__ import annotations

from alembic import op

revision = "0018_aionx_tenant_columns"
down_revision = "0017_aionx_sovereign_organs"
branch_labels = None
depends_on = None

AIONX_TABLES = [
    "decision_objects",
    "decision_options",
    "decision_outcomes",
    "decision_patterns",
    "decision_retrospectives",
    "counterfactual_simulations",
    "counterfactual_actualizations",
    "decision_debt_assessments",
    "institutional_debt_index",
    "client_digital_twins",
    "client_twin_interactions",
    "client_twin_predictions",
    "wisdom_index_snapshots",
    "provider_calibration_records",
    "provider_council_sessions",
    "shelved_discoveries",
    "convergence_council_sessions",
    "convergence_council_messages",
    "mission_autopsies",
    "sentinel_observations",
    "sentinel_threat_registry",
    "mission_ownership_records",
    "self_modification_registry",
]


def upgrade() -> None:
    for table in AIONX_TABLES:
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS tenant_id UUID")
        op.execute(
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS created_at "
            "TIMESTAMPTZ NOT NULL DEFAULT now()"
        )
        op.execute(
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS updated_at "
            "TIMESTAMPTZ NOT NULL DEFAULT now()"
        )
        op.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{table}_tenant ON {table}(tenant_id)"
        )


def downgrade() -> None:
    for table in AIONX_TABLES:
        op.execute(f"DROP INDEX IF EXISTS idx_{table}_tenant")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS tenant_id")
        # created_at/updated_at intentionally retained on downgrade (base columns)
