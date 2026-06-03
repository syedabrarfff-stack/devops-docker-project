"""Fill master prompt contract gaps for lead and outreach tables.

Revision ID: 0009_master_prompt_contract_gaps
Revises: 0008_department_intelligence
Create Date: 2026-06-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_master_prompt_contract_gaps"
down_revision = "0008_department_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS outreach_eligible BOOLEAN NOT NULL DEFAULT true")
    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS review_queue BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS disqualification_reason TEXT")
    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS signal_breakdown JSON NOT NULL DEFAULT '{}'::json")
    op.execute("CREATE INDEX IF NOT EXISTS ix_leads_outreach_eligible ON leads (outreach_eligible)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_leads_review_queue ON leads (review_queue)")

    op.execute("ALTER TYPE outreach_status ADD VALUE IF NOT EXISTS 'SKIPPED'")
    op.execute("ALTER TABLE outreach_log ADD COLUMN IF NOT EXISTS skip_reason VARCHAR(160)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_outreach_log_skip_reason ON outreach_log (skip_reason)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_outreach_log_skip_reason")
    op.execute("ALTER TABLE outreach_log DROP COLUMN IF EXISTS skip_reason")
    op.execute("DROP INDEX IF EXISTS ix_leads_review_queue")
    op.execute("DROP INDEX IF EXISTS ix_leads_outreach_eligible")
    op.execute("ALTER TABLE leads DROP COLUMN IF EXISTS signal_breakdown")
    op.execute("ALTER TABLE leads DROP COLUMN IF EXISTS disqualification_reason")
    op.execute("ALTER TABLE leads DROP COLUMN IF EXISTS review_queue")
    op.execute("ALTER TABLE leads DROP COLUMN IF EXISTS outreach_eligible")
