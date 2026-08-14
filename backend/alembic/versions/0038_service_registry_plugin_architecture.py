"""Service Registry Plugin Architecture.

Create new tables for dynamic service catalog (replaces hardcoded modules).

Revision ID: 0038
Revises: 0037
Create Date: 2026-07-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0038'
down_revision = '0037'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ENUM types
    sa.Enum('active', 'beta', 'deprecated', 'archived', name='servicestatus').create(op.get_bind())
    sa.Enum('autonomous', 'human_supervised', 'hybrid', name='servicetype').create(op.get_bind())

    # Create service_registry table
    op.create_table(
        'service_registry',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.String(20), nullable=True, server_default='1.0.0'),
        sa.Column('status', sa.Enum('active', 'beta', 'deprecated', 'archived', name='servicestatus'), nullable=False, server_default='active'),
        sa.Column('division', sa.String(100), nullable=True),
        sa.Column('human_interface_executive', sa.String(200), nullable=True),
        sa.Column('service_type', sa.Enum('autonomous', 'human_supervised', 'hybrid', name='servicetype'), nullable=False, server_default='autonomous'),
        sa.Column('capability_flags', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('agent_layer', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('kpi_targets', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('dependencies', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('success_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('avg_execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('monthly_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deprecated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_service_registry_code')
    )
    op.create_index('idx_service_registry_status', 'service_registry', ['status'], unique=False)
    op.create_index('idx_service_registry_division', 'service_registry', ['division'], unique=False)
    op.create_index('idx_service_registry_tenant', 'service_registry', ['tenant_id'], unique=False)
    op.create_index('idx_service_registry_code', 'service_registry', ['code'], unique=False)

    # Create service_templates table
    op.create_table(
        'service_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('base_service_code', sa.String(50), nullable=True),
        sa.Column('configuration', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('required_capabilities', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('optional_capabilities', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('docker_image', sa.String(200), nullable=True),
        sa.Column('environment_template', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('agent_requirements', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('model_preferences', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_name')
    )
    op.create_index('idx_service_templates_name', 'service_templates', ['template_name'], unique=False)

    # Create service_instances table
    op.create_table(
        'service_instances',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('instance_name', sa.String(200), nullable=False),
        sa.Column('status', sa.Enum('active', 'beta', 'deprecated', 'archived', name='servicestatus'), nullable=False, server_default='beta'),
        sa.Column('configuration', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('environment', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('deployed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('deployment_region', sa.String(50), nullable=True),
        sa.Column('deployment_container_id', sa.String(200), nullable=True),
        sa.Column('is_healthy', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('last_health_check', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deprecated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['service_id'], ['service_registry.id'], ),
        sa.ForeignKeyConstraint(['template_id'], ['service_templates.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_service_instances_tenant', 'service_instances', ['tenant_id'], unique=False)
    op.create_index('idx_service_instances_service', 'service_instances', ['service_id'], unique=False)
    op.create_index('idx_service_instances_status', 'service_instances', ['status'], unique=False)

    # Create service_metrics table
    op.create_table(
        'service_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metric_date', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('total_executions', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('successful_executions', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('failed_executions', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('success_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('avg_execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('min_execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('max_execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('daily_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('monthly_cost_estimate', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('active_users', sa.Integer(), nullable=True),
        sa.Column('calls_per_user', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('error_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('avg_response_time_ms', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['service_id'], ['service_registry.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_service_metrics_service', 'service_metrics', ['service_id'], unique=False)
    op.create_index('idx_service_metrics_date', 'service_metrics', ['metric_date'], unique=False)

    # Create service_dependencies table
    op.create_table(
        'service_dependencies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('depends_on_service_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dependency_type', sa.String(50), nullable=True),
        sa.Column('is_critical', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['depends_on_service_id'], ['service_registry.id'], ),
        sa.ForeignKeyConstraint(['service_id'], ['service_registry.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_service_dependencies_service', 'service_dependencies', ['service_id'], unique=False)
    op.create_index('idx_service_dependencies_depends_on', 'service_dependencies', ['depends_on_service_id'], unique=False)

    # Create service_audit table
    op.create_table(
        'service_audit',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(50), nullable=True),
        sa.Column('actor', sa.String(200), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('change_description', sa.Text(), nullable=True),
        sa.Column('before_state', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('after_state', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['service_id'], ['service_registry.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_service_audit_service', 'service_audit', ['service_id'], unique=False)
    op.create_index('idx_service_audit_timestamp', 'service_audit', ['timestamp'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_service_audit_timestamp', table_name='service_audit')
    op.drop_index('idx_service_audit_service', table_name='service_audit')
    op.drop_index('idx_service_dependencies_depends_on', table_name='service_dependencies')
    op.drop_index('idx_service_dependencies_service', table_name='service_dependencies')
    op.drop_index('idx_service_metrics_date', table_name='service_metrics')
    op.drop_index('idx_service_metrics_service', table_name='service_metrics')
    op.drop_index('idx_service_instances_status', table_name='service_instances')
    op.drop_index('idx_service_instances_service', table_name='service_instances')
    op.drop_index('idx_service_instances_tenant', table_name='service_instances')
    op.drop_index('idx_service_templates_name', table_name='service_templates')
    op.drop_index('idx_service_registry_code', table_name='service_registry')
    op.drop_index('idx_service_registry_tenant', table_name='service_registry')
    op.drop_index('idx_service_registry_division', table_name='service_registry')
    op.drop_index('idx_service_registry_status', table_name='service_registry')

    # Drop tables
    op.drop_table('service_audit')
    op.drop_table('service_dependencies')
    op.drop_table('service_metrics')
    op.drop_table('service_instances')
    op.drop_table('service_templates')
    op.drop_table('service_registry')

    # Drop ENUMs
    sa.Enum('active', 'beta', 'deprecated', 'archived', name='servicestatus').drop(op.get_bind())
    sa.Enum('autonomous', 'human_supervised', 'hybrid', name='servicetype').drop(op.get_bind())
