"""Add CRM connections, canonical leads, and lead enrichment tables

Revision ID: 003_crm_and_leads
Revises: 002_knowledge_models
Create Date: 2026-09-08 19:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_crm_and_leads'
down_revision: Union[str, None] = '002_knowledge_models'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. CRM Connections
    op.create_table(
        'crm_connections',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('provider', sa.Enum('HUBSPOT', 'SALESFORCE', 'PIPEDRIVE', name='crm_provider_type'), nullable=False),
        sa.Column('account_id', sa.String(length=100), nullable=True),
        sa.Column('account_name', sa.String(length=255), nullable=True),
        sa.Column('encrypted_access_token', sa.Text(), nullable=False),
        sa.Column('encrypted_refresh_token', sa.Text(), nullable=False),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('field_mappings_json', sa.JSON(), nullable=False),
        sa.Column('sync_status', sa.Enum('CONNECTED', 'SYNCING', 'PAUSED', 'REVOKED', 'ERROR', name='crm_sync_status'), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_cursor', sa.String(length=255), nullable=True),
        sa.Column('sync_error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_crm_connections_workspace_id', 'crm_connections', ['workspace_id'], unique=False)

    # 2. Canonical CRM Leads
    op.create_table(
        'crm_leads',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('crm_connection_id', sa.String(length=36), nullable=True),
        sa.Column('crm_record_id', sa.String(length=100), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=100), nullable=True),
        sa.Column('job_title', sa.String(length=255), nullable=True),
        sa.Column('company_name', sa.String(length=255), nullable=True),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('industry', sa.String(length=255), nullable=True),
        sa.Column('employee_count', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('revenue_band', sa.String(length=100), nullable=True),
        sa.Column('lifecycle_stage', sa.String(length=100), nullable=True),
        sa.Column('owner_id', sa.String(length=100), nullable=True),
        sa.Column('lead_notes', sa.Text(), nullable=True),
        sa.Column('custom_fields', sa.JSON(), nullable=False),
        sa.Column('opt_out', sa.Boolean(), nullable=False, default=False),
        sa.Column('do_not_contact', sa.Boolean(), nullable=False, default=False),
        sa.Column('bounce_status', sa.String(length=50), nullable=False, default='NONE'),
        sa.Column('icp_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('intent_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('total_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('score_reasons_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['crm_connection_id'], ['crm_connections.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'email', name='uq_crm_leads_workspace_email')
    )
    op.create_index('ix_crm_leads_workspace_id', 'crm_leads', ['workspace_id'], unique=False)
    op.create_index('ix_crm_leads_email', 'crm_leads', ['email'], unique=False)
    op.create_index('ix_crm_leads_domain', 'crm_leads', ['domain'], unique=False)
    op.create_index('ix_crm_leads_crm_connection_id', 'crm_leads', ['crm_connection_id'], unique=False)
    op.create_index('ix_crm_leads_crm_record_id', 'crm_leads', ['crm_record_id'], unique=False)
    op.create_index('ix_crm_leads_opt_out', 'crm_leads', ['opt_out'], unique=False)
    op.create_index('ix_crm_leads_do_not_contact', 'crm_leads', ['do_not_contact'], unique=False)
    op.create_index('ix_crm_leads_total_score', 'crm_leads', ['total_score'], unique=False)

    # 3. Lead Enrichment
    op.create_table(
        'lead_enrichments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('lead_id', sa.String(length=36), nullable=False),
        sa.Column('company_summary', sa.Text(), nullable=True),
        sa.Column('role_summary', sa.Text(), nullable=True),
        sa.Column('detected_technologies', sa.JSON(), nullable=False),
        sa.Column('signals_json', sa.JSON(), nullable=False),
        sa.Column('source_urls', sa.JSON(), nullable=False),
        sa.Column('enriched_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['crm_leads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lead_id', name='uq_lead_enrichments_lead_id')
    )
    op.create_index('ix_lead_enrichments_workspace_id', 'lead_enrichments', ['workspace_id'], unique=False)

def downgrade() -> None:
    op.drop_table('lead_enrichments')
    op.drop_table('crm_leads')
    op.drop_table('crm_connections')
    op.execute("DROP TYPE IF EXISTS crm_sync_status;")
    op.execute("DROP TYPE IF EXISTS crm_provider_type;")
