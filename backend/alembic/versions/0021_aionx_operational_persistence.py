"""AIONX operational persistence and governed autonomy records.

Revision ID: 0021_aionx_operational_persistence
Revises: 0020_aionx_pipeline_history
Create Date: 2026-06-05
"""
from __future__ import annotations

from alembic import op

revision = "0021_aionx_operational_persistence"
down_revision = "0020_aionx_pipeline_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_mission_files (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            mission_id TEXT NOT NULL UNIQUE,
            client_name TEXT NOT NULL,
            objective TEXT NOT NULL,
            gateway TEXT NOT NULL DEFAULT 'AIONX COUNCIL',
            mission_status TEXT NOT NULL DEFAULT 'PLANNED',
            captain_required BOOLEAN NOT NULL DEFAULT false,
            mission_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            milestones JSONB NOT NULL DEFAULT '[]'::jsonb,
            governance_workflow JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_by TEXT NOT NULL DEFAULT 'JARVIS',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_mission_files_status ON aionx_mission_files(mission_status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_mission_files_created ON aionx_mission_files(created_at)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_milestone_plans (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            mission_file_id UUID NOT NULL,
            mission_id TEXT NOT NULL,
            milestone_number SMALLINT NOT NULL,
            title TEXT NOT NULL,
            owner TEXT NOT NULL DEFAULT 'JARVIS',
            status TEXT NOT NULL DEFAULT 'PENDING',
            success_criteria JSONB NOT NULL DEFAULT '[]'::jsonb,
            evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_milestone_plans_mission ON aionx_milestone_plans(mission_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_milestone_plans_status ON aionx_milestone_plans(status)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_qa_certificates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            certificate_id TEXT NOT NULL UNIQUE,
            mission_id TEXT,
            milestone_id TEXT,
            criteria JSONB NOT NULL DEFAULT '[]'::jsonb,
            failures JSONB NOT NULL DEFAULT '[]'::jsonb,
            verdict TEXT NOT NULL DEFAULT 'pending',
            client_delivery_allowed BOOLEAN NOT NULL DEFAULT false,
            next_route TEXT NOT NULL DEFAULT 'qa_review',
            certificate_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            issued_by TEXT NOT NULL DEFAULT 'QUALITY_ASSURANCE',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_qa_certificates_mission ON aionx_qa_certificates(mission_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_qa_certificates_verdict ON aionx_qa_certificates(verdict)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_repair_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            repair_id TEXT NOT NULL UNIQUE,
            mission_id TEXT,
            milestone_id TEXT,
            defect TEXT NOT NULL,
            root_cause TEXT NOT NULL,
            fix_required TEXT NOT NULL,
            verification TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'HIGH',
            route TEXT NOT NULL,
            repair_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            status TEXT NOT NULL DEFAULT 'OPEN',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_repair_records_status ON aionx_repair_records(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_repair_records_priority ON aionx_repair_records(priority)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_fallback_drill_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            component TEXT NOT NULL,
            failure_mode TEXT NOT NULL,
            fallback TEXT NOT NULL,
            target_activation_seconds INTEGER NOT NULL DEFAULT 120,
            captain_notification_required BOOLEAN NOT NULL DEFAULT false,
            drill_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            status TEXT NOT NULL DEFAULT 'RECORDED',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_fallback_drills_component ON aionx_fallback_drill_records(component)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_knowledge_synthesis_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            synthesis_id TEXT NOT NULL UNIQUE,
            mission_id TEXT,
            milestone_id TEXT,
            what_worked JSONB NOT NULL DEFAULT '[]'::jsonb,
            what_was_harder JSONB NOT NULL DEFAULT '[]'::jsonb,
            client_response TEXT NOT NULL DEFAULT 'not_recorded',
            memory_targets JSONB NOT NULL DEFAULT '[]'::jsonb,
            case_study_candidate BOOLEAN NOT NULL DEFAULT false,
            synthesis_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_knowledge_synthesis_mission ON aionx_knowledge_synthesis_records(mission_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_system_state_snapshots (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            overall_health_score FLOAT NOT NULL DEFAULT 0,
            system_state TEXT NOT NULL DEFAULT 'UNKNOWN',
            snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
            captured_by TEXT NOT NULL DEFAULT 'AIONX_STATE_HEARTBEAT',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_system_state_snapshots_created ON aionx_system_state_snapshots(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_system_state_snapshots_state ON aionx_system_state_snapshots(system_state)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_event_spine (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            event_type TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'JARVIS',
            severity TEXT NOT NULL DEFAULT 'INFO',
            correlation_id TEXT,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            governance_status TEXT NOT NULL DEFAULT 'RECORDED',
            captain_approval_required BOOLEAN NOT NULL DEFAULT false,
            processed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_event_spine_type_created ON aionx_event_spine(event_type, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_event_spine_governance ON aionx_event_spine(governance_status)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_autonomy_proposals (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            proposal_id TEXT NOT NULL UNIQUE,
            proposal_type TEXT NOT NULL DEFAULT 'SELF_IMPROVEMENT',
            title TEXT NOT NULL,
            rationale TEXT NOT NULL,
            blast_radius TEXT NOT NULL DEFAULT 'LOW',
            expected_benefit TEXT NOT NULL,
            rollback_plan TEXT NOT NULL,
            approval_status TEXT NOT NULL DEFAULT 'PENDING_CAPTAIN_REVIEW',
            proposal_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_by TEXT NOT NULL DEFAULT 'GENESIS_ENGINE',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_autonomy_proposals_status ON aionx_autonomy_proposals(approval_status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_autonomy_proposals_type ON aionx_autonomy_proposals(proposal_type)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aionx_external_scan_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            scan_type TEXT NOT NULL DEFAULT 'TECH_RADAR',
            source TEXT NOT NULL DEFAULT 'AIONX_SENTINEL',
            summary TEXT NOT NULL,
            findings JSONB NOT NULL DEFAULT '[]'::jsonb,
            recommended_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
            scan_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aionx_external_scan_records_type_created ON aionx_external_scan_records(scan_type, created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS aionx_external_scan_records")
    op.execute("DROP TABLE IF EXISTS aionx_autonomy_proposals")
    op.execute("DROP TABLE IF EXISTS aionx_event_spine")
    op.execute("DROP TABLE IF EXISTS aionx_system_state_snapshots")
    op.execute("DROP TABLE IF EXISTS aionx_knowledge_synthesis_records")
    op.execute("DROP TABLE IF EXISTS aionx_fallback_drill_records")
    op.execute("DROP TABLE IF EXISTS aionx_repair_records")
    op.execute("DROP TABLE IF EXISTS aionx_qa_certificates")
    op.execute("DROP TABLE IF EXISTS aionx_milestone_plans")
    op.execute("DROP TABLE IF EXISTS aionx_mission_files")
