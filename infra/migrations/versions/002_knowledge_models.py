"""Add knowledge models: business_profiles, knowledge_documents, knowledge_chunks with pgvector, website_scans

Revision ID: 002_knowledge_models
Revises: 001_initial_schema
Create Date: 2026-09-08 19:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '002_knowledge_models'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Business Profiles
    op.create_table(
        'business_profiles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('legal_name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('offerings', sa.JSON(), nullable=False),
        sa.Column('value_propositions', sa.JSON(), nullable=False),
        sa.Column('industries', sa.JSON(), nullable=False),
        sa.Column('icp_hints', sa.JSON(), nullable=False),
        sa.Column('pricing', sa.JSON(), nullable=True),
        sa.Column('features', sa.JSON(), nullable=False),
        sa.Column('faqs', sa.JSON(), nullable=False),
        sa.Column('proof', sa.JSON(), nullable=False),
        sa.Column('brand_voice', sa.JSON(), nullable=False),
        sa.Column('claims_policy', sa.JSON(), nullable=False),
        sa.Column('ctas', sa.JSON(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('confidence_score', sa.Float(), nullable=False, default=1.0),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_business_profiles_workspace_id', 'business_profiles', ['workspace_id'], unique=False)

    # 2. Knowledge Documents
    op.create_table(
        'knowledge_documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('screenshot_url', sa.Text(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_knowledge_documents_workspace_id', 'knowledge_documents', ['workspace_id'], unique=False)
    op.create_index('ix_knowledge_documents_content_hash', 'knowledge_documents', ['content_hash'], unique=False)

    # 3. Knowledge Chunks with Vector(1536)
    vector_col = Vector(1536) if is_postgres else sa.JSON()
    op.create_table(
        'knowledge_chunks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False, default=0),
        sa.Column('embedding', vector_col, nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['knowledge_documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_knowledge_chunks_workspace_id', 'knowledge_chunks', ['workspace_id'], unique=False)
    op.create_index('ix_knowledge_chunks_document_id', 'knowledge_chunks', ['document_id'], unique=False)

    # HNSW vector index for fast cosine similarity search on PostgreSQL
    if is_postgres:
        op.execute("CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding_hnsw ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);")

    # 4. Website Scans
    op.create_table(
        'website_scans',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'PARTIAL_FAILURE', name='scan_status'), nullable=False),
        sa.Column('pages_discovered', sa.Integer(), nullable=False, default=0),
        sa.Column('pages_crawled', sa.Integer(), nullable=False, default=0),
        sa.Column('pages_failed', sa.Integer(), nullable=False, default=0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_website_scans_workspace_id', 'website_scans', ['workspace_id'], unique=False)

def downgrade() -> None:
    op.drop_table('website_scans')
    op.drop_table('knowledge_chunks')
    op.drop_table('knowledge_documents')
    op.drop_table('business_profiles')
