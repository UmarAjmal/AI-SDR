"""Add email infrastructure and campaign orchestration models

Revision ID: 004_email_and_campaigns
Revises: 003_crm_and_leads
Create Date: 2026-09-08 19:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_email_and_campaigns'
down_revision: Union[str, None] = '003_crm_and_leads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Email Accounts
    op.create_table(
        'email_accounts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('provider', sa.Enum('GOOGLE', 'MICROSOFT', 'SMTP', name='email_provider_type'), nullable=False),
        sa.Column('email_address', sa.String(length=255), nullable=False),
        sa.Column('encrypted_credentials', sa.Text(), nullable=False),
        sa.Column('daily_send_limit', sa.Integer(), nullable=False, default=40),
        sa.Column('current_day_sends', sa.Integer(), nullable=False, default=0),
        sa.Column('last_send_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('health_status', sa.Enum('HEALTHY', 'PAUSED', 'REVOKED', 'WARMUP', name='mailbox_health_status'), nullable=False, default='HEALTHY'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_email_accounts_workspace_id', 'email_accounts', ['workspace_id'], unique=False)
    op.create_index('ix_email_accounts_email_address', 'email_accounts', ['email_address'], unique=False)

    # 2. Email Threads
    op.create_table(
        'email_threads',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('lead_id', sa.String(length=36), nullable=True),
        sa.Column('campaign_id', sa.String(length=36), nullable=True),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('status', sa.Enum('OPEN', 'REPLIED', 'CLOSED', 'BOUNCED', name='thread_status'), nullable=False, default='OPEN'),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['crm_leads.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_email_threads_workspace_id', 'email_threads', ['workspace_id'], unique=False)
    op.create_index('ix_email_threads_lead_id', 'email_threads', ['lead_id'], unique=False)
    op.create_index('ix_email_threads_campaign_id', 'email_threads', ['campaign_id'], unique=False)

    # 3. Email Messages
    op.create_table(
        'email_messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('thread_id', sa.String(length=36), nullable=False),
        sa.Column('provider_message_id', sa.String(length=255), nullable=True),
        sa.Column('direction', sa.Enum('OUTBOUND', 'INBOUND', name='message_direction'), nullable=False),
        sa.Column('from_address', sa.String(length=255), nullable=False),
        sa.Column('to_address', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('body_text', sa.Text(), nullable=False),
        sa.Column('body_html', sa.Text(), nullable=True),
        sa.Column('headers_json', sa.JSON(), nullable=False),
        sa.Column('delivery_status', sa.Enum('PENDING', 'SENT', 'DELIVERED', 'BOUNCED', 'FAILED', name='delivery_status'), nullable=False, default='SENT'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['thread_id'], ['email_threads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_email_messages_workspace_id', 'email_messages', ['workspace_id'], unique=False)
    op.create_index('ix_email_messages_thread_id', 'email_messages', ['thread_id'], unique=False)
    op.create_index('ix_email_messages_provider_message_id', 'email_messages', ['provider_message_id'], unique=False)

    # 4. Suppression List
    op.create_table(
        'suppression_list',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('reason', sa.Enum('UNSUBSCRIBE', 'HARD_BOUNCE', 'COMPLAINT', 'MANUAL', name='suppression_reason'), nullable=False, default='UNSUBSCRIBE'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'email', name='uq_suppression_workspace_email')
    )
    op.create_index('ix_suppression_list_workspace_id', 'suppression_list', ['workspace_id'], unique=False)
    op.create_index('ix_suppression_list_email', 'suppression_list', ['email'], unique=False)
    op.create_index('ix_suppression_list_domain', 'suppression_list', ['domain'], unique=False)

    # 5. Campaigns
    op.create_table(
        'campaigns',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'REVIEW', 'SCHEDULED', 'RUNNING', 'PAUSED', 'COMPLETED', 'ARCHIVED', name='campaign_state'), nullable=False, default='DRAFT'),
        sa.Column('objective', sa.String(length=255), nullable=False, default='DEMO_BOOKING'),
        sa.Column('config_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_campaigns_workspace_id', 'campaigns', ['workspace_id'], unique=False)
    op.create_index('ix_campaigns_status', 'campaigns', ['status'], unique=False)

    # 6. Campaign Steps
    op.create_table(
        'campaign_steps',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('campaign_id', sa.String(length=36), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('delay_days', sa.Integer(), nullable=False, default=3),
        sa.Column('delay_hours', sa.Integer(), nullable=False, default=0),
        sa.Column('prompt_instructions', sa.Text(), nullable=True),
        sa.Column('template_config_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('campaign_id', 'step_number', name='uq_campaign_step_number')
    )
    op.create_index('ix_campaign_steps_campaign_id', 'campaign_steps', ['campaign_id'], unique=False)

    # 7. Campaign Leads
    op.create_table(
        'campaign_leads',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('campaign_id', sa.String(length=36), nullable=False),
        sa.Column('lead_id', sa.String(length=36), nullable=False),
        sa.Column('current_step_number', sa.Integer(), nullable=False, default=1),
        sa.Column('state', sa.Enum('QUEUED', 'WAITING', 'READY', 'SENT', 'REPLIED', 'PAUSED', 'UNSUBSCRIBED', 'BOUNCED', 'MEETING_BOOKED', 'QUALIFIED', 'DISQUALIFIED', 'HANDOFF', 'COMPLETED', name='lead_sequence_state'), nullable=False, default='QUEUED'),
        sa.Column('next_action_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lead_id'], ['crm_leads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('campaign_id', 'lead_id', name='uq_campaign_lead_enrollment')
    )
    op.create_index('ix_campaign_leads_workspace_id', 'campaign_leads', ['workspace_id'], unique=False)
    op.create_index('ix_campaign_leads_campaign_id', 'campaign_leads', ['campaign_id'], unique=False)
    op.create_index('ix_campaign_leads_lead_id', 'campaign_leads', ['lead_id'], unique=False)
    op.create_index('ix_campaign_leads_state', 'campaign_leads', ['state'], unique=False)
    op.create_index('ix_campaign_leads_next_action_at', 'campaign_leads', ['next_action_at'], unique=False)

    # 8. Conversation Events (5-Question Audit Trail)
    op.create_table(
        'conversation_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('lead_id', sa.String(length=36), nullable=True),
        sa.Column('campaign_id', sa.String(length=36), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('rule_matched', sa.String(length=255), nullable=True),
        sa.Column('model_version', sa.String(length=100), nullable=True),
        sa.Column('prompt_version', sa.String(length=100), nullable=True),
        sa.Column('knowledge_chunk_ids', sa.JSON(), nullable=False),
        sa.Column('previous_state', sa.String(length=100), nullable=True),
        sa.Column('new_state', sa.String(length=100), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['lead_id'], ['crm_leads.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_conversation_events_workspace_id', 'conversation_events', ['workspace_id'], unique=False)
    op.create_index('ix_conversation_events_lead_id', 'conversation_events', ['lead_id'], unique=False)
    op.create_index('ix_conversation_events_campaign_id', 'conversation_events', ['campaign_id'], unique=False)
    op.create_index('ix_conversation_events_event_type', 'conversation_events', ['event_type'], unique=False)
    op.create_index('ix_conversation_events_created_at', 'conversation_events', ['created_at'], unique=False)

def downgrade() -> None:
    op.drop_table('conversation_events')
    op.drop_table('campaign_leads')
    op.drop_table('campaign_steps')
    op.drop_table('campaigns')
    op.drop_table('suppression_list')
    op.drop_table('email_messages')
    op.drop_table('email_threads')
    op.drop_table('email_accounts')
    op.execute("DROP TYPE IF EXISTS lead_sequence_state;")
    op.execute("DROP TYPE IF EXISTS campaign_state;")
    op.execute("DROP TYPE IF EXISTS suppression_reason;")
    op.execute("DROP TYPE IF EXISTS delivery_status;")
    op.execute("DROP TYPE IF EXISTS message_direction;")
    op.execute("DROP TYPE IF EXISTS thread_status;")
    op.execute("DROP TYPE IF EXISTS mailbox_health_status;")
    op.execute("DROP TYPE IF EXISTS email_provider_type;")
