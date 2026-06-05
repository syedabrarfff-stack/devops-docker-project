"""AIONX mission document and cross-validation persistence.

Revision ID: 0022_aionx_mission_validation
Revises: 0021_aionx_ops_persistence
Create Date: 2026-06-05
"""
from __future__ import annotations

from alembic import op

revision = "0022_aionx_mission_validation"
down_revision = "0021_aionx_ops_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_mission_documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            mission_id UUID NOT NULL,
            document_type TEXT NOT NULL,
            author TEXT NOT NULL DEFAULT 'JARVIS',
            content TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            content_size_bytes INTEGER NOT NULL DEFAULT 0,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            immutable BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_mission_documents_mission ON aionx_mission_documents(mission_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_mission_documents_type ON aionx_mission_documents(document_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_mission_documents_created ON aionx_mission_documents(created_at)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_cross_validation_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            validation_type TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'INFO',
            verdict TEXT NOT NULL DEFAULT 'PASS',
            checks JSONB NOT NULL DEFAULT '[]'::jsonb,
            blockers JSONB NOT NULL DEFAULT '[]'::jsonb,
            recommendations JSONB NOT NULL DEFAULT '[]'::jsonb,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_by TEXT NOT NULL DEFAULT 'CROSS_DEPARTMENT_VALIDATION',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_cross_validation_type ON aionx_cross_validation_records(validation_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_cross_validation_subject ON aionx_cross_validation_records(subject_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_cross_validation_verdict ON aionx_cross_validation_records(verdict)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS aionx_cross_validation_records")
    op.execute("DROP TABLE IF EXISTS aionx_mission_documents")
