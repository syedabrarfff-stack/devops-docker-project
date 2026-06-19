"""Add performance indexes across CRM, memory, approval, revenue, and scheduling tables.

Revision ID: 0027_performance_indexes
Revises: 0026_leads_whatsapp_linkedin
Create Date: 2026-06-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0027_performance_indexes"
down_revision = "0026_leads_whatsapp_linkedin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CRM — FK columns used in WHERE filters
    op.create_index("ix_contacts_company_id", "contacts", ["company_id"])
    op.create_index("ix_companies_status", "companies", ["status"])
    op.create_index("ix_deals_contact_id", "deals", ["contact_id"])
    op.create_index("ix_deals_company_id", "deals", ["company_id"])

    # Approvals — hot query: pending per tenant
    op.create_index("ix_approval_requests_tenant_status", "approval_requests", ["tenant_id", "status"])

    # Memory — order by created_at per tenant
    op.create_index("ix_memory_operational_tenant_created", "memory_operational", ["tenant_id", "created_at"])
    op.create_index("ix_memory_strategic_tenant_created", "memory_strategic", ["tenant_id", "created_at"])
    op.create_index("ix_memory_graph_nodes_tenant_updated", "memory_graph_nodes", ["tenant_id", "updated_at"])

    # Revenue — filter unpaid/overdue invoices per tenant
    op.create_index("ix_invoices_tenant_status", "invoices", ["tenant_id", "status"])

    # Scheduling — enabled jobs ordered by next run
    op.create_index("ix_scheduled_jobs_enabled_next_run", "scheduled_jobs", ["enabled", "next_run_at"])
    op.create_index("ix_job_failures_job_name_status", "job_failures", ["job_name", "status"])

    # Civilization — filter by event type per tenant
    op.create_index("ix_civilization_ledger_tenant_event_type", "civilization_ledger", ["tenant_id", "event_type"])

    # Connector Hub — daily ingestion lookup per tenant
    op.create_index("ix_connector_hub_ingestions_tenant_date", "connector_hub_ingestions", ["tenant_id", "date"])
    op.create_index("ix_connector_hub_packages_tenant_type", "connector_hub_packages", ["tenant_id", "package_type"])


def downgrade() -> None:
    op.drop_index("ix_connector_hub_packages_tenant_type", "connector_hub_packages")
    op.drop_index("ix_connector_hub_ingestions_tenant_date", "connector_hub_ingestions")
    op.drop_index("ix_civilization_ledger_tenant_event_type", "civilization_ledger")
    op.drop_index("ix_job_failures_job_name_status", "job_failures")
    op.drop_index("ix_scheduled_jobs_enabled_next_run", "scheduled_jobs")
    op.drop_index("ix_invoices_tenant_status", "invoices")
    op.drop_index("ix_memory_graph_nodes_tenant_updated", "memory_graph_nodes")
    op.drop_index("ix_memory_strategic_tenant_created", "memory_strategic")
    op.drop_index("ix_memory_operational_tenant_created", "memory_operational")
    op.drop_index("ix_approval_requests_tenant_status", "approval_requests")
    op.drop_index("ix_deals_company_id", "deals")
    op.drop_index("ix_deals_contact_id", "deals")
    op.drop_index("ix_companies_status", "companies")
    op.drop_index("ix_contacts_company_id", "contacts")
