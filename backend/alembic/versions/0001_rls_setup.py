"""Apply tenant row-level security to every JARVIS table.

Revision ID: 0001_rls_setup
Revises:
Create Date: 2026-06-01
"""
from __future__ import annotations

from alembic import op

revision = "0001_rls_setup"
down_revision = None
branch_labels = None
depends_on = None


TABLES = (
    "agent_messages",
    "agent_permissions",
    "agent_tasks",
    "ai_request_logs",
    "approval_requests",
    "audit_logs",
    "clients",
    "companies",
    "contacts",
    "contract_templates",
    "conversation_summaries",
    "conversations",
    "deals",
    "email_tracking",
    "follow_up_queue",
    "gmail_messages",
    "incident_reports",
    "invoices",
    "knowledge_base",
    "leads",
    "learning_records",
    "memories",
    "notification_logs",
    "optimization_recommendations",
    "outcome_records",
    "outreach_emails",
    "outreach_log",
    "outreach_sequences",
    "proposals",
    "research_reports",
    "scheduled_jobs",
    "service_divisions",
    "sop_documents",
    "team_members",
    "tech_radar_entries",
    "tenants",
    "users",
    "workflow_runs",
)


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _policy_name(table: str) -> str:
    return f"rls_{table}_tenant_isolation"


def _index_name(table: str) -> str:
    return f"idx_{table}_tenant_id"


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_tenant_context(tenant_uuid uuid)
        RETURNS void
        LANGUAGE plpgsql
        AS $$
        BEGIN
            PERFORM set_config('app.current_tenant_id', tenant_uuid::text, true);
        END;
        $$;
        """
    )

    for table in TABLES:
        quoted_table = _quote(table)
        quoted_policy = _quote(_policy_name(table))
        quoted_index = _quote(_index_name(table))

        op.execute(f"ALTER TABLE {quoted_table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"DROP POLICY IF EXISTS {quoted_policy} ON {quoted_table};")
        op.execute(
            f"""
            CREATE POLICY {quoted_policy}
            ON {quoted_table}
            USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
            """
        )
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {quoted_index} ON {quoted_table} (tenant_id);"
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        quoted_table = _quote(table)
        quoted_policy = _quote(_policy_name(table))
        quoted_index = _quote(_index_name(table))

        op.execute(f"DROP POLICY IF EXISTS {quoted_policy} ON {quoted_table};")
        op.execute(f"ALTER TABLE {quoted_table} DISABLE ROW LEVEL SECURITY;")
        op.execute(f"DROP INDEX IF EXISTS {quoted_index};")

    op.execute("DROP FUNCTION IF EXISTS set_tenant_context(uuid);")
