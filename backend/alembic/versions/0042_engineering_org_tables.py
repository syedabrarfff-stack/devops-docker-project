"""E7-1: Create Engineering Organization tables (Mission Planner + departments).

Revision ID: 0042_engineering_org_tables
Revises: 0041_headquarters_action_requests
Create Date: 2026-07-08

Tables added:
  engineering_task_graphs    — one row per decomposed engineering objective
  engineering_work_packages  — one row per department-owned unit of work within a graph

Departments themselves are a code catalogue (app/services/engineering/department_registry.py),
matching the existing AI Council pattern — no departments table needed.

All tables use IF NOT EXISTS so the migration is idempotent.
"""
from __future__ import annotations

from alembic import op

revision = "0042_engineering_org_tables"
down_revision = "0041_headquarters_action_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── engineering_task_graphs ───────────────────────────────────────────────
    # One row per Mission Planner run: an objective decomposed into a DAG of
    # work packages. Status tracks the graph as a whole.
    op.execute("""
        CREATE TABLE IF NOT EXISTS engineering_task_graphs (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            objective           TEXT NOT NULL,
            objective_type      TEXT NOT NULL DEFAULT 'feature',
            status              TEXT NOT NULL DEFAULT 'PLANNING',
            decomposed_by       TEXT,
            context             JSONB NOT NULL DEFAULT '{}',
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at        TIMESTAMPTZ
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_task_graphs_status "
        "ON engineering_task_graphs (status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_task_graphs_created "
        "ON engineering_task_graphs (created_at)"
    )

    # ── engineering_work_packages ─────────────────────────────────────────────
    # One row per department-owned unit of work within a task graph.
    # depends_on is a UUID array referencing other work_packages in the same graph.
    op.execute("""
        CREATE TABLE IF NOT EXISTS engineering_work_packages (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            task_graph_id       UUID NOT NULL REFERENCES engineering_task_graphs(id) ON DELETE CASCADE,
            department          TEXT NOT NULL,
            title               TEXT NOT NULL,
            description         TEXT NOT NULL DEFAULT '',
            acceptance_criteria JSONB NOT NULL DEFAULT '[]',
            depends_on          UUID[] NOT NULL DEFAULT '{}',
            operation           TEXT NOT NULL DEFAULT 'bug.fix',
            authority_tier      TEXT,
            status              TEXT NOT NULL DEFAULT 'PENDING',
            kernel_task_id      UUID,
            draft_output        JSONB,
            review_result       JSONB,
            deploy_result       JSONB,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at        TIMESTAMPTZ
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_work_packages_graph "
        "ON engineering_work_packages (task_graph_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_work_packages_department "
        "ON engineering_work_packages (department)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_work_packages_status "
        "ON engineering_work_packages (status)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS engineering_work_packages")
    op.execute("DROP TABLE IF EXISTS engineering_task_graphs")
