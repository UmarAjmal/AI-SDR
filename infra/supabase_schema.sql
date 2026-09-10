-- ==============================================================================
-- Codenter AI SDR Platform — Complete Supabase PostgreSQL Schema
-- Strict compliance with Developer Product Specification v1.0 (Section 12)
-- ==============================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Custom ENUM Types (Idempotent creation)
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_status') THEN
        CREATE TYPE user_status AS ENUM ('ACTIVE', 'SUSPENDED', 'PENDING');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'workspace_role') THEN
        CREATE TYPE workspace_role AS ENUM ('OWNER', 'ADMIN', 'MEMBER', 'VIEWER');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'scan_status') THEN
        CREATE TYPE scan_status AS ENUM ('PENDING', 'CRAWLING', 'EXTRACTING', 'COMPLETED', 'FAILED');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'crm_provider_type') THEN
        CREATE TYPE crm_provider_type AS ENUM ('HUBSPOT', 'SALESFORCE');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'crm_sync_status') THEN
        CREATE TYPE crm_sync_status AS ENUM ('CONNECTED', 'SYNCING', 'ERROR', 'DISCONNECTED');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'campaign_state') THEN
        CREATE TYPE campaign_state AS ENUM ('DRAFT', 'ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'lead_sequence_state') THEN
        CREATE TYPE lead_sequence_state AS ENUM ('READY', 'SENT', 'REPLIED', 'QUALIFIED', 'MEETING_BOOKED', 'PAUSED', 'STOPPED');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'email_provider_type') THEN
        CREATE TYPE email_provider_type AS ENUM ('GOOGLE', 'MICROSOFT', 'SMTP');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'mailbox_health_status') THEN
        CREATE TYPE mailbox_health_status AS ENUM ('HEALTHY', 'PAUSED', 'REVOKED', 'WARMUP');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'thread_status') THEN
        CREATE TYPE thread_status AS ENUM ('OPEN', 'REPLIED', 'CLOSED', 'BOUNCED');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'message_direction') THEN
        CREATE TYPE message_direction AS ENUM ('OUTBOUND', 'INBOUND');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'delivery_status') THEN
        CREATE TYPE delivery_status AS ENUM ('PENDING', 'SENT', 'DELIVERED', 'BOUNCED', 'FAILED');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'suppression_reason') THEN
        CREATE TYPE suppression_reason AS ENUM ('UNSUBSCRIBE', 'HARD_BOUNCE', 'COMPLAINT', 'MANUAL');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'calendar_provider_type') THEN
        CREATE TYPE calendar_provider_type AS ENUM ('GOOGLE', 'MICROSOFT');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'appointment_status') THEN
        CREATE TYPE appointment_status AS ENUM ('CONFIRMED', 'CANCELLED', 'RESCHEDULED');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'usage_event_type') THEN
        CREATE TYPE usage_event_type AS ENUM ('LLM_PROMPT', 'LLM_COMPLETION', 'EMAIL_SENT', 'WEBSITE_CRAWL', 'ENRICHMENT');
    END IF;
END $$;

-- 3. Identity & Workspace Tables
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    status user_status NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);

CREATE TABLE IF NOT EXISTS workspaces (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    settings_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_workspaces_domain ON workspaces(domain);

CREATE TABLE IF NOT EXISTS workspace_members (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role workspace_role NOT NULL DEFAULT 'MEMBER',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_workspace_member UNIQUE (workspace_id, user_id)
);
CREATE INDEX IF NOT EXISTS ix_workspace_members_workspace_id ON workspace_members(workspace_id);
CREATE INDEX IF NOT EXISTS ix_workspace_members_user_id ON workspace_members(user_id);

-- 4. Business Knowledge & Website Intelligence Tables
CREATE TABLE IF NOT EXISTS business_profiles (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    company_name VARCHAR(255) NOT NULL,
    description TEXT,
    value_propositions JSONB DEFAULT '[]'::jsonb,
    pricing_model TEXT,
    target_industries JSONB DEFAULT '[]'::jsonb,
    target_roles JSONB DEFAULT '[]'::jsonb,
    competitors JSONB DEFAULT '[]'::jsonb,
    faqs JSONB DEFAULT '[]'::jsonb,
    case_studies JSONB DEFAULT '[]'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    profile_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_business_profiles_workspace_id ON business_profiles(workspace_id);

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    url VARCHAR(1000) NOT NULL,
    title VARCHAR(500),
    content_hash VARCHAR(64) NOT NULL,
    source_type VARCHAR(50) NOT NULL DEFAULT 'WEBSITE',
    raw_text TEXT,
    clean_text TEXT,
    page_type VARCHAR(50),
    fetched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_knowledge_documents_workspace_id ON knowledge_documents(workspace_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_documents_content_hash ON knowledge_documents(content_hash);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    document_id VARCHAR(36) NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_workspace_id ON knowledge_chunks(workspace_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_document_id ON knowledge_chunks(document_id);

-- Optional HNSW index on pgvector embeddings for cosine similarity retrieval
CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding_hnsw 
ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE TABLE IF NOT EXISTS website_scans (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    target_url VARCHAR(1000) NOT NULL,
    status scan_status NOT NULL DEFAULT 'PENDING',
    pages_discovered INTEGER NOT NULL DEFAULT 0,
    pages_crawled INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_website_scans_workspace_id ON website_scans(workspace_id);

-- 5. CRM & Lead Intelligence Tables
CREATE TABLE IF NOT EXISTS crm_connections (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    provider crm_provider_type NOT NULL DEFAULT 'HUBSPOT',
    account_id VARCHAR(255) NOT NULL,
    account_name VARCHAR(255),
    encrypted_access_token TEXT NOT NULL,
    encrypted_refresh_token TEXT,
    field_mappings_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    sync_status crm_sync_status NOT NULL DEFAULT 'CONNECTED',
    last_sync_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_crm_connections_workspace_id ON crm_connections(workspace_id);

CREATE TABLE IF NOT EXISTS crm_leads (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    crm_lead_id VARCHAR(255),
    crm_account_id VARCHAR(255),
    email VARCHAR(255) NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    company_name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    job_title VARCHAR(255),
    industry VARCHAR(255),
    employee_count INTEGER,
    phone VARCHAR(50),
    lifecycle_stage VARCHAR(50) DEFAULT 'lead',
    total_score NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    score_band VARCHAR(20) NOT NULL DEFAULT 'COLD',
    score_reasons_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    qualification_status VARCHAR(50) NOT NULL DEFAULT 'UNQUALIFIED',
    is_qualified BOOLEAN NOT NULL DEFAULT FALSE,
    qualification_details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    opt_out BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_crm_leads_workspace_email UNIQUE (workspace_id, email)
);
CREATE INDEX IF NOT EXISTS ix_crm_leads_workspace_id ON crm_leads(workspace_id);
CREATE INDEX IF NOT EXISTS ix_crm_leads_email ON crm_leads(email);
CREATE INDEX IF NOT EXISTS ix_crm_leads_company_name ON crm_leads(company_name);
CREATE INDEX IF NOT EXISTS ix_crm_leads_opt_out ON crm_leads(opt_out);

CREATE TABLE IF NOT EXISTS lead_enrichment (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    lead_id VARCHAR(36) NOT NULL UNIQUE REFERENCES crm_leads(id) ON DELETE CASCADE,
    fields_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    sources_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    enriched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_lead_enrichment_lead_id ON lead_enrichment(lead_id);

-- 6. Campaign & Orchestration Pipeline Tables
CREATE TABLE IF NOT EXISTS campaigns (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    status campaign_state NOT NULL DEFAULT 'DRAFT',
    objective VARCHAR(500),
    target_icp_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    schedule_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_campaigns_workspace_id ON campaigns(workspace_id);
CREATE INDEX IF NOT EXISTS ix_campaigns_status ON campaigns(status);

CREATE TABLE IF NOT EXISTS campaign_steps (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    campaign_id VARCHAR(36) NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    delay_days INTEGER NOT NULL DEFAULT 1,
    template_subject VARCHAR(500) NOT NULL,
    template_body TEXT NOT NULL,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_campaign_step UNIQUE (campaign_id, step_number)
);
CREATE INDEX IF NOT EXISTS ix_campaign_steps_campaign_id ON campaign_steps(campaign_id);

CREATE TABLE IF NOT EXISTS campaign_leads (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    campaign_id VARCHAR(36) NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    lead_id VARCHAR(36) NOT NULL REFERENCES crm_leads(id) ON DELETE CASCADE,
    state lead_sequence_state NOT NULL DEFAULT 'READY',
    current_step INTEGER NOT NULL DEFAULT 1,
    next_action_at TIMESTAMP WITH TIME ZONE,
    last_action_at TIMESTAMP WITH TIME ZONE,
    stop_reason VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_campaign_lead UNIQUE (campaign_id, lead_id)
);
CREATE INDEX IF NOT EXISTS ix_campaign_leads_workspace_id ON campaign_leads(workspace_id);
CREATE INDEX IF NOT EXISTS ix_campaign_leads_campaign_id ON campaign_leads(campaign_id);
CREATE INDEX IF NOT EXISTS ix_campaign_leads_lead_id ON campaign_leads(lead_id);
CREATE INDEX IF NOT EXISTS ix_campaign_leads_state ON campaign_leads(state);
CREATE INDEX IF NOT EXISTS ix_campaign_leads_next_action_at ON campaign_leads(next_action_at);

-- 7. Email Infrastructure & Messaging Tables
CREATE TABLE IF NOT EXISTS email_accounts (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    provider email_provider_type NOT NULL DEFAULT 'GOOGLE',
    email_address VARCHAR(255) NOT NULL,
    encrypted_credentials TEXT NOT NULL,
    daily_send_limit INTEGER NOT NULL DEFAULT 40,
    current_day_sends INTEGER NOT NULL DEFAULT 0,
    last_send_at TIMESTAMP WITH TIME ZONE,
    health_status mailbox_health_status NOT NULL DEFAULT 'HEALTHY',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_email_accounts_workspace_id ON email_accounts(workspace_id);
CREATE INDEX IF NOT EXISTS ix_email_accounts_email_address ON email_accounts(email_address);

CREATE TABLE IF NOT EXISTS email_threads (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    lead_id VARCHAR(36) NOT NULL REFERENCES crm_leads(id) ON DELETE CASCADE,
    campaign_id VARCHAR(36) REFERENCES campaigns(id) ON DELETE SET NULL,
    provider_thread_id VARCHAR(255),
    subject VARCHAR(500) NOT NULL,
    status thread_status NOT NULL DEFAULT 'OPEN',
    summary TEXT,
    intent VARCHAR(50),
    last_message_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_email_threads_workspace_id ON email_threads(workspace_id);
CREATE INDEX IF NOT EXISTS ix_email_threads_lead_id ON email_threads(lead_id);
CREATE INDEX IF NOT EXISTS ix_email_threads_provider_thread_id ON email_threads(provider_thread_id);

CREATE TABLE IF NOT EXISTS email_messages (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    thread_id VARCHAR(36) NOT NULL REFERENCES email_threads(id) ON DELETE CASCADE,
    provider_message_id VARCHAR(255),
    direction message_direction NOT NULL,
    from_address VARCHAR(255) NOT NULL,
    to_address VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    body_text TEXT NOT NULL,
    body_html TEXT,
    delivery_status delivery_status NOT NULL DEFAULT 'PENDING',
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_email_messages_workspace_id ON email_messages(workspace_id);
CREATE INDEX IF NOT EXISTS ix_email_messages_thread_id ON email_messages(thread_id);
CREATE INDEX IF NOT EXISTS ix_email_messages_provider_message_id ON email_messages(provider_message_id);

-- 8. AI Decisions & 5-Question Audit Event Stream
CREATE TABLE IF NOT EXISTS ai_responses (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    thread_id VARCHAR(36) NOT NULL REFERENCES email_threads(id) ON DELETE CASCADE,
    intent VARCHAR(50) NOT NULL,
    output_text TEXT NOT NULL,
    confidence NUMERIC(5, 4) NOT NULL DEFAULT 0.0,
    policy_result_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ai_responses_workspace_id ON ai_responses(workspace_id);
CREATE INDEX IF NOT EXISTS ix_ai_responses_thread_id ON ai_responses(thread_id);

CREATE TABLE IF NOT EXISTS conversation_events (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    lead_id VARCHAR(36) REFERENCES crm_leads(id) ON DELETE SET NULL,
    campaign_id VARCHAR(36) REFERENCES campaigns(id) ON DELETE SET NULL,
    event_type VARCHAR(100) NOT NULL,
    rule_matched VARCHAR(255),
    model_version VARCHAR(100),
    prompt_version VARCHAR(100),
    knowledge_chunk_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    previous_state VARCHAR(100),
    new_state VARCHAR(100),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_conversation_events_workspace_id ON conversation_events(workspace_id);
CREATE INDEX IF NOT EXISTS ix_conversation_events_lead_id ON conversation_events(lead_id);
CREATE INDEX IF NOT EXISTS ix_conversation_events_campaign_id ON conversation_events(campaign_id);
CREATE INDEX IF NOT EXISTS ix_conversation_events_event_type ON conversation_events(event_type);
CREATE INDEX IF NOT EXISTS ix_conversation_events_created_at ON conversation_events(created_at);

-- 9. Calendar Engine & Meeting Bookings Tables
CREATE TABLE IF NOT EXISTS calendar_connections (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    provider calendar_provider_type NOT NULL DEFAULT 'GOOGLE',
    account_email VARCHAR(255) NOT NULL,
    encrypted_access_token TEXT NOT NULL,
    encrypted_refresh_token TEXT NOT NULL,
    token_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    sync_status VARCHAR(50) NOT NULL DEFAULT 'CONNECTED',
    working_hours_json JSONB NOT NULL DEFAULT '{"start_time":"09:00","end_time":"17:00","days":[0,1,2,3,4]}'::jsonb,
    buffer_minutes INTEGER NOT NULL DEFAULT 15,
    timezone VARCHAR(100) NOT NULL DEFAULT 'UTC',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_calendar_connections_workspace_id ON calendar_connections(workspace_id);

CREATE TABLE IF NOT EXISTS appointments (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    calendar_connection_id VARCHAR(36) REFERENCES calendar_connections(id) ON DELETE SET NULL,
    lead_id VARCHAR(36) REFERENCES crm_leads(id) ON DELETE SET NULL,
    campaign_id VARCHAR(36),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status appointment_status NOT NULL DEFAULT 'CONFIRMED',
    provider_event_id VARCHAR(255),
    meet_link VARCHAR(1000),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_appointments_workspace_id ON appointments(workspace_id);
CREATE INDEX IF NOT EXISTS ix_appointments_calendar_conn_id ON appointments(calendar_connection_id);
CREATE INDEX IF NOT EXISTS ix_appointments_lead_id ON appointments(lead_id);
CREATE INDEX IF NOT EXISTS ix_appointments_start_time ON appointments(start_time);
CREATE INDEX IF NOT EXISTS ix_appointments_end_time ON appointments(end_time);

-- 10. Suppression, Compliance & Unsubscribe Tables
CREATE TABLE IF NOT EXISTS suppression_list (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    email VARCHAR(255),
    domain VARCHAR(255),
    reason suppression_reason NOT NULL DEFAULT 'MANUAL',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_suppression_list_workspace_id ON suppression_list(workspace_id);
CREATE INDEX IF NOT EXISTS ix_suppression_list_email ON suppression_list(email);
CREATE INDEX IF NOT EXISTS ix_suppression_list_domain ON suppression_list(domain);

CREATE TABLE IF NOT EXISTS unsubscribe_events (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    source VARCHAR(100) NOT NULL DEFAULT 'INBOUND_EMAIL',
    raw_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_unsubscribe_events_workspace_id ON unsubscribe_events(workspace_id);
CREATE INDEX IF NOT EXISTS ix_unsubscribe_events_email ON unsubscribe_events(email);

-- 11. Usage Metering & Administrative Audit Logs
CREATE TABLE IF NOT EXISTS usage_events (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    event_type usage_event_type NOT NULL,
    model VARCHAR(100),
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0.0,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_usage_events_workspace_id ON usage_events(workspace_id);
CREATE INDEX IF NOT EXISTS ix_usage_events_created_at ON usage_events(created_at);

CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    actor_id VARCHAR(36),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(36),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_audit_logs_workspace_id ON audit_logs(workspace_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_id ON audit_logs(actor_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at);

-- ==============================================================================
-- Schema Initialization Completed Successfully
-- ==============================================================================
